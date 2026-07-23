from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from antscihub_sieve.domain.asset import asset_sidecar_for, media_path_for, validate_asset
from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.probe import run_ffprobe
from antscihub_sieve.persistence.identity import sha256_file
from antscihub_sieve.persistence.json_atomic import read_json, write_json_atomic


class AssetService:
    def resolve(self, reference: str | Path) -> tuple[Path, Path]:
        path = Path(reference).expanduser().resolve()
        if path.name.lower().endswith(".asset.json"):
            sidecar = path
            if not sidecar.exists():
                raise SieveError("ASSET_SIDECAR_MISSING", "Asset sidecar does not exist", path=str(sidecar))
            asset = read_json(sidecar, code="ASSET_SIDECAR_INVALID")
            validate_asset(asset, path=sidecar)
            return sidecar, media_path_for(sidecar, asset)
        return asset_sidecar_for(path), path

    def inspect(self, reference: str | Path) -> dict[str, Any]:
        sidecar, media = self.resolve(reference)
        if not sidecar.exists():
            return {"registered": False, "media_path": str(media), "sidecar_path": str(sidecar), "probe": run_ffprobe(media)}
        asset = read_json(sidecar, code="ASSET_SIDECAR_INVALID")
        validate_asset(asset, path=sidecar)
        return {"registered": True, "asset": asset, "media_path": str(media), "sidecar_path": str(sidecar)}

    def initialize(self, video: str | Path, *, label: str | None = None) -> dict[str, Any]:
        path = Path(video).expanduser().resolve()
        label = (label or path.stem).strip()
        if not label:
            raise SieveError("ASSET_SIDECAR_INVALID", "Asset label cannot be empty")
        if not path.is_file():
            raise SieveError("MEDIA_PROBE_FAILED", "Video does not exist", path=str(path))
        sidecar = asset_sidecar_for(path)
        if sidecar.exists():
            existing = read_json(sidecar, code="ASSET_SIDECAR_INVALID")
            validate_asset(existing, path=sidecar)
            if existing["label"] == label:
                return self.inspect(sidecar)
            raise SieveError("ASSET_SIDECAR_INVALID", "A different asset sidecar already exists", path=str(sidecar))
        probe = run_ffprobe(path)
        media = {"filename": path.name, "content_sha256": sha256_file(path), "size_bytes": path.stat().st_size, **probe}
        asset = {"schema_version": 1, "asset_id": str(uuid.uuid4()), "label": label,
                 "media": media, "lineage": {"parent": None, "derivation": None, "ancestors": []},
                 "calibration": {}, "attributes": {}}
        write_json_atomic(sidecar, asset)
        return {"registered": True, "asset": asset, "media_path": str(path), "sidecar_path": str(sidecar)}

    def verify(self, reference: str | Path, *, level: str = "metadata") -> dict[str, Any]:
        result = self.inspect(reference)
        if not result["registered"]:
            raise SieveError("ASSET_SIDECAR_MISSING", "Video has no asset sidecar", path=result["sidecar_path"])
        asset, media = result["asset"], Path(result["media_path"])
        if not media.is_file():
            raise SieveError("ASSET_CONTENT_MISMATCH", "Asset media is not reachable", path=str(media))
        probe = run_ffprobe(media, count_frames=level == "full")
        stored = asset["media"]
        if media.stat().st_size != stored["size_bytes"] or (probe["width"], probe["height"]) != (stored["width"], stored["height"]):
            raise SieveError("ASSET_CONTENT_MISMATCH", "Media metadata differs from its asset sidecar", path=str(media))
        if level in {"quick", "full"} and sha256_file(media) != stored["content_sha256"]:
            raise SieveError("ASSET_CONTENT_MISMATCH", "Media content hash differs from its asset sidecar", path=str(media))
        return {**result, "verified": True, "level": level, "probe": probe}
