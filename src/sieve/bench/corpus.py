"""The generated decoder corpus and its manifest.

[INTENT] One owner for the manifest format. `decoder_benchmark.py` writes it
and the latency harness under `tests/bench/` reads it, and a manifest with two
independent readers is a format with two definitions that agree until one is
edited.

The corpus itself is not committed -- `.gitignore` excludes
`tests/fixtures/decoder-corpus/`, because it is ninety megabytes that
regenerate deterministically from FFmpeg's `testsrc2`. `REGENERATE_COMMAND` is
what a caller shows a user who does not have it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = ["CORPUS_FILENAME", "DEFAULT_CORPUS_DIR", "REGENERATE_COMMAND", "Clip", "read_manifest"]

CORPUS_FILENAME: Final = "manifest.json"
DEFAULT_CORPUS_DIR: Final = Path("tests/fixtures/decoder-corpus")
REGENERATE_COMMAND: Final = (
    "python -m sieve.bench.decoder_benchmark --generate-corpus --corpus-frames 1000"
)


@dataclass(frozen=True)
class Clip:
    label: str
    codec: str
    path: Path
    expected_bit_depth: int


def read_manifest(corpus_dir: Path) -> list[Clip]:
    """Load the corpus manifest, resolving clip paths against ``corpus_dir``.

    Raises ``FileNotFoundError`` for both an absent manifest and a manifest
    listing files that are not there. The second case is the one worth being
    loud about: a partially generated corpus otherwise produces a benchmark
    that silently covers fewer codecs than its report claims.
    """
    manifest_path = corpus_dir / CORPUS_FILENAME
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"No corpus manifest at {manifest_path}. Regenerate with: {REGENERATE_COMMAND}"
        )
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = [
        Clip(
            label=item["label"],
            codec=item["codec"],
            path=(corpus_dir / item["file"]).resolve(),
            expected_bit_depth=int(item["expected_bit_depth"]),
        )
        for item in data["clips"]
    ]
    missing = [str(clip.path) for clip in clips if not clip.path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"Corpus files are missing: {missing}. Regenerate with: {REGENERATE_COMMAND}"
        )
    return clips
