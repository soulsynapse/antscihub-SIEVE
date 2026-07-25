"""Scrub latency at the decode boundary -- the harness's one real measurement.

[INTENT] Every other budget in `sieve.bench.budgets` describes an interaction
that does not exist yet. This one has a measurable component today, so the
harness gets proven end to end -- budget lookup, environment capture, verdict,
recorded result -- against a number rather than against a placeholder. A
harness whose first measurement arrives with the feature it measures is a
harness nobody has debugged.

What is measured is a seek-and-decode on the pinned ADR-018 path, not a scrub.
The 50 ms budget covers seek, decode, color conversion, and widget repaint;
this covers the first two. `DECODE_SHARE` is where that gap is written down.

[STALE WHEN] `io/video_read.py` lands. This reaches `cv2` directly because the
decode boundary ADR-018 specifies has no module yet, and a benchmark against a
module that does not exist cannot run. When it exists, this measures through it
-- otherwise the harness measures a path the product does not take.
"""

from __future__ import annotations

import os
import random
from itertools import cycle
from typing import Any

import cv2
import numpy as np
import pytest

from sieve.bench.budgets import Verdict, budget, verdict_for
from sieve.bench.corpus import Clip

pytestmark = pytest.mark.slow

BUDGET_KEY = "scrub-seek"

# [ASSUMPTION] Decode is allotted 60% of the 50 ms scrub budget, leaving 20 ms
# for color conversion, the QImage wrap, and the repaint. The split is a
# judgement made before the repaint path exists, chosen so that a decode which
# passes here leaves a repaint budget that a Qt widget has been observed to
# meet. It is the number to replace with a measurement once the scrub is
# assembled, and it is the reason a pass here is not a pass on the budget.
DECODE_SHARE = 0.6

# Distinct targets per call: seeking repeatedly to one frame would measure a
# decoder cache rather than a scrub. Seeded so two runs on one machine are
# comparable, which is the whole point of recording anything.
SEEK_SAMPLE = 64

ENFORCE = os.environ.get("SIEVE_BENCH_ENFORCE", "").strip().lower() in {"1", "true", "yes"}

# Height, width, channels. ADR-018 pins BGR delivery, so a frame that is not
# three-dimensional is not the array the decode boundary promises.
FRAME_NDIM = 3


def _frame_count(capture: cv2.VideoCapture) -> int:
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if count <= 0:
        pytest.skip(
            "OpenCV reports no frame count for this clip; index-based seeking is undefined."
        )
    return count


def test_scrub_seek_decode_latency(
    benchmark: Any,
    scrub_clip: Clip,
    bench_environment: dict[str, Any],
) -> None:
    entry = budget(BUDGET_KEY)
    capture = cv2.VideoCapture(str(scrub_clip.path))
    if not capture.isOpened():
        pytest.skip(f"OpenCV could not open {scrub_clip.path}")
    try:
        total = _frame_count(capture)
        rng = random.Random(f"sieve-scrub-seek:{scrub_clip.label}")
        targets = cycle(rng.sample(range(total), min(SEEK_SAMPLE, total)))

        def seek_and_decode() -> np.ndarray:
            index = next(targets)
            if not capture.set(cv2.CAP_PROP_POS_FRAMES, index):
                raise RuntimeError(f"OpenCV rejected a seek to frame {index}")
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"OpenCV seeked to frame {index} and decoded nothing")
            return frame

        # The capture handle is opened once and reused, because a scrub happens
        # on a file the user already has open. Timing the open here would fold
        # the `file-open` budget into the `scrub-seek` one.
        frame = benchmark(seek_and_decode)
    finally:
        capture.release()

    # What this test asserts, as opposed to reports. Both are machine-
    # independent: a decode that returns the wrong shape or the wrong dtype is
    # broken on any hardware, and ADR-018 pins uint8 BGR as the delivered
    # representation whatever the source depth.
    assert frame.ndim == FRAME_NDIM, f"Expected an HxWx3 frame; got shape {frame.shape}"
    assert frame.dtype == np.uint8, (
        f"ADR-018 pins uint8 BGR delivery; OpenCV returned {frame.dtype}. "
        "A change here changes the decode boundary's declared dtype contract."
    )

    measured_ms = benchmark.stats["median"] * 1000.0
    verdict = verdict_for(BUDGET_KEY, measured_ms, share=DECODE_SHARE)
    benchmark.extra_info.update(
        {
            "budget_key": entry.key,
            "budget_interaction": entry.interaction,
            "budget_ms": entry.milliseconds,
            "budget_regime": entry.regime.value,
            "decode_share": DECODE_SHARE,
            "allotted_ms": entry.milliseconds * DECODE_SHARE,
            "measured_median_ms": measured_ms,
            "verdict": verdict.value,
            "clip": scrub_clip.label,
            "codec": scrub_clip.codec,
            "environment": bench_environment,
        }
    )

    # ADR-008 forbids a single universal wall-time threshold across
    # heterogeneous developer machines, so the default is to record the verdict
    # and let a human read it. SIEVE_BENCH_ENFORCE is how a machine that has
    # been established as canonical opts into failing -- the gate the NOTES
    # deferral is waiting on, with the enforcement point already wired.
    if ENFORCE and verdict is Verdict.REGRESSED:
        pytest.fail(
            f"{entry.interaction}: decode median {measured_ms:.2f} ms against an allotted "
            f"{entry.milliseconds * DECODE_SHARE:.2f} ms "
            f"({DECODE_SHARE:.0%} of the {entry.milliseconds:.0f} ms budget), past the "
            "regression margin. SIEVE_BENCH_ENFORCE is set, so this is a failure."
        )
