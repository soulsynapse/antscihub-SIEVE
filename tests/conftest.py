"""Fixtures shared by every suite that needs real video.

[INTENT] The corpus fixture lived under `tests/bench/` while the latency
harness was its only reader. `tests/io/` is the second, and a fixture copied
into a second conftest is a manifest with two readers again -- the thing
`sieve.bench.corpus` exists to prevent. It moved up rather than being
duplicated.

The corpus is generated, not committed: `.gitignore` excludes
`tests/fixtures/decoder-corpus/`, because five encodes of a synthetic source
are ninety megabytes that regenerate deterministically. A fresh checkout
therefore has none, and these fixtures skip with the command that fixes it. A
suite that cannot run is not the same as a suite that failed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sieve.bench.corpus import Clip, read_manifest

CORPUS_DIR = Path(__file__).resolve().parent / "fixtures" / "decoder-corpus"


@pytest.fixture(scope="session")
def corpus() -> list[Clip]:
    try:
        return read_manifest(CORPUS_DIR)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
