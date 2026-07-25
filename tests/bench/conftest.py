"""Fixtures for the latency-budget harness.

[INTENT] The corpus these benchmarks read is generated, not committed --
`.gitignore` excludes `tests/fixtures/decoder-corpus/`, because five encodes of
a synthetic source are ninety megabytes that regenerate deterministically. A
fresh checkout therefore has no corpus, and these fixtures skip with the
command that fixes it rather than failing on a missing path. A benchmark
session that cannot run is not the same as a benchmark session that failed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sieve.bench.corpus import REGENERATE_COMMAND, Clip, read_manifest
from sieve.bench.environment import capture

CORPUS_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "decoder-corpus"


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
def corpus() -> list[Clip]:
    try:
        return read_manifest(CORPUS_DIR)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))


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
