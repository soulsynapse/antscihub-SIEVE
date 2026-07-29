





































from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from sieve.backend.dispatch import Backend
from sieve.backend.identity import backend_identity
from sieve.core.filter_base import FilterSpec
from sieve.core.pipeline_model import Node, resolved_params
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.decode.identity import decoder_identity















HASH_VERSION = 3




DIGEST_BYTES = 32


class NotCacheableError(ValueError):
    pass











def _digest(*parts: object) -> str:








    payload = json.dumps([HASH_VERSION, *parts], separators=(",", ":"))
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=DIGEST_BYTES).hexdigest()


def source_identity(video: Path) -> str:




















    stat = video.stat()
    return f"{PurePosixPath(video.resolve()).as_posix()}|{stat.st_size}|{stat.st_mtime_ns}"


def source_key(source: str, roi: ROI | None = None, *, luma: bool = False) -> str:













































    region = None if roi is None else [roi.x, roi.y, roi.width, roi.height]
    return _digest("source", source, decoder_identity(), region, "luma" if luma else "bgr")


def node_key(
    node: Node,
    *,
    spec: FilterSpec,
    upstream: Mapping[str, str],
    backend: Backend,
    replicate: Replicate | None = None,
) -> str:






































    if spec.key != (node.filter_id, node.version):
        raise ValueError(
            f"spec is {spec.filter_id} {spec.version} but node names "
            f"{node.filter_id} {node.version}"
        )
    if not spec.cacheable:
        raise NotCacheableError(
            f"{spec.filter_id} {spec.version} is not deterministic, so its output cannot be "
            "keyed — nothing that reads such an entry can know it matches what would be "
            "recomputed"
        )
    params = spec.params_model.model_validate(resolved_params(node, replicate))
    return _digest(
        "node",
        sorted([port, key] for port, key in upstream.items()),
        node.filter_id,
        node.version,
        params.canonical_json(),
        None if spec.backend_agnostic else backend_identity(backend),
    )
