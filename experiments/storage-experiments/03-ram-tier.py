"""RAM tier: what a cached frame costs per form, and what a play-through evicts.

Two questions the eviction and form knobs need numbers for:

**Form.** A cached frame can be full-res crop luma, display-size luma, or
crop luma+chroma. Each is a bytes-per-frame vs re-decode-on-form-miss trade;
this measures the fill rate and bytes of each form so the budget arithmetic
is real (a form miss costs a fresh decode of the same frame — the original's
random-access price, measured in 01/02 — since a cached small frame cannot
be upscaled into a big one).

**Pollution.** ideas.md names the failure — playback walks the timeline and
evicts exactly the frames someone returned to — but it has never had a
number. Sessions: a lingering scrub warms a budget-capped LRU cache, a full
play-through runs through it, the *same* scrub returns. The metric is the
return scrub's hit rate, per eviction policy (play fills the cache vs play
bypasses it) per budget. The pre-play hit rate is reported beside it so the
damage is attributable to play, not to the budget being too small to begin
with.
"""

from __future__ import annotations

import random
import sys
import threading
import time
from collections import OrderedDict
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
DISPLAY_W = 512               #: display-size form: crop strided down to this
N_SCRUB = 80
FETCH_SEED = 7
LINGER_SIGMA = 8
LINGER_JUMP_P = 0.12
BUDGETS = (60, 150, 300)      #: LRU capacity in frames (300 = never evicts)
POLICIES = ("play-fills", "play-bypasses")


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _crop_luma(frame):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    return arr[CROP_Y : CROP_Y + CROP_H, CROP_X : CROP_X + CROP_W]


def form_take(frame, form: str):
    if form == "crop-luma":
        return np.ascontiguousarray(_crop_luma(frame))
    if form == "display-luma":
        stride = -(-CROP_W // DISPLAY_W)
        return np.ascontiguousarray(_crop_luma(frame)[::stride, ::stride])
    if form == "crop-luma+chroma":
        y = np.ascontiguousarray(_crop_luma(frame))
        planes = []
        for p in (frame.planes[1], frame.planes[2]):
            arr = np.frombuffer(p, dtype=np.uint8)
            h, w = frame.height // 2, frame.width // 2
            arr = arr[: h * p.line_size].reshape(h, p.line_size)[:, :w]
            planes.append(np.ascontiguousarray(
                arr[CROP_Y // 2 : (CROP_Y + CROP_H) // 2,
                    CROP_X // 2 : (CROP_X + CROP_W) // 2]))
        return (y, *planes)
    raise ValueError(form)


def form_bytes(stored) -> int:
    if isinstance(stored, tuple):
        return sum(a.nbytes for a in stored)
    return stored.nbytes


# ── phase A: sequential fill rate and bytes per form ─────────────────────────

def measure_forms(run: Run, base_idx: int) -> None:
    for form in ("crop-luma", "display-luma", "crop-luma+chroma"):
        samples = []
        nbytes = 0
        with av.open(str(BIG)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            pts_of, step = _pts_helpers(stream)
            target = pts_of(base_idx)
            container.seek(target, stream=stream)
            decoded = container.decode(stream)
            for frame in decoded:
                if frame.pts is not None and frame.pts + step / 2 >= target:
                    break
            count = 0
            before = time.perf_counter()
            for frame in decoded:
                stored = form_take(frame, form)
                now = time.perf_counter()
                samples.append((now - before) * 1000.0)
                before = now
                nbytes = form_bytes(stored)
                count += 1
                if count >= SPAN - 1:
                    break
        run.cases.append(Case(
            f"form/{form}", {"form": form, "bytes_per_frame": nbytes,
                             "warmup_discarded": 3},
            samples[3:], unit="ms per frame (sequential fill)",
            note=f"{nbytes} bytes/frame -> "
                 f"{8_000_000_000 // max(1, nbytes):,} frames per 8 GB",
        ))


# ── phase B: pollution ───────────────────────────────────────────────────────

class LRU:
    def __init__(self, budget: int):
        self.budget = budget
        self.d: OrderedDict[int, np.ndarray] = OrderedDict()

    def get(self, k):
        if k in self.d:
            self.d.move_to_end(k)
            return self.d[k]
        return None

    def put(self, k, v):
        self.d[k] = v
        self.d.move_to_end(k)
        while len(self.d) > self.budget:
            self.d.popitem(last=False)


def lingering_targets() -> list[int]:
    rng = random.Random(FETCH_SEED)
    targets, anchor = [], rng.randrange(SPAN)
    for _ in range(N_SCRUB):
        if rng.random() < LINGER_JUMP_P:
            anchor = rng.randrange(SPAN)
        targets.append(max(0, min(SPAN - 1, round(rng.gauss(anchor, LINGER_SIGMA)))))
    return targets


def pollution_session(run: Run, base_idx: int, policy: str, budget: int) -> None:
    cache = LRU(budget)
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        pts_of, step = _pts_helpers(stream)
        half = step / 2

        def fetch(rel):
            target = pts_of(base_idx + rel)
            container.seek(target, stream=stream)
            for frame in container.decode(stream):
                if frame.pts is not None and frame.pts + half >= target:
                    return np.ascontiguousarray(_crop_luma(frame))
            raise RuntimeError(f"off the end at {rel}")

        targets = lingering_targets()
        pre_hits = 0
        for t in targets:  # warm scrub: misses memoize
            if cache.get(t) is None:
                cache.put(t, fetch(t))
            else:
                pre_hits += 1
        pre_rate = pre_hits / len(targets)

        # the play-through: sequential pass over the whole span
        target = pts_of(base_idx)
        container.seek(target, stream=stream)
        decoded = container.decode(stream)
        for frame in decoded:
            if frame.pts is not None and frame.pts + half >= target:
                break
        rel = 0
        for frame in decoded:
            if policy == "play-fills" and cache.get(rel) is None:
                cache.put(rel, np.ascontiguousarray(_crop_luma(frame)))
            rel += 1
            if rel >= SPAN:
                break

        # the return scrub: same targets, timed
        samples, hits = [], 0
        for t in targets:
            before = time.perf_counter()
            got = cache.get(t)
            if got is None:
                cache.put(t, fetch(t))
            else:
                hits += 1
            samples.append((time.perf_counter() - before) * 1000.0)
    run.cases.append(Case(
        f"pollution/{policy}/budget={budget}",
        {"policy": policy, "budget_frames": budget,
         "pre_play_hit_rate": round(pre_rate, 3),
         "return_hit_rate": round(hits / len(targets), 3),
         "warmup_discarded": 0},
        samples, unit="ms per return-scrub fetch",
        note=f"pre-play hits {pre_rate:.0%}, post-play {hits / len(targets):.0%}",
    ))


def main() -> None:
    run = Run(
        experiment="03-ram-tier",
        question=(
            "What does a cached frame cost per form (bytes and fill rate), "
            "and how much scrub hit-rate does a full play-through destroy, "
            "per eviction policy and budget?"
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
        f"pollution sessions: {N_SCRUB}-fetch lingering scrub (seed "
        f"{FETCH_SEED}) warms a budget-capped LRU, a full {SPAN}-frame "
        "play-through runs, the same scrub returns; policies: play-fills "
        "(play inserts into the cache) vs play-bypasses (play reads but "
        "never inserts)."
    )

    measure_forms(run, base_idx)
    for policy in POLICIES:
        for budget in BUDGETS:
            pollution_session(run, base_idx, policy, budget)

    for case in run.cases:
        report(case)
        if "return_hit_rate" in case.params:
            print(f"      pre={case.params['pre_play_hit_rate']:.0%} "
                  f"return={case.params['return_hit_rate']:.0%}")
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()
