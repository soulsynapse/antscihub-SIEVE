from __future__ import annotations

from pathlib import Path
from typing import Any

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.domain.geometry import compose_translation
from antscihub_sieve.errors import SieveError


class LineageService:
    def __init__(self, assets: AssetService | None = None) -> None:
        self.assets = assets or AssetService()

    def describe(self, reference: str | Path) -> dict[str, Any]:
        inspected = self.assets.inspect(reference)
        if not inspected["registered"]:
            raise SieveError("ASSET_SIDECAR_MISSING", "Asset sidecar is required")
        lineage = inspected["asset"]["lineage"]
        return {"asset_id": inspected["asset"]["asset_id"], "lineage": lineage,
                "has_known_parent": lineage.get("parent") is not None,
                "translation_to_earliest_known_ancestor": self.compose_transform(inspected["asset"])}

    def compose_transform(self, asset: dict[str, Any]) -> dict[str, int]:
        boxes = [a["derivation"]["parent_box_xyxy"] for a in asset["lineage"].get("ancestors", []) if a.get("derivation")]
        if asset["lineage"].get("derivation"):
            boxes.append(asset["lineage"]["derivation"]["parent_box_xyxy"])
        x, y = compose_translation(boxes)
        return {"x": x, "y": y}

    def resolve_parent(self, reference: str | Path, locate: str | Path | None = None,
                       *, verify_content: bool = True) -> dict[str, Any]:
        inspected = self.assets.inspect(reference); parent = inspected["asset"]["lineage"].get("parent")
        if parent is None:
            return {"status": "none_recorded", "parent": None}
        candidates = [Path(locate).expanduser().resolve()] if locate else []
        child_sidecar = Path(inspected["sidecar_path"])
        for hint in parent.get("location_hints", []):
            candidate = Path(hint); candidates.append((child_sidecar.parent / candidate).resolve() if not candidate.is_absolute() else candidate)
        for candidate in candidates:
            try:
                # A user-selected replacement must earn trust with a full content
                # hash.  Normal navigation follows a location already recorded in
                # the lineage sidecar, so re-reading a multi-GB video on every
                # click adds no useful identity information.  Check the sidecar
                # identity and cheap file metadata in that path instead.
                if locate is not None or verify_content:
                    found = self.assets.verify(candidate, level="quick")
                else:
                    found = self.assets.inspect(candidate)
                    if not found["registered"]:
                        continue
                    media = Path(found["media_path"])
                    if not media.is_file() or media.stat().st_size != found["asset"]["media"]["size_bytes"]:
                        continue
            except SieveError:
                continue
            asset = found["asset"]
            if asset["asset_id"] != parent["asset_id"] or asset["media"]["content_sha256"] != parent["content_sha256"]:
                if locate:
                    raise SieveError("PARENT_IDENTITY_MISMATCH", "Selected asset is not this child's parent", path=str(candidate))
                continue
            return {"status": "reachable", "parent": parent, "resolved": found}
        return {"status": "unreachable", "parent": parent}
