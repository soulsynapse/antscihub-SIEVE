from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.application.derivation import DerivationService
from antscihub_sieve.application.layouts import LayoutService
from antscihub_sieve.application.lineage import LineageService
from antscihub_sieve.domain.geometry import clamp_move, compose_translation, validate_box
from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.session import MediaSession


def test_half_open_coordinates_and_move_rules() -> None:
    assert validate_box([0, 0, 10, 8], 10, 8) == (0, 0, 10, 8)
    assert validate_box([9, 7, 10, 8], 10, 8) == (9, 7, 10, 8)
    for box in ([0, 0, 0, 1], [-1, 0, 1, 1], [0, 0, 11, 8]):
        with pytest.raises(SieveError, match="half-open"): validate_box(box, 10, 8)
    assert clamp_move((2, 2, 7, 6), 9, -2, 10, 8) == (5, 0, 10, 4)
    assert compose_translation([[2, 3, 9, 9], [5, 7, 8, 10]]) == (7, 10)


def test_asset_round_trip_is_portable_and_malformed_is_preserved(video: Path, tmp_path: Path) -> None:
    service = AssetService(); initialized = service.initialize(video, label="source")
    sidecar = Path(initialized["sidecar_path"]); before = sidecar.read_bytes(); assert service.verify(sidecar, level="full")["verified"]
    moved = tmp_path / "moved"; moved.mkdir(); moved_video = moved / video.name; moved_sidecar = moved / sidecar.name
    shutil.copy2(video, moved_video); shutil.copy2(sidecar, moved_sidecar)
    assert service.inspect(moved_sidecar)["asset"]["asset_id"] == initialized["asset"]["asset_id"]
    sidecar.write_text("{broken", encoding="utf-8")
    with pytest.raises(SieveError) as error: service.initialize(video, label="source")
    assert error.value.code == "ASSET_SIDECAR_INVALID" and sidecar.read_text(encoding="utf-8") == "{broken"
    assert before.startswith(b"{")


def test_layout_overlap_counter_template_and_parent_guard(video: Path, tmp_path: Path) -> None:
    assets = AssetService(); assets.initialize(video, label="source"); layouts = LayoutService(assets)
    first = layouts.add(video, [0, 0, 10, 10])["region"]; second = layouts.add(video, [5, 5, 15, 13])["region"]
    layouts.remove(video, second["region_id"]); third = layouts.add(video, [1, 1, 4, 4])["region"]
    assert [first["label"], second["label"], third["label"]] == ["rep1", "rep2", "rep3"]
    template = tmp_path / "template.json"; layouts.export_template(video, template); layouts.clear(video)
    imported = layouts.import_template(video, template)["imported_regions"]
    assert imported[0]["region_id"] != first["region_id"]
    layout_path = video.with_suffix(".replicate-layout.json"); data = json.loads(layout_path.read_text()); data["parent"]["asset_id"] = "wrong"; layout_path.write_text(json.dumps(data))
    with pytest.raises(SieveError) as error: layouts.load(video)
    assert error.value.code == "LAYOUT_PARENT_MISMATCH"


def test_media_frames_use_one_sequential_decoder(video: Path) -> None:
    session = MediaSession(video)
    try:
        first = session.read_frame_rgb(0); decoder = session._decoder
        middle = session.read_frame_rgb(1); assert session._decoder is decoder
        final = session.read_frame_rgb(session.frame_count - 1)
        assert len(first) == len(middle) == len(final) == 18 * 14 * 3
    finally: session.close()


def test_packet_count_checks_length_without_decoding_frames(video: Path) -> None:
    from antscihub_sieve.media.probe import expected_frame_count, run_ffprobe
    probe = run_ffprobe(video, count_packets=True)
    assert probe["decoded_frame_count"] is None
    assert probe["packet_frame_count"] == 12
    assert expected_frame_count(probe) == 12


def test_trusted_parent_navigation_does_not_hash_video(video: Path, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    assets = AssetService(); parent = assets.initialize(video, label="parent")
    layouts = LayoutService(assets); region = layouts.add(video, [1, 1, 12, 10], "rep1")["region"]
    child = DerivationService(assets, layouts).run(video, region_ids=[region["region_id"]], out=tmp_path / "children")["children"][0]
    service = LineageService(assets)
    monkeypatch.setattr(assets, "verify", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("navigation hashed media")))
    resolved = service.resolve_parent(child["asset_path"], verify_content=False)
    assert resolved["status"] == "reachable"
    assert resolved["resolved"]["asset"]["asset_id"] == parent["asset"]["asset_id"]


def _crop_rgb(raw: bytes, source_width: int, box: list[int]) -> bytes:
    x0, y0, x1, y1 = box; return b"".join(raw[y * source_width * 3 + x0 * 3:y * source_width * 3 + x1 * 3] for y in range(y0, y1))


def test_derivation_exact_frames_lineage_recursive_and_rerun(video: Path, tmp_path: Path) -> None:
    assets = AssetService(); parent = assets.initialize(video, label="source"); layouts = LayoutService(assets); derive = DerivationService(assets, layouts)
    box = [1, 1, 12, 10]; region = layouts.add(video, box, "rep1")["region"]
    planned = derive.plan(video, layout=video.with_suffix(".replicate-layout.json"), out=tmp_path / "out", profile="lossless")
    assert planned["writes_performed"] is False and not Path(planned["regions"][0]["output_directory"]).exists()
    result = derive.run(video, layout=video.with_suffix(".replicate-layout.json"), region_ids=[region["region_id"]], out=tmp_path / "out")
    child = result["children"][0]; assert child["status"] == "complete" and child["asset"]["media"]["width"] == 11 and child["asset"]["media"]["height"] == 9
    assert "\\" not in child["asset"]["lineage"]["parent"]["location_hints"][0]
    parent_session, child_session = MediaSession(video), MediaSession(Path(child["media_path"]))
    try:
        for frame in (0, parent_session.frame_count - 1): assert child_session.read_frame_rgb(frame) == _crop_rgb(parent_session.read_frame_rgb(frame), 18, box)
    finally: parent_session.close(); child_session.close()
    rerun = derive.run(video, layout=video.with_suffix(".replicate-layout.json"), out=tmp_path / "out")
    assert rerun["children"][0]["status"] == "existing"
    child_video = Path(child["media_path"]); inner = layouts.add(child_video, [1, 1, 5, 5], "inner")["region"]
    grand = derive.run(child_video, region_ids=[inner["region_id"]], out=tmp_path / "grand")["children"][0]
    assert grand["status"] == "complete" and LineageService(assets).describe(grand["asset_path"])["translation_to_earliest_known_ancestor"] == {"x": 2, "y": 2}


def test_cancel_removes_temporary_output(video: Path, tmp_path: Path) -> None:
    assets = AssetService(); assets.initialize(video, label="source"); layouts = LayoutService(assets); region = layouts.add(video, [0, 0, 18, 14])["region"]; service = DerivationService(assets, layouts)
    def progress(record: dict[str, object]) -> None:
        if record["phase"] == "encoding": service.cancel()
    result = service.run(video, region_ids=[region["region_id"]], out=tmp_path / "cancelled", progress=progress)
    assert result["cancelled"] and result["children"][0]["error"]["code"] == "DERIVATION_CANCELLED"
    assert not list((tmp_path / "cancelled").glob("**/*.tmp")) and not list((tmp_path / "cancelled").glob("**/video.asset.json"))
    canceled = layouts.load(video)["layout"]["draft_regions"][0]
    assert canceled["state"] == "canceled" and canceled["last_error"]["code"] == "DERIVATION_CANCELLED"


def test_cancel_during_verification_does_not_publish_a_ready_child(video: Path, tmp_path: Path) -> None:
    assets = AssetService(); assets.initialize(video, label="source"); layouts = LayoutService(assets); region = layouts.add(video, [0, 0, 18, 14])["region"]; service = DerivationService(assets, layouts)
    def progress(record: dict[str, object]) -> None:
        if record["phase"] == "verifying": service.cancel()
    output = tmp_path / "cancelled-during-verification"
    result = service.run(video, region_ids=[region["region_id"]], out=output, progress=progress)
    assert result["cancelled"] and result["complete_count"] == 0
    assert result["children"][0]["error"]["code"] == "DERIVATION_CANCELLED"
    assert not list(output.glob("**/video.asset.json"))
    layout = layouts.load(video)["layout"]
    assert layout["created_children"] == [] and layout["draft_regions"][0]["state"] == "canceled"


def test_attempted_geometry_is_frozen_and_clear_only_removes_drafts(video: Path) -> None:
    assets = AssetService(); assets.initialize(video, label="source"); layouts = LayoutService(assets)
    frozen = layouts.add(video, [1, 1, 8, 8], "attempted")["region"]; editable = layouts.add(video, [9, 1, 17, 8], "draft")["region"]
    layouts.set_states(video, {frozen["region_id"]: ("extracting", None)})
    with pytest.raises(SieveError, match="frozen"):
        layouts.update(video, frozen["region_id"], [2, 2, 9, 9])
    layouts.set_states(video, {frozen["region_id"]: ("failed", {"code": "ENCODE_FAILED", "message": "test"})})
    cleared = layouts.clear(video)["layout"]
    assert [region["region_id"] for region in cleared["draft_regions"]] == [frozen["region_id"]]
    assert cleared["draft_regions"][0]["box_xyxy"] == [1, 1, 8, 8]


def test_interrupted_extraction_recovery_is_fail_closed(video: Path) -> None:
    assets = AssetService(); assets.initialize(video, label="source"); layouts = LayoutService(assets)
    extracting = layouts.add(video, [1, 1, 8, 8], "extracting")["region"]
    verifying = layouts.add(video, [9, 1, 17, 8], "verifying")["region"]
    layouts.set_states(video, {extracting["region_id"]: ("extracting", None), verifying["region_id"]: ("verifying", None)})
    recovered = layouts.recover_interrupted(video)
    assert recovered["recovered_count"] == 2 and recovered["layout"]["created_children"] == []
    for region in recovered["layout"]["draft_regions"]:
        assert region["state"] == "canceled"
        assert region["last_error"]["code"] == "EXTRACTION_INTERRUPTED"
    assert layouts.recover_interrupted(video)["recovered_count"] == 0


def test_unexpected_derivation_error_is_persisted_as_failed(video: Path, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    assets = AssetService(); assets.initialize(video); layouts = LayoutService(assets); region = layouts.add(video, [1, 1, 9, 9])["region"]; service = DerivationService(assets, layouts)
    monkeypatch.setattr(service, "_run_one", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    result = service.run(video, out=tmp_path / "children", region_ids=[region["region_id"]])
    assert result["complete_count"] == 0 and result["children"][0]["error"]["code"] == "DERIVATION_FAILED"
    persisted = layouts.load(video)["layout"]["draft_regions"][0]
    assert persisted["state"] == "failed" and persisted["last_error"]["detail"] == "boom"


@pytest.mark.parametrize("profile", ["high-quality", "compact"])
def test_lossy_profiles_preserve_odd_crop_dimensions(video: Path, tmp_path: Path, profile: str) -> None:
    assets = AssetService(); assets.initialize(video, label="source"); service = DerivationService(assets)
    result = service.run(video, crop=[1, 1, 12, 10], label=profile, out=tmp_path / profile, profile=profile)
    child = result["children"][0]
    assert child["status"] == "complete", child.get("error")
    assert (child["asset"]["media"]["width"], child["asset"]["media"]["height"]) == (11, 9)


def test_ffprobe_is_launched_without_a_windows_console(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.media import probe
    from antscihub_sieve.media.process import CREATE_NO_WINDOW
    captured: dict[str, object] = {}
    class Completed:
        returncode = 0; stderr = ""
        stdout = json.dumps({"streams": [{"width": 10, "height": 8, "avg_frame_rate": "2/1", "duration": "1.0"}], "format": {}})
    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs); return Completed()
    monkeypatch.setattr(probe.subprocess, "run", fake_run)
    assert probe.run_ffprobe(tmp_path / "video.mkv")["width"] == 10
    assert captured["creationflags"] == CREATE_NO_WINDOW
