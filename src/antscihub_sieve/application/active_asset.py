from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.application.lineage import LineageService
from antscihub_sieve.persistence.json_atomic import write_json_atomic


@dataclass(frozen=True, slots=True)
class ParentIdentity:
    asset_id: str
    content_sha256: str
    label: str
    location_hints: tuple[str, ...]
    status: str
    resolved_sidecar_path: Path | None


@dataclass(frozen=True, slots=True)
class ActiveAsset:
    asset_id: str
    sidecar_path: Path
    video_path: Path
    label: str
    kind: str
    width: int
    height: int
    fps_num: int
    fps_den: int
    duration_seconds: float
    parent: ParentIdentity | None

    @property
    def fps(self) -> float:
        return self.fps_num / self.fps_den


class ActiveAssetController(QObject):
    """Application session containing only the current immutable asset snapshot."""

    active_asset_changed = pyqtSignal(object)

    def __init__(self, assets: AssetService | None = None) -> None:
        super().__init__()
        self._assets = assets or AssetService()
        self._lineage = LineageService(self._assets)
        self._active_asset: ActiveAsset | None = None

    @property
    def active_asset(self) -> ActiveAsset | None:
        return self._active_asset

    def open_asset(self, reference: str | Path) -> ActiveAsset:
        inspected = self._assets.inspect(reference)
        if not inspected["registered"]:
            inspected = self._assets.initialize(inspected["media_path"])
        snapshot = self._snapshot(inspected)
        self._active_asset = snapshot
        self.active_asset_changed.emit(snapshot)
        return snapshot

    def locate_parent(self, reference: str | Path) -> ActiveAsset:
        active = self._require_active()
        result = self._lineage.resolve_parent(active.sidecar_path, reference)
        if result["status"] == "reachable":
            inspected = self._assets.inspect(active.sidecar_path)
            parent = inspected["asset"]["lineage"]["parent"]
            hint = Path(os.path.relpath(reference, active.sidecar_path.parent)).as_posix()
            if hint not in parent["location_hints"]:
                parent["location_hints"].insert(0, hint)
            write_json_atomic(active.sidecar_path, inspected["asset"])
        return self.open_asset(active.sidecar_path)

    def _require_active(self) -> ActiveAsset:
        if self._active_asset is None:
            raise RuntimeError("No active asset")
        return self._active_asset

    def _snapshot(self, inspected: dict) -> ActiveAsset:  # type: ignore[type-arg]
        asset = inspected["asset"]
        media = asset["media"]
        parent_record = asset["lineage"].get("parent")
        parent = None
        if parent_record is not None:
            resolution = self._lineage.resolve_parent(inspected["sidecar_path"], verify_content=False)
            resolved = resolution.get("resolved")
            parent = ParentIdentity(
                asset_id=parent_record["asset_id"],
                content_sha256=parent_record["content_sha256"],
                label=parent_record.get("label", parent_record["asset_id"][:8]),
                location_hints=tuple(parent_record.get("location_hints", ())),
                status=resolution["status"],
                resolved_sidecar_path=Path(resolved["sidecar_path"]) if resolved else None,
            )
        return ActiveAsset(
            asset_id=asset["asset_id"],
            sidecar_path=Path(inspected["sidecar_path"]),
            video_path=Path(inspected["media_path"]),
            label=asset["label"],
            kind="replicate" if parent_record is not None else "video",
            width=int(media["width"]),
            height=int(media["height"]),
            fps_num=int(media["fps_num"]),
            fps_den=int(media["fps_den"]),
            duration_seconds=float(media["duration_seconds"]),
            parent=parent,
        )
