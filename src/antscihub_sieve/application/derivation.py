from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.application.layouts import LayoutService, utc_now
from antscihub_sieve.domain.asset import validate_asset
from antscihub_sieve.domain.geometry import validate_box
from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.probe import expected_frame_count, run_ffprobe
from antscihub_sieve.media.process import CREATE_NO_WINDOW
from antscihub_sieve.media.profiles import PROFILES
from antscihub_sieve.persistence.identity import sha256_file
from antscihub_sieve.persistence.json_atomic import write_json_atomic

Progress = Callable[[dict[str, Any]], None]


def _slug(label: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", label.strip()).strip("-._").lower()
    return value[:60] or "replicate"


def _relative_hint(target: Path, base: Path) -> str:
    return Path(os.path.relpath(target, base)).as_posix()


class DerivationService:
    def __init__(self, assets: AssetService | None = None, layouts: LayoutService | None = None) -> None:
        self.assets = assets or AssetService(); self.layouts = layouts or LayoutService(self.assets)
        self._cancel = threading.Event(); self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancel.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def _raise_if_cancelled(self, region_id: str) -> None:
        if self._cancel.is_set():
            raise SieveError("DERIVATION_CANCELLED", "Derivation was cancelled", region_id=region_id)

    def _parent(self, reference: str | Path) -> dict[str, Any]:
        inspected = self.assets.verify(reference, level="metadata")
        return inspected

    def _regions(self, parent: str | Path, *, crop: str | list[int] | None, label: str | None,
                 layout: str | Path | None, region_ids: list[str] | None,
                 inspected: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        asset = (inspected or self._parent(parent))["asset"]; media = asset["media"]
        if crop is not None:
            box = validate_box(crop, media["width"], media["height"])
            return [{"region_id": str(uuid.uuid4()), "label": label or "replicate", "box_xyxy": list(box), "color": "#ffd24a"}], None
        loaded = self.layouts.load(layout or parent)
        document = loaded["layout"]
        if document is None:
            raise SieveError("LAYOUT_PARENT_MISMATCH", "No replicate layout exists for this asset")
        expected = (asset["asset_id"], media["content_sha256"], media["width"], media["height"])
        actual_parent = document["parent"]
        actual = (actual_parent["asset_id"], actual_parent["content_sha256"], actual_parent["width"], actual_parent["height"])
        if expected != actual:
            raise SieveError("LAYOUT_PARENT_MISMATCH", "Derivation layout does not match the parent")
        wanted = set(region_ids or [])
        regions = [r for r in document["draft_regions"] if (r["region_id"] in wanted if wanted else r["state"] in {"draft", "failed", "canceled"})]
        created_regions = []
        if not document["draft_regions"] or wanted:
            for record in document["created_children"]:
                snap = dict(record["region_snapshot"])
                if not wanted or snap["region_id"] in wanted:
                    snap["_created_child"] = record["child"]
                    created_regions.append(snap)
        regions += created_regions
        if wanted - {r["region_id"] for r in regions}:
            raise SieveError("LAYOUT_COORDINATES_INVALID", "One or more requested region ids are not drafts", region_ids=sorted(wanted))
        if not regions:
            raise SieveError("LAYOUT_COORDINATES_INVALID", "No draft regions were selected")
        return regions, document

    def plan(self, parent: str | Path, *, out: str | Path, profile: str = "lossless", crop: str | list[int] | None = None,
             label: str | None = None, layout: str | Path | None = None, region_ids: list[str] | None = None) -> dict[str, Any]:
        if profile not in PROFILES:
            raise SieveError("ENCODER_START_FAILED", "Unknown encoding profile", profile=profile)
        inspected = self._parent(parent); regions, document = self._regions(parent, crop=crop, label=label, layout=layout,
                                                                          region_ids=region_ids, inspected=inspected)
        output_root = Path(out).expanduser().resolve(); encoding = PROFILES[profile]; plans = []
        for region in regions:
            box = validate_box(region["box_xyxy"], inspected["asset"]["media"]["width"], inspected["asset"]["media"]["height"])
            existing = region.get("_created_child"); child_id = existing["asset_id"] if existing else str(uuid.uuid4())
            existing_path = None
            if existing:
                layout_base = Path(self.layouts.load(layout or parent)["layout_path"]).parent
                for hint in existing.get("location_hints", []):
                    candidate = Path(hint); candidate = candidate if candidate.is_absolute() else (layout_base / candidate).resolve()
                    if candidate.exists(): existing_path = candidate; break
            directory = existing_path.parent if existing_path else output_root / f"{_slug(region['label'])}--{child_id[:8]}"
            plans.append({"region_id": region["region_id"], "label": region["label"], "box_xyxy": list(box),
                          "output_width": box[2] - box[0], "output_height": box[3] - box[1], "child_asset_id": child_id,
                          "output_directory": str(directory), "video_path": str(directory / "video.mkv"),
                          "profile": encoding.name, "codec": encoding.codec, "pixel_format": encoding.pixel_format,
                          "color_metadata": encoding.color_metadata, "encoder_arguments": list(encoding.arguments), "collision": directory.exists() and not existing_path,
                          "existing_asset_path": str(existing_path) if existing_path else None,
                          "expected_content_sha256": existing.get("content_sha256") if existing else None})
        return {"parent_asset_id": inspected["asset"]["asset_id"], "parent_path": inspected["media_path"],
                "output_root": str(output_root), "profile": profile, "regions": plans, "writes_performed": False,
                "layout_path": str(layout) if layout else None, "has_layout": document is not None}

    def _emit(self, callback: Progress | None, job: str, plan: dict[str, Any], phase: str, message: str, **extra: Any) -> None:
        if callback:
            callback({"job_id": job, "region_id": plan["region_id"], "label": plan["label"], "phase": phase,
                      "message": message, **extra})

    def run(self, parent: str | Path, *, out: str | Path, profile: str = "lossless", crop: str | list[int] | None = None,
            label: str | None = None, layout: str | Path | None = None, region_ids: list[str] | None = None,
            progress: Progress | None = None) -> dict[str, Any]:
        self._cancel.clear(); job = str(uuid.uuid4())
        if crop is None and region_ids is None:
            self.layouts.recover_interrupted(layout or parent)
        planned = self.plan(parent, out=out, profile=profile, crop=crop, label=label, layout=layout, region_ids=region_ids)
        # plan() already metadata-verified this same parent. Re-read its small
        # sidecar instead of launching ffprobe again before encoding.
        parent_info = self.assets.inspect(parent); parent_asset = parent_info["asset"]; parent_media = Path(parent_info["media_path"])
        source_frames = expected_frame_count(parent_asset["media"]); results = []
        for item in planned["regions"]:
            try:
                if planned["has_layout"] and not item.get("existing_asset_path"):
                    self.layouts.set_states(parent, {item["region_id"]: ("extracting", None)})
                results.append(self._run_one(job, item, parent_asset, parent_media, source_frames, progress,
                                             parent_reference=parent if planned["has_layout"] else None))
                if planned["has_layout"]:
                    self._record_created(parent, item, results[-1])
            except SieveError as exc:
                if planned["has_layout"] and not item.get("existing_asset_path"):
                    state = "canceled" if exc.code == "DERIVATION_CANCELLED" else "failed"
                    self.layouts.set_states(parent, {item["region_id"]: (state, exc.as_dict())})
                self._emit(progress, job, item, "failed", exc.message, error=exc.as_dict())
                results.append({"status": "failed", "region_id": item["region_id"], "label": item["label"], "error": exc.as_dict()})
                if exc.code == "DERIVATION_CANCELLED":
                    break
            except Exception as exc:
                error = {"code": "DERIVATION_FAILED", "message": "Unexpected failure interrupted derivation", "detail": str(exc)}
                if planned["has_layout"] and not item.get("existing_asset_path"):
                    self.layouts.set_states(parent, {item["region_id"]: ("failed", error)})
                self._emit(progress, job, item, "failed", error["message"], error=error)
                results.append({"status": "failed", "region_id": item["region_id"], "label": item["label"], "error": error})
                break
        return {"job_id": job, "parent_asset_id": parent_asset["asset_id"], "children": results,
                "complete_count": sum(r["status"] in {"complete", "existing"} for r in results),
                "failed_count": sum(r["status"] == "failed" for r in results), "cancelled": self._cancel.is_set()}

    def _run_one(self, job: str, plan: dict[str, Any], parent_asset: dict[str, Any], parent_media: Path,
                 source_frames: int, progress: Progress | None, *, parent_reference: str | Path | None = None) -> dict[str, Any]:
        self._raise_if_cancelled(plan["region_id"])
        output_dir = Path(plan["output_directory"]); final_video = output_dir / "video.mkv"
        if plan.get("existing_asset_path"):
            verified = self.verify(plan["existing_asset_path"]); asset = verified["asset"]
            if asset["asset_id"] != plan["child_asset_id"] or asset["media"]["content_sha256"] != plan["expected_content_sha256"]:
                raise SieveError("ASSET_CONTENT_MISMATCH", "Recorded child location does not match its identity", path=plan["existing_asset_path"])
            derivation = asset["lineage"]["derivation"]
            if derivation["parent_box_xyxy"] != plan["box_xyxy"]:
                raise SieveError("DERIVATION_VERIFY_FAILED", "Recorded child crop does not match its region snapshot")
            return {"status": "existing", **verified, "region_id": plan["region_id"], "label": plan["label"]}
        if output_dir.exists():
            try:
                verified = self.verify(output_dir / "video.asset.json")
                derivation = verified["asset"]["lineage"]["derivation"]
                if derivation["parent_box_xyxy"] == plan["box_xyxy"] and verified["asset"]["label"] == plan["label"]:
                    return {"status": "existing", **verified}
            except SieveError:
                pass
            raise SieveError("OUTPUT_COLLISION", "Planned child output already exists", path=str(output_dir), region_id=plan["region_id"])
        temp = output_dir.with_name(f".{output_dir.name}.{job[:8]}.tmp")
        if temp.exists():
            shutil.rmtree(temp)
        temp.mkdir(parents=True); temp_video = temp / "video.mkv"
        try:
            self._emit(progress, job, plan, "planning", "Encoding plan validated", frames_completed=0, frames_expected=source_frames, fraction=0.0)
            x0, y0, x1, y1 = plan["box_xyxy"]
            args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(parent_media), "-map", "0:v:0",
                    "-vf", f"crop={x1-x0}:{y1-y0}:{x0}:{y0}:exact=1", "-an", *plan["encoder_arguments"],
                    "-progress", "pipe:1", "-nostats", str(temp_video)]
            try:
                self._process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
            except OSError as exc:
                raise SieveError("ENCODER_START_FAILED", "FFmpeg encoder could not be started", detail=str(exc), arguments=args) from exc
            assert self._process.stdout is not None
            completed_frames = 0
            for line in self._process.stdout:
                if self._cancel.is_set():
                    self._process.terminate(); break
                key, _, value = line.strip().partition("=")
                if key == "frame" and value.isdigit():
                    completed_frames = int(value)
                    self._emit(progress, job, plan, "encoding", "Encoding child video", frames_completed=completed_frames,
                               frames_expected=source_frames, fraction=min(1.0, completed_frames / max(1, source_frames)))
            stderr = self._process.stderr.read() if self._process.stderr else ""; returncode = self._process.wait(); self._process = None
            if self._cancel.is_set():
                raise SieveError("DERIVATION_CANCELLED", "Derivation was cancelled", region_id=plan["region_id"])
            if returncode:
                raise SieveError("ENCODE_FAILED", "FFmpeg failed while encoding child", detail=stderr.strip(), arguments=args)
            if parent_reference is not None:
                self.layouts.set_states(parent_reference, {plan["region_id"]: ("verifying", None)})
            self._emit(progress, job, plan, "verifying", "Verifying encoded video", frames_completed=source_frames,
                       frames_expected=source_frames, fraction=1.0)
            self._raise_if_cancelled(plan["region_id"])
            # The encoder has already decoded every source frame. Counting video
            # packets validates the output length without decoding the entire
            # new child a second time; FFmpeg emits one packet per video frame for
            # all supported SIEVE profiles.
            child_probe = run_ffprobe(temp_video, count_packets=True, cancel_event=self._cancel); child_frames = expected_frame_count(child_probe)
            self._raise_if_cancelled(plan["region_id"])
            if (child_probe["width"], child_probe["height"]) != (plan["output_width"], plan["output_height"]):
                raise SieveError("DERIVATION_VERIFY_FAILED", "Encoded child dimensions do not match the crop", probe=child_probe)
            if child_frames != source_frames:
                raise SieveError("DECODE_TRUNCATED", "Encoded child does not contain the full temporal range",
                                 expected=source_frames, actual=child_frames)
            content_hash = sha256_file(temp_video); self._raise_if_cancelled(plan["region_id"]); now = utc_now()
            parent_hint = _relative_hint(Path(self.assets.inspect(parent_media)["sidecar_path"]), temp)
            parent_snapshot = {"asset_id": parent_asset["asset_id"], "content_sha256": parent_asset["media"]["content_sha256"],
                               "label": parent_asset["label"], "location_hints": [parent_hint]}
            derivation = {"operation": "crop", "parent_box_xyxy": plan["box_xyxy"], "output_width": plan["output_width"],
                          "output_height": plan["output_height"], "child_to_parent_translation": {"x": x0, "y": y0},
                          "frame_start": 0, "frame_count": child_frames, "encoder": plan["codec"],
                          "profile": plan["profile"], "pixel_format": plan["pixel_format"], "color_metadata": plan["color_metadata"],
                          "arguments": args[args.index("-an") + 1:args.index("-progress")], "created_utc": now}
            ancestors = list(parent_asset["lineage"].get("ancestors", []))
            ancestors.append({**parent_snapshot, "derivation": parent_asset["lineage"].get("derivation")})
            child_asset = {"schema_version": 1, "asset_id": plan["child_asset_id"], "label": plan["label"],
                           "media": {"filename": "video.mkv", "content_sha256": content_hash, "size_bytes": temp_video.stat().st_size, **child_probe},
                           "lineage": {"parent": parent_snapshot, "derivation": derivation, "ancestors": ancestors},
                           "calibration": dict(parent_asset.get("calibration", {})), "attributes": {}}
            validate_asset(child_asset); self._raise_if_cancelled(plan["region_id"]); write_json_atomic(temp / "video.asset.json", child_asset)
            self._emit(progress, job, plan, "publishing", "Publishing verified child", fraction=1.0)
            self._raise_if_cancelled(plan["region_id"])
            temp.replace(output_dir)
            result = {"status": "complete", "asset": child_asset, "asset_path": str(output_dir / "video.asset.json"),
                      "media_path": str(final_video), "region_id": plan["region_id"], "label": plan["label"]}
            self._emit(progress, job, plan, "complete", "Child replicate created", fraction=1.0, child=result)
            return result
        except BaseException:
            if self._process and self._process.poll() is None:
                self._process.terminate(); self._process.wait(timeout=5)
            self._process = None
            if temp.exists():
                shutil.rmtree(temp)
            raise

    def _record_created(self, parent: str | Path, plan: dict[str, Any], result: dict[str, Any]) -> None:
        if result["status"] != "complete":
            return
        loaded = self.layouts.load(parent); layout = loaded["layout"]
        region = next((r for r in layout["draft_regions"] if r["region_id"] == plan["region_id"]), None)
        if region is None:
            return
        layout["draft_regions"] = [r for r in layout["draft_regions"] if r["region_id"] != plan["region_id"]]
        layout_path = Path(loaded["layout_path"]); hint = _relative_hint(Path(result["asset_path"]), layout_path.parent)
        layout["created_children"].append({"region_snapshot": {k: region[k] for k in ("region_id", "label", "box_xyxy", "color")},
                                           "child": {"asset_id": result["asset"]["asset_id"],
                                                     "content_sha256": result["asset"]["media"]["content_sha256"], "location_hints": [hint]},
                                           "created_utc": utc_now()})
        self.layouts.save(parent, layout)

    def verify(self, child: str | Path) -> dict[str, Any]:
        path = Path(child).expanduser().resolve()
        if path.is_dir():
            path = path / "video.asset.json"
        result = self.assets.verify(path, level="full")
        if result["asset"]["lineage"].get("derivation", {}).get("operation") != "crop":
            raise SieveError("DERIVATION_VERIFY_FAILED", "Asset is not a verified crop derivation", path=str(path))
        return result
