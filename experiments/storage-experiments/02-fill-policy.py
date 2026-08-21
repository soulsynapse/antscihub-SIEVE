"""Fill policy: chunk size, fill order and worker count against a scrub with hands.

01 could not tell fill orders apart because its scripted scrub drew uniform
random targets — no locality for near-playhead to exploit. This adds a
*lingering* scrub model (gaussian around an anchor that occasionally jumps,
which is what hands do) and runs the factorial the fill design needs:

  chunk size   GOP x 1/2/4 — seek overhead per chunk against how fast fill
               can react when the anchor moves.
  fill order   sequential vs near-playhead, now with locality to exploit.
  workers      1 vs 2 fill threads — 01 measured one worker at a third of
               its solo rate under foreground contention; does a second help
               or trip the collapse the decode shelf measured?

Every session: same-seed scripted scrub at FETCH_HZ, misses memoized, sleeps
excluded from samples, hit/miss routes and fill progress in the params. The
verdict metric is misses (each one is a ~300 ms stall a user felt) and when
the last one happened; fill completion time is the secondary.
"""

from __future__ import annotations

import random
import sys
import threading
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness
from harness import FOOTAGE, Case, Run, report

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"

# ── knobs ────────────────────────────────────────────────────────────────────
SPAN = 300
START_S = 60
CROP_W, CROP_H, CROP_X, CROP_Y = 1024, 1024, 2144, 982
N_FETCHES = 100
FETCH_INTERVAL_S = 0.05
FETCH_SEED = 7
GOP = 24                      #: results/04-*: fixed on this footage
CHUNK_GOPS = (1, 2, 4)        #: fill chunk = GOP x this
ORDERS = ("sequential", "near-playhead")
SCRUBS = ("uniform", "lingering")
LINGER_SIGMA = 8              #: gaussian spread of a lingering scrub
LINGER_JUMP_P = 0.12          #: per-fetch chance the anchor teleports
WORKER_SWEEP = (1, 2)         #: measured at chunk=GOP, near-playhead, lingering


def scripted_targets(model: str) -> list[int]:
    rng = random.Random(FETCH_SEED)
    if model == "uniform":
        return [rng.randrange(SPAN) for _ in range(N_FETCHES)]
    targets, anchor = [], rng.randrange(SPAN)
    for _ in range(N_FETCHES):
        if rng.random() < LINGER_JUMP_P:
            anchor = rng.randrange(SPAN)
        targets.append(max(0, min(SPAN - 1, round(rng.gauss(anchor, LINGER_SIGMA)))))
    return targets


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _take_luma(frame):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    return np.ascontiguousarray(arr[CROP_Y : CROP_Y + CROP_H,
                                    CROP_X : CROP_X + CROP_W])


class Fetcher:
    def __init__(self, base_idx: int):
        self.container = av.open(str(BIG))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)
        self.base_idx = base_idx

    def fetch(self, rel_idx: int):
        target = self.pts_of(self.base_idx + rel_idx)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        for frame in self.container.decode(self.stream):
            if frame.pts is not None and frame.pts + half >= target:
                return _take_luma(frame)
        raise RuntimeError(f"ran off the end at rel_idx={rel_idx}")

    def close(self):
        self.container.close()


def fill_worker(base_idx: int, chunk: int, cache: dict, last_req: list,
                order: str, remaining: set, lock: threading.Lock,
                progress: list, t0: float, stop: threading.Event) -> None:
    fetcher = Fetcher(base_idx)
    pts_of, step = fetcher.pts_of, fetcher.step
    half = step / 2
    try:
        while not stop.is_set():
            with lock:
                if not remaining:
                    return
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
                    cache[rel] = _take_luma(frame)
                progress.append((time.perf_counter() - t0, len(cache)))
                rel += 1
                if rel >= min(pick + chunk, SPAN) or stop.is_set():
                    break
    finally:
        fetcher.close()


def session(run: Run, base_idx: int, scrub: str, order: str,
            chunk_gops: int, workers: int) -> None:
    chunk = GOP * chunk_gops
    targets = scripted_targets(scrub)
    cache: dict[int, np.ndarray] = {}
    last_req = [targets[0]]
    remaining = set(range(0, SPAN, chunk))
    lock = threading.Lock()
    progress: list[tuple[float, int]] = []
    stop = threading.Event()
    miss_fetcher = Fetcher(base_idx)
    t0 = time.perf_counter()
    threads = [
        threading.Thread(target=fill_worker,
                         args=(base_idx, chunk, cache, last_req, order,
                               remaining, lock, progress, t0, stop),
                         daemon=True)
        for _ in range(workers)
    ]
    for t in threads:
        t.start()
    samples, routes = [], []
    next_tick = time.perf_counter()
    for tgt in targets:
        now = time.perf_counter()
        if now < next_tick:
            time.sleep(next_tick - now)
        next_tick = max(next_tick, now) + FETCH_INTERVAL_S
        last_req[0] = tgt
        before = time.perf_counter()
        if tgt in cache:
            routes.append("hit")
        else:
            cache[tgt] = miss_fetcher.fetch(tgt)
            routes.append("miss")
        samples.append((time.perf_counter() - before) * 1000.0)
    fill_done = progress[-1][0] if len(cache) >= SPAN else None
    stop.set()
    for t in threads:
        t.join(timeout=30)
    miss_fetcher.close()
    misses = [i for i, r in enumerate(routes) if r == "miss"]
    name = f"{scrub}/{order}/gop x{chunk_gops}/{workers}w"
    run.cases.append(Case(
        name,
        {"scrub": scrub, "order": order, "chunk_gops": chunk_gops,
         "workers": workers, "routes": routes, "fill_done_s": fill_done,
         "filled_frames": len(cache), "misses": len(misses),
         "last_miss": misses[-1] if misses else None,
         "fetch_interval_s": FETCH_INTERVAL_S, "warmup_discarded": 0},
        samples, unit="ms per fetch",
        note="sleep between fetches excluded",
    ))


def main() -> None:
    run = Run(
        experiment="02-fill-policy",
        question=(
            "Under uniform and lingering scrubs, how do fill chunk size, "
            "fill order and worker count trade misses, last-miss time and "
            "fill completion?"
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
        f"lingering scrub: gaussian sigma={LINGER_SIGMA} around an anchor "
        f"that jumps with p={LINGER_JUMP_P}/fetch; every session same seed "
        f"({FETCH_SEED}), {N_FETCHES} fetches at {1 / FETCH_INTERVAL_S:.0f}/s."
    )

    for scrub in SCRUBS:
        for order in ORDERS:
            for chunk_gops in CHUNK_GOPS:
                session(run, base_idx, scrub, order, chunk_gops, workers=1)
    for workers in WORKER_SWEEP:
        if workers == 1:
            continue  # already covered above
        session(run, base_idx, "lingering", "near-playhead", 1, workers)

    for case in run.cases:
        q = f"misses={case.params['misses']:>3} last={str(case.params['last_miss']):>4} fill={case.params['fill_done_s'] and round(case.params['fill_done_s'], 2)}"
        print(f"  {case.name:<38} {q}")
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()
