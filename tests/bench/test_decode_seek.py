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

[STABLE] The measurement runs through `sieve.io.video_read`, the decode
boundary ADR-018 specifies, rather than through `cv2` directly. A benchmark
that reaches past the boundary measures a path the product does not take, and
would stay green through a regression introduced in the boundary itself.

[STALE WHEN] The video viewer lands and the scrub becomes assemblable end to
end. At that point `DECODE_SHARE` is replaceable with a measurement, and this
becomes the decode component of a real scrub number rather than a proxy for it.
"""

from __future__ import annotations

import os
import random
from itertools import cycle
from typing import Any

import numpy as np
import pytest

from sieve.bench.budgets import Verdict, budget, verdict_for
from sieve.bench.corpus import Clip
from sieve.io.video_read import VideoOpenError, VideoReader

pytestmark = pytest.mark.slow

BUDGET_KEY = "scrub-seek"

# Measured, not guessed, as of the video viewer landing (2026-07-25): the
# BGR-to-QImage wrap, the aspect-preserving scale, and QLabel.setPixmap
# through VideoViewer._paint on the h264-8bit corpus clip median 0.7-0.8 ms
# over 64 samples on this machine, offscreen and against a real window alike
# (max observed 6.7 ms). Allotting 10% of the 50 ms scrub budget to that
# component leaves roughly 5x headroom over the observed maximum, which is
# the margin this share is chosen for rather than for the median alone.
# Superseded the earlier 0.6 guess, made before the repaint path existed to
# measure. Re-measure with `tests/gui/measure_repaint.py` if the widget's
# paint path changes shape.
DECODE_SHARE = 0.9

# Distinct targets per call: seeking repeatedly to one frame would measure a
# decoder cache rather than a scrub. Seeded so two runs on one machine are
# comparable, which is the whole point of recording anything.
SEEK_SAMPLE = 64

ENFORCE = os.environ.get("SIEVE_BENCH_ENFORCE", "").strip().lower() in {"1", "true", "yes"}

# Height, width, channels. ADR-018 pins BGR delivery, so a frame that is not
# three-dimensional is not the array the decode boundary promises.
FRAME_NDIM = 3


def test_scrub_seek_decode_latency(
    benchmark: Any,
    scrub_clip: Clip,
    bench_environment: dict[str, Any],
) -> None:
    entry = budget(BUDGET_KEY)
    try:
        reader = VideoReader(scrub_clip.path)
    except VideoOpenError as exc:
        pytest.skip(str(exc))
    try:
        total = reader.info.frame_count
        if total is None:
            pytest.skip(
                f"{scrub_clip.label} reports no frame count, so index-based seeking "
                f"is undefined and there is no scrub to measure."
            )
        rng = random.Random(f"sieve-scrub-seek:{scrub_clip.label}")
        targets = cycle(rng.sample(range(total), min(SEEK_SAMPLE, total)))

        # The reader is opened once and reused, because a scrub happens on a
        # file the user already has open. Timing the open here would fold the
        # `file-open` budget into the `scrub-seek` one.
        frame = benchmark(lambda: reader.read(next(targets)))
    finally:
        reader.close()

    # What this test asserts, as opposed to reports. Both are machine-
    # independent: a decode that returns the wrong shape or the wrong dtype is
    # broken on any hardware. The boundary's own contract is covered in
    # `tests/io/test_video_read.py`; kept here as a sanity check that the timed
    # region produced a frame at all, since a benchmark of a function that
    # returns nothing still reports a very good number.
    assert frame.ndim == FRAME_NDIM, f"Expected an HxWx3 frame; got shape {frame.shape}"
    assert frame.dtype == np.uint8, (
        f"ADR-018 pins uint8 BGR delivery; the boundary returned {frame.dtype}."
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
