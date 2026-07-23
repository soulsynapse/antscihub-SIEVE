from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.domain.asset import layout_sidecar_for
from antscihub_sieve.domain.geometry import validate_box
from antscihub_sieve.domain.layout import DRAFT_STATES, validate_layout
from antscihub_sieve.errors import SieveError
from antscihub_sieve.persistence.json_atomic import read_json, write_json_atomic

PALETTE = ("#ff5a5a", "#ffd24a", "#52d273", "#4da6ff", "#b86bff", "#ff7ac8", "#45d6d6")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class LayoutService:
    def __init__(self, assets: AssetService | None = None) -> None:
        self.assets = assets or AssetService()

    def _asset(self, parent: str | Path) -> tuple[dict[str, Any], Path, Path]:
        inspected = self.assets.inspect(parent)
        if not inspected["registered"]:
            raise SieveError("ASSET_SIDECAR_MISSING", "Initialize the parent asset first", path=inspected["sidecar_path"])
        media = Path(inspected["media_path"])
        return inspected["asset"], media, layout_sidecar_for(media)

    def create(self, parent: str | Path) -> dict[str, Any]:
        asset, _, path = self._asset(parent)
        media = asset["media"]
        layout = {"schema_version": 1, "layout_id": str(uuid.uuid4()),
                  "parent": {"asset_id": asset["asset_id"], "content_sha256": media["content_sha256"],
                             "width": media["width"], "height": media["height"]},
                  "next_display_number": 1, "draft_regions": [], "created_children": []}
        write_json_atomic(path, layout)
        return {"layout": layout, "layout_path": str(path)}

    def load(self, reference: str | Path, *, create: bool = False) -> dict[str, Any]:
        ref = Path(reference).expanduser().resolve()
        if ref.name.lower().endswith(".replicate-layout.json"):
            layout = read_json(ref, code="LAYOUT_PARENT_MISMATCH")
            validate_layout(layout, path=ref)
            return {"layout": layout, "layout_path": str(ref)}
        asset, _, path = self._asset(ref)
        if not path.exists():
            if create:
                return self.create(ref)
            return {"layout": None, "layout_path": str(path)}
        layout = read_json(path, code="LAYOUT_PARENT_MISMATCH")
        validate_layout(layout, asset, path=path)
        return {"layout": layout, "layout_path": str(path)}

    def save(self, parent: str | Path, layout: dict[str, Any]) -> dict[str, Any]:
        asset, _, path = self._asset(parent)
        validate_layout(layout, asset, path=path)
        write_json_atomic(path, layout)
        return {"layout": layout, "layout_path": str(path)}

    def add(self, parent: str | Path, box: str | list[int], label: str | None = None, *, color: str | None = None) -> dict[str, Any]:
        loaded = self.load(parent, create=True); layout = loaded["layout"]
        resolved = validate_box(box, layout["parent"]["width"], layout["parent"]["height"])
        number = int(layout["next_display_number"]); now = utc_now()
        region = {"region_id": str(uuid.uuid4()), "label": label or f"rep{number}", "box_xyxy": list(resolved),
                  "color": color or PALETTE[(number - 1) % len(PALETTE)], "state": "draft",
                  "created_utc": now, "updated_utc": now}
        layout["draft_regions"].append(region); layout["next_display_number"] = number + 1
        self.save(parent, layout)
        return {**loaded, "layout": layout, "region": region}

    def _region(self, layout: dict[str, Any], region_id: str) -> dict[str, Any]:
        for region in layout["draft_regions"]:
            if region["region_id"] == region_id:
                return region
        raise SieveError("LAYOUT_COORDINATES_INVALID", "Draft region was not found", region_id=region_id)

    def update(self, parent: str | Path, region_id: str, box: str | list[int]) -> dict[str, Any]:
        loaded = self.load(parent); layout = loaded["layout"]
        region = self._region(layout, region_id)
        if region["state"] != "draft":
            raise SieveError("LAYOUT_COORDINATES_INVALID", "Geometry is frozen once extraction has started", region_id=region_id, state=region["state"])
        region["box_xyxy"] = list(validate_box(box, layout["parent"]["width"], layout["parent"]["height"]))
        region["updated_utc"] = utc_now(); self.save(parent, layout)
        return {**loaded, "layout": layout, "region": region}

    def rename(self, parent: str | Path, region_id: str, label: str) -> dict[str, Any]:
        if not label.strip():
            raise SieveError("LAYOUT_COORDINATES_INVALID", "Region label cannot be empty", region_id=region_id)
        loaded = self.load(parent); layout = loaded["layout"]; region = self._region(layout, region_id)
        region["label"] = label.strip(); region["updated_utc"] = utc_now(); self.save(parent, layout)
        return {**loaded, "layout": layout, "region": region}

    def remove(self, parent: str | Path, region_id: str) -> dict[str, Any]:
        loaded = self.load(parent); layout = loaded["layout"]; region = self._region(layout, region_id)
        layout["draft_regions"] = [r for r in layout["draft_regions"] if r["region_id"] != region_id]
        self.save(parent, layout); return {**loaded, "layout": layout, "removed": region}

    def remove_child_record(self, parent: str | Path, asset_id: str) -> dict[str, Any]:
        loaded = self.load(parent); layout = loaded["layout"]
        child_index = next((index for index, record in enumerate(layout["created_children"]) if record["child"].get("asset_id") == asset_id), None)
        if child_index is None:
            raise SieveError("ASSET_SIDECAR_MISSING", "Created child record was not found", asset_id=asset_id)
        child = layout["created_children"].pop(child_index)
        self.save(parent, layout)
        return {**loaded, "layout": layout, "removed": child}

    def clear(self, parent: str | Path) -> dict[str, Any]:
        loaded = self.load(parent, create=True); layout = loaded["layout"]
        removed = sum(r["state"] == "draft" for r in layout["draft_regions"])
        layout["draft_regions"] = [r for r in layout["draft_regions"] if r["state"] != "draft"]; self.save(parent, layout)
        return {**loaded, "layout": layout, "removed_count": removed}

    def set_states(self, parent: str | Path, states: dict[str, tuple[str, dict[str, Any] | None]]) -> dict[str, Any]:
        loaded = self.load(parent); layout = loaded["layout"]
        for region_id, (state, error) in states.items():
            if state not in DRAFT_STATES:
                raise SieveError("LAYOUT_COORDINATES_INVALID", "Unknown extraction state", region_id=region_id, state=state)
            region = self._region(layout, region_id); region["state"] = state; region["updated_utc"] = utc_now()
            if error is None: region.pop("last_error", None)
            else: region["last_error"] = error
        self.save(parent, layout)
        return {**loaded, "layout": layout}

    def recover_interrupted(self, parent: str | Path) -> dict[str, Any]:
        """Fail closed after a crash or shutdown interrupted an extraction."""
        loaded = self.load(parent, create=True); layout = loaded["layout"]; recovered: list[str] = []
        for region in layout["draft_regions"]:
            if region["state"] not in {"extracting", "verifying"}: continue
            previous = region["state"]; region["state"] = "canceled"; region["updated_utc"] = utc_now()
            region["last_error"] = {"code": "EXTRACTION_INTERRUPTED", "message": f"The application stopped while this replicate was {previous}. Retry extraction explicitly."}
            recovered.append(region["region_id"])
        if recovered: self.save(parent, layout)
        return {**loaded, "layout": layout, "recovered_region_ids": recovered, "recovered_count": len(recovered)}

    def export_template(self, parent: str | Path, out: str | Path) -> dict[str, Any]:
        layout = self.load(parent, create=True)["layout"]
        template = {"schema_version": 1, "template": "sieve-replicate-layout", "width": layout["parent"]["width"],
                    "height": layout["parent"]["height"], "draft_regions": [
                        {k: r[k] for k in ("label", "box_xyxy", "color")} for r in layout["draft_regions"]]}
        destination = Path(out).expanduser().resolve(); write_json_atomic(destination, template)
        return {"template_path": str(destination), "draft_count": len(template["draft_regions"])}

    def import_template(self, parent: str | Path, template_path: str | Path) -> dict[str, Any]:
        template = read_json(Path(template_path), code="LAYOUT_COORDINATES_INVALID")
        if set(template) - {"schema_version", "template", "width", "height", "draft_regions"}:
            raise SieveError("LAYOUT_COORDINATES_INVALID", "Template contains unknown keys")
        loaded = self.load(parent, create=True); layout = loaded["layout"]
        added = []
        for item in template.get("draft_regions", []):
            box = validate_box(item.get("box_xyxy", []), layout["parent"]["width"], layout["parent"]["height"])
            result = self.add(parent, list(box), item.get("label"), color=item.get("color")); added.append(result["region"])
        return {**self.load(parent), "imported_regions": added}

    def validate(self, reference: str | Path) -> dict[str, Any]:
        loaded = self.load(reference); validate_layout(loaded["layout"]); return {**loaded, "valid": True}
