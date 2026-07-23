from __future__ import annotations

from pathlib import Path
from typing import Any

from antscihub_sieve.domain.geometry import validate_box
from antscihub_sieve.errors import SieveError

DRAFT_STATES = {"draft", "extracting", "verifying", "failed", "canceled"}


def validate_layout(layout: dict[str, Any], asset: dict[str, Any] | None = None, *, path: Path | None = None) -> None:
    if layout.get("schema_version") != 1 or not isinstance(layout.get("layout_id"), str):
        raise SieveError("LAYOUT_PARENT_MISMATCH", "Unsupported or malformed layout", path=str(path) if path else None)
    parent = layout.get("parent")
    if not isinstance(parent, dict):
        raise SieveError("LAYOUT_PARENT_MISMATCH", "Layout parent is missing", path=str(path) if path else None)
    if asset is not None:
        media = asset["media"]
        expected = (asset["asset_id"], media["content_sha256"], media["width"], media["height"])
        actual = (parent.get("asset_id"), parent.get("content_sha256"), parent.get("width"), parent.get("height"))
        if actual != expected:
            raise SieveError("LAYOUT_PARENT_MISMATCH", "Layout belongs to a different parent asset", expected=expected, actual=actual)
    width, height = int(parent.get("width", 0)), int(parent.get("height", 0))
    ids: set[str] = set()
    for region in layout.get("draft_regions", []):
        if not isinstance(region, dict) or not isinstance(region.get("region_id"), str) or region["region_id"] in ids:
            raise SieveError("LAYOUT_COORDINATES_INVALID", "Draft region ids must be unique")
        ids.add(region["region_id"])
        if region.get("state") not in DRAFT_STATES:
            raise SieveError("LAYOUT_COORDINATES_INVALID", "Draft region state is invalid", region_id=region["region_id"], state=region.get("state"))
        validate_box(region.get("box_xyxy", []), width, height)
    for child in layout.get("created_children", []):
        if not isinstance(child, dict) or not isinstance(child.get("region_snapshot"), dict):
            raise SieveError("LAYOUT_COORDINATES_INVALID", "Created child record is malformed")
        validate_box(child["region_snapshot"].get("box_xyxy", []), width, height)
