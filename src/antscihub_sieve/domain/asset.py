from __future__ import annotations

from pathlib import Path
from typing import Any

from antscihub_sieve.errors import SieveError


def asset_sidecar_for(video: Path) -> Path:
    return video.with_suffix(".asset.json")


def layout_sidecar_for(video: Path) -> Path:
    return video.with_suffix(".replicate-layout.json")


def media_path_for(sidecar: Path, asset: dict[str, Any]) -> Path:
    filename = asset.get("media", {}).get("filename")
    if not isinstance(filename, str) or not filename:
        raise SieveError("ASSET_SIDECAR_INVALID", "Asset media.filename is missing", path=str(sidecar))
    return (sidecar.parent / filename).resolve()


def validate_asset(asset: dict[str, Any], *, path: Path | None = None) -> None:
    if asset.get("schema_version") != 1:
        raise SieveError("ASSET_SIDECAR_INVALID", "Unsupported or malformed asset sidecar", path=str(path) if path else None)
    if "kind" in asset:
        raise SieveError("ASSET_SIDECAR_INVALID", "Asset kind is not part of the lineage-agnostic schema", path=str(path) if path else None)
    if not isinstance(asset.get("asset_id"), str) or not isinstance(asset.get("label"), str):
        raise SieveError("ASSET_SIDECAR_INVALID", "Asset id and label are required", path=str(path) if path else None)
    media = asset.get("media")
    lineage = asset.get("lineage")
    required = {"filename", "content_sha256", "size_bytes", "width", "height", "fps_num", "fps_den"}
    if not isinstance(media, dict) or not required.issubset(media) or not isinstance(lineage, dict):
        raise SieveError("ASSET_SIDECAR_INVALID", "Asset media or lineage is incomplete", path=str(path) if path else None)
