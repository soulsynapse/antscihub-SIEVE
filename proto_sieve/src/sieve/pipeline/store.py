"""Secret: which directory holds saved pipelines, and how a ``Pipeline``
becomes the text ``store/`` writes.

Name-to-path resolution, the escape guard, and the actual file I/O are
``store/``'s secret, not this module's — this file only ever supplies a
directory and a JSON string.
"""

from __future__ import annotations

from pathlib import Path

from proto_sieve.src.sieve.pipeline.pipeline import Pipeline, from_json, to_json
from proto_sieve.src.sieve.store import list_names, load_text, repo_root, save_text

DEFAULT_PIPELINES_DIR = repo_root() / "proto_sieve" / "pipelines"


def save(name: str, pipeline: Pipeline, directory: Path = DEFAULT_PIPELINES_DIR) -> Path:
    return save_text(name, to_json(pipeline), directory)


def load(name: str, directory: Path = DEFAULT_PIPELINES_DIR) -> Pipeline:
    return from_json(load_text(name, directory))


def list_pipelines(directory: Path = DEFAULT_PIPELINES_DIR) -> list[str]:
    return list_names(directory)
