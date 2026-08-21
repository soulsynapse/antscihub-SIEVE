"""Time-to-tunable: how fast does a cold region become interactive, per strategy?

The decode shelf priced the substrates; this prices the *wait*. Four ways to
open a 300-frame region of the uncut original and start scrubbing it:

  cold        every fetch pays the original's random-access price, forever —
              the do-nothing floor.
  transcode   encode the lossy-intra cut first (exp05's recipe), then fetch
              from it: the ceiling on snappiness, bought with an upfront wall.
  lazy-seq    a background thread fills a RAM dict sequentially (the cheap
              rate) while the foreground scrubs immediately; misses pay the
              random rate and are memoized too.
  lazy-near   same, but fill radiates outward from the last scrubbed frame in
              GOP-aligned chunks — the attention-guided policy.

The foreground is a scripted human: one random fetch in the region every
FETCH_INTERVAL_S, same seed for every strategy. Sleep between fetches is
excluded from the samples; the per-fetch trace *is* the finding — a strategy
is tunable at the fetch where its trailing latency reaches cut-level, and
that index is computed at read time, never stored. Fill progress and
hit/miss routes land in the case params so the trace can be read against
coverage.
"""

from __future__ import annotations

import random
import subprocess
import sys
import threading
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np

# one harness serves every experiment folder; duplicating it would fork the
# result format, so import it from decode-experiments and repoint RESULTS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness
from harness import FOOTAGE, Case, Run, report, time_case

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"

# ── knobs ────────────────────────────────────────────────────────────────────
SPAN = 300              #: frames in the region being opened
START_S = 60            #: where the region starts in the original
CROP_W, CROP_H, CROP_X, CROP_Y = 1024, 1024, 2144, 982  # exp05's region
N_FETCHES = 100         #: scripted scrub length
FETCH_INTERVAL_S = 0.05 #: one fetch per this many seconds (~human drag rate)
FETCH_SEED = 7          #: same targets for every strategy
GOP = 24                #: fill-chunk alignment (results/04-*: fixed on this footage)
CUT_ARGS = ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-g", "1",
            "-copyts"]  #: the permissive envelope, exp05's winner + ADR-0004
SCRATCH_CUT = FOOTAGE / "derived" / "_scratch-time-to-tunable.mp4"


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _take_luma(frame, crop: bool):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    if crop:
        arr = arr[CROP_Y : CROP_Y + CROP_H, CROP_X : CROP_X + CROP_W]
    return np.ascontiguousarray(arr)


class Fetcher:
    """One open container fetching exact frames by region-relative index."""

    def __init__(self, path: Path, base_idx: int, crop: bool):
        self.container = av.open(str(path))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)
        self.base_idx = base_idx
        self.crop = crop

    def fetch(self, rel_idx: int):
        target = self.pts_of(self.base_idx + rel_idx)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        for frame in self.container.decode(self.stream):
            if frame.pts is not None and frame.pts + half >= target:
                return _take_luma(frame, self.crop)
        raise RuntimeError(f"ran off the end seeking rel_idx={rel_idx}")

    def close(self):
        self.container.close()


# ── background fill (the store's pausable-chunk primitive) ───────────────────

def fill_worker(base_idx: int, cache: dict, last_req: list, order: str,
                progress: list, stop: threading.Event) -> None:
    """Decode the region into `cache` in GOP-aligned chunks.

    `order` is the policy knob: "sequential" walks the chunks in file order;
    "near-playhead" always takes the unfilled chunk closest to the last
    foreground request. Chunk starts are keyframe-aligned so each chunk is
    one cheap landing plus sequential decode.
    """
    t0 = time.perf_counter()
    chunk_starts = list(range(0, SPAN, GOP))
    remaining = set(chunk_starts)
    fetcher = Fetcher(BIG, base_idx, crop=True)
    pts_of, step = fetcher.pts_of, fetcher.step
    half = step / 2
    try:
        while remaining and not stop.is_set():
            if order == "near-playhead":
                pick = min(remaining, key=lambda s: abs(s - last_req[0]))
            else:
                pick = min(remaining)
            remaining.discard(pick)
            target = pts_of(base_idx + pick)
            fetcher.container.seek(target, stream=fetcher.stream)
            rel = pick
            for frame in fetcher.container.decode(fetcher.stream):
                if frame.pts is None or frame.pts + half < target:
                    continue
                if rel not in cache:
                    cache[rel] = _take_luma(frame, True)
                progress.append((time.perf_counter() - t0, len(cache)))
                rel += 1
                if rel >= min(pick + GOP, SPAN) or stop.is_set():
                    break
    finally:
        fetcher.close()


# ── strategies ───────────────────────────────────────────────────────────────

def scripted_targets() -> list[int]:
    rng = random.Random(FETCH_SEED)
    return [rng.randrange(SPAN) for _ in range(N_FETCHES)]


def run_session(run: Run, name: str, fetch_fn, params: dict,
                setup_note: str = "") -> None:
    """The scripted scrub: timed fetches, sleeps excluded from the samples."""
    targets = scripted_targets()
    samples, routes = [], []
    next_tick = time.perf_counter()
    for t in targets:
        now = time.perf_counter()
        if now < next_tick:
            time.sleep(next_tick - now)
        next_tick = max(next_tick, now) + FETCH_INTERVAL_S
        before = time.perf_counter()
        route = fetch_fn(t)
        samples.append((time.perf_counter() - before) * 1000.0)
        routes.append(route)
    params = dict(params)
    params.update({"fetch_interval_s": FETCH_INTERVAL_S, "routes": routes,
                   "warmup_discarded": 0})
    case = Case(name, params, samples, unit="ms per fetch",
                note=setup_note or "sleep between fetches excluded")
    run.cases.append(case)


def main() -> None:
    run = Run(
        experiment="01-time-to-tunable",
        question=(
            "From a cold open of a region of the uncut original, how long "
            "until interactive fetch latency reaches cut-level, per strategy "
            "(cold / transcode-first / lazy sequential fill / lazy "
            "near-playhead fill)?"
        ),
    )
    if not BIG.exists():
        print(f"missing {BIG}")
        return
    run.add_footage(BIG)
    with av.open(str(BIG)) as c:
        rate = c.streams.video[0].average_rate
    base_idx = int(START_S * rate) + 1
    run.note(
        f"region = {SPAN} frames from ~{START_S}s (base index {base_idx}), "
        f"crop {CROP_W}x{CROP_H}+{CROP_X}+{CROP_Y}; foreground = "
        f"{N_FETCHES} same-seed fetches at {1 / FETCH_INTERVAL_S:.0f}/s; "
        f"fill chunks GOP-aligned at {GOP}."
    )

    # cold: the do-nothing floor
    fetcher = Fetcher(BIG, base_idx, crop=True)
    run_session(run, "cold", lambda t: (fetcher.fetch(t), "miss")[1],
                {"strategy": "cold"})
    fetcher.close()

    # transcode-first: pay the cut, then fetch from it
    SCRATCH_CUT.parent.mkdir(exist_ok=True)
    SCRATCH_CUT.unlink(missing_ok=True)
    before = time.perf_counter()
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y",
         "-ss", str(START_S), "-i", str(BIG), "-frames:v", str(SPAN),
         "-vf", f"crop={CROP_W}:{CROP_H}:{CROP_X}:{CROP_Y}", "-an",
         *CUT_ARGS, str(SCRATCH_CUT)],
        stderr=subprocess.PIPE,
    )
    encode_s = time.perf_counter() - before
    if proc.returncode != 0:
        run.note("transcode FAILED: "
                 + proc.stderr.decode(errors="replace")[:200])
    else:
        run.note(f"transcode-first: cut encoded in {encode_s:.1f}s "
                 f"({SCRATCH_CUT.stat().st_size} bytes) — its time-to-first-"
                 "fetch; fetches below start only after it")
        fetcher = Fetcher(SCRATCH_CUT, 0, crop=False)
        run_session(run, "transcode-first",
                    lambda t: (fetcher.fetch(t), "cut")[1],
                    {"strategy": "transcode-first", "encode_s": encode_s})
        fetcher.close()

    # lazy fill, both orders: scrub starts immediately, fill races it
    for order in ("sequential", "near-playhead"):
        cache: dict[int, np.ndarray] = {}
        last_req = [0]
        progress: list[tuple[float, int]] = []
        stop = threading.Event()
        miss_fetcher = Fetcher(BIG, base_idx, crop=True)
        thread = threading.Thread(
            target=fill_worker,
            args=(base_idx, cache, last_req, order, progress, stop),
            daemon=True,
        )

        def lazy_fetch(t: int) -> str:
            last_req[0] = t
            if t in cache:
                return "hit"
            arr = miss_fetcher.fetch(t)
            cache[t] = arr
            return "miss"

        thread.start()
        run_session(run, f"lazy-{order}", lazy_fetch,
                    {"strategy": f"lazy-{order}"})
        fill_done = progress[-1][0] if len(cache) >= SPAN else None
        stop.set()
        thread.join(timeout=30)
        miss_fetcher.close()
        run.cases[-1].params["fill_done_s"] = fill_done
        run.cases[-1].params["filled_frames"] = len(cache)
        run.note(f"lazy-{order}: fill covered {len(cache)}/{SPAN} frames"
                 + (f", complete at {fill_done:.2f}s" if fill_done else
                    " (incomplete when the scrub ended)"))

    SCRATCH_CUT.unlink(missing_ok=True)
    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()
