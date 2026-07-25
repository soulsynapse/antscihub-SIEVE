"""Fixtures for the latency-budget harness.

The `corpus` fixture these build on lives in `tests/conftest.py`, because
`tests/io/` reads it too. What stays here is what only a benchmark needs:
machine metadata, and the choice of which clip a latency number is measured
against.
"""

from __future__ import annotations

from typing import Any

import pytest

from sieve.bench.corpus import REGENERATE_COMMAND, Clip
from sieve.bench.environment import capture


@pytest.fixture(scope="session")
def bench_environment() -> dict[str, Any]:
    """Machine and dependency metadata, captured once per session (ADR-008).

    Attached to every benchmark's ``extra_info`` so a saved result carries the
    context needed to judge whether a later result is comparable. ADR-008
    rejects a universal wall-time threshold precisely because that context
    varies between the machines a result comes from.
    """
    return capture()


@pytest.fixture(scope="session")
def scrub_clip(corpus: list[Clip]) -> Clip:
    """The clip the scrub measurement runs against.

    H.264 8-bit deliberately: the user stories in `docs/01-vision/` centre on
    ordinary 8-bit recordings, so a budget measured against ProRes would report
    a number no user's scrub produces. The other codecs are exercised for seek
    *accuracy* by `sieve.bench.decoder_benchmark`, which is the question
    ADR-018 turned on and is not this one.
    """
    for clip in corpus:
        if clip.label == "h264-8bit":
            return clip
    pytest.skip(
        f"The corpus has no h264-8bit clip, so the scrub measurement has no subject. "
        f"Regenerate with: {REGENERATE_COMMAND}"
    )
