from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.application.working_window import (
    ExtentProvenance,
    WorkingWindowOutcomeKind,
    WorkingWindowRequest,
    extent_provenance,
    open_working_window,
)
from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.session import MediaSession


def request_for(
    initialized: dict[str, object],
    start: int,
    stop: int,
    *,
    plane_id: str = "rgb24",
) -> WorkingWindowRequest:
    asset = initialized["asset"]
    assert isinstance(asset, dict)
    media = asset["media"]
    assert isinstance(media, dict)
    return WorkingWindowRequest(
        asset_ref=Path(str(initialized["sidecar_path"])),
        expected_asset_id=str(asset["asset_id"]),
        expected_content_sha256=str(media["content_sha256"]),
        start_frame=start,
        stop_frame=stop,
        plane_id=plane_id,
    )


def test_working_window_contract_imports_without_qt() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import antscihub_sieve.application.working_window; "
                "assert not any(n == 'PyQt6' or n.startswith('PyQt6.') "
                "for n in sys.modules)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_native_half_open_batches_are_absolute_and_batch_invariant(
    video: Path,
) -> None:
    assets = AssetService()
    initialized = assets.initialize(video, label="source")
    request = request_for(initialized, 2, 5)

    with open_working_window(
        request, batch_size=2, assets=assets
    ) as stream:
        batches = list(stream)
    assert [batch.absolute_frame_indices for batch in batches] == [
        (2, 3),
        (4,),
    ]
    assert [batch.shape for batch in batches] == [
        (2, 14, 18, 3),
        (1, 14, 18, 3),
    ]
    assert all(
        len(frame) == 18 * 14 * 3
        for batch in batches
        for frame in batch.frame_buffers
    )
    assert stream.resolved.identity_status == "recorded"
    assert (stream.resolved.fps_num, stream.resolved.fps_den) == (6, 1)
    assert stream.resolved.plane.plane_id == "rgb24"
    assert stream.resolved.plane.channel_order == ("R", "G", "B")
    assert stream.outcome is not None
    assert stream.outcome.kind is WorkingWindowOutcomeKind.COMPLETE
    assert (stream.outcome.delivered_start, stream.outcome.delivered_stop) == (
        2,
        5,
    )
    assert stream.closed

    with open_working_window(
        request, batch_size=1, assets=assets
    ) as one_at_a_time:
        single_batches = list(one_at_a_time)
    assert [
        (frame, raw)
        for batch in batches
        for frame, raw in zip(
            batch.absolute_frame_indices,
            batch.frame_buffers,
            strict=True,
        )
    ] == [
        (frame, raw)
        for batch in single_batches
        for frame, raw in zip(
            batch.absolute_frame_indices,
            batch.frame_buffers,
            strict=True,
        )
    ]


@pytest.mark.parametrize(
    ("start", "stop"),
    [(-1, 1), (1, 1), (2, 1)],
)
def test_invalid_spans_fail_before_opening_media(
    tmp_path: Path,
    start: int,
    stop: int,
) -> None:
    request = WorkingWindowRequest(
        asset_ref=tmp_path / "missing.asset.json",
        expected_asset_id="asset",
        expected_content_sha256="hash",
        start_frame=start,
        stop_frame=stop,
    )
    with pytest.raises(SieveError) as error:
        open_working_window(request)
    assert error.value.code == "WORKING_WINDOW_INVALID"


def test_unregistered_identity_bounds_and_plane_fail_explicitly(
    video: Path,
) -> None:
    missing_sidecar = video.with_suffix(".asset.json")
    raw_request = WorkingWindowRequest(
        asset_ref=video,
        expected_asset_id="asset",
        expected_content_sha256="hash",
        start_frame=0,
        stop_frame=1,
    )
    with pytest.raises(SieveError) as error:
        open_working_window(raw_request)
    assert error.value.code == "ASSET_SIDECAR_MISSING"
    assert not missing_sidecar.exists()

    assets = AssetService()
    initialized = assets.initialize(video, label="source")
    wrong_identity = request_for(initialized, 0, 1)
    wrong_identity = WorkingWindowRequest(
        asset_ref=wrong_identity.asset_ref,
        expected_asset_id="wrong",
        expected_content_sha256=wrong_identity.expected_content_sha256,
        start_frame=0,
        stop_frame=1,
    )
    with pytest.raises(SieveError) as error:
        open_working_window(wrong_identity, assets=assets)
    assert error.value.code == "ASSET_CONTENT_MISMATCH"

    with pytest.raises(SieveError) as error:
        open_working_window(
            request_for(initialized, 0, 1, plane_id="luma"),
            assets=assets,
        )
    assert error.value.code == "MEDIA_PLANE_UNSUPPORTED"

    with pytest.raises(SieveError) as error:
        open_working_window(
            request_for(initialized, 0, 13),
            assets=assets,
        )
    assert error.value.code == "WORKING_WINDOW_INVALID"
    assert error.value.context["declared_stop"] == 12


def test_extent_provenance_retains_the_count_source() -> None:
    assert (
        extent_provenance({"decoded_frame_count": 3})
        is ExtentProvenance.DECODED_COUNT
    )
    assert (
        extent_provenance(
            {
                "decoded_frame_count": None,
                "packet_frame_count": 3,
            }
        )
        is ExtentProvenance.PACKET_COUNT
    )
    assert (
        extent_provenance(
            {
                "decoded_frame_count": None,
                "packet_frame_count": None,
                "container_frame_count": 3,
            }
        )
        is ExtentProvenance.CONTAINER_COUNT
    )
    assert (
        extent_provenance({})
        is ExtentProvenance.DURATION_ESTIMATE
    )


class FakeSession:
    def __init__(
        self,
        metadata: dict[str, object],
        *,
        fail_at: int | None = None,
        reason: str = "decoder_error",
    ) -> None:
        self.metadata = metadata
        self.frame_count = 12
        self.closed = False
        self.fail_at = fail_at
        self.reason = reason
        self.max_widths: list[int | None] = []

    def read_frame_rgb(
        self, frame: int, *, max_width: int | None = None
    ) -> bytes:
        self.max_widths.append(max_width)
        if frame == self.fail_at:
            raise SieveError(
                "FRAME_DECODE_FAILED",
                "fixture decode stopped",
                frame=frame,
                reason=self.reason,
            )
        width = int(self.metadata["width"])
        height = int(self.metadata["height"])
        return bytes([frame]) * width * height * 3

    def close(self) -> None:
        self.closed = True


def fake_metadata(initialized: dict[str, object]) -> dict[str, object]:
    asset = initialized["asset"]
    assert isinstance(asset, dict)
    media = asset["media"]
    assert isinstance(media, dict)
    return {
        "width": media["width"],
        "height": media["height"],
        "fps_num": media["fps_num"],
        "fps_den": media["fps_den"],
        "pixel_format": media["pixel_format"],
        "decoded_frame_count": None,
        "packet_frame_count": None,
        "container_frame_count": 12,
        "duration_seconds": media["duration_seconds"],
        "color_range": media["color_range"],
        "color_space": media["color_space"],
        "color_transfer": media["color_transfer"],
        "color_primaries": media["color_primaries"],
    }


def test_cancellation_delivers_a_bounded_prefix_and_closes(
    video: Path,
) -> None:
    assets = AssetService()
    initialized = assets.initialize(video, label="source")
    fake = FakeSession(fake_metadata(initialized))
    checks = 0

    def cancelled() -> bool:
        nonlocal checks
        checks += 1
        return checks > 2

    stream = open_working_window(
        request_for(initialized, 0, 6),
        batch_size=4,
        cancelled=cancelled,
        assets=assets,
        session_factory=lambda _path: fake,
    )
    with stream:
        batches = list(stream)
    assert [batch.absolute_frame_indices for batch in batches] == [(0, 1)]
    assert fake.max_widths == [None, None]
    assert stream.outcome is not None
    assert stream.outcome.kind is WorkingWindowOutcomeKind.CANCELLED
    assert stream.outcome.delivered_stop == 2
    assert stream.outcome.stopped_at_frame == 2
    assert fake.closed


def test_context_exit_cancels_early_consumer_and_closes(video: Path) -> None:
    assets = AssetService()
    initialized = assets.initialize(video, label="source")
    fake = FakeSession(fake_metadata(initialized))
    stream = open_working_window(
        request_for(initialized, 0, 5),
        assets=assets,
        session_factory=lambda _path: fake,
    )
    with stream:
        assert next(stream).absolute_frame_indices == (0,)
    assert stream.outcome is not None
    assert stream.outcome.kind is WorkingWindowOutcomeKind.CANCELLED
    assert stream.outcome.delivered_stop == 1
    assert fake.closed


def test_clean_eof_truncates_but_ambiguous_failure_raises(
    video: Path,
) -> None:
    assets = AssetService()
    initialized = assets.initialize(video, label="source")

    eof_session = FakeSession(
        fake_metadata(initialized),
        fail_at=2,
        reason="clean_eof",
    )
    eof_stream = open_working_window(
        request_for(initialized, 0, 5),
        batch_size=4,
        assets=assets,
        session_factory=lambda _path: eof_session,
    )
    with eof_stream:
        batches = list(eof_stream)
    assert [batch.absolute_frame_indices for batch in batches] == [(0, 1)]
    assert eof_stream.outcome is not None
    assert eof_stream.outcome.kind is WorkingWindowOutcomeKind.TRUNCATED
    assert eof_stream.outcome.delivered_stop == 2
    assert eof_stream.outcome.stopped_at_frame == 2
    assert eof_session.closed

    failed_session = FakeSession(
        fake_metadata(initialized),
        fail_at=2,
        reason="decoder_error",
    )
    failed_stream = open_working_window(
        request_for(initialized, 0, 5),
        batch_size=1,
        assets=assets,
        session_factory=lambda _path: failed_session,
    )
    with pytest.raises(SieveError) as error:
        with failed_stream:
            list(failed_stream)
    assert error.value.context["reason"] == "decoder_error"
    assert failed_stream.outcome is not None
    assert failed_stream.outcome.kind is WorkingWindowOutcomeKind.FAILED
    assert failed_stream.outcome.delivered_stop == 2
    assert failed_session.closed


def test_unexpected_source_failure_still_closes(video: Path) -> None:
    assets = AssetService()
    initialized = assets.initialize(video, label="source")

    class BrokenSession(FakeSession):
        def read_frame_rgb(
            self, frame: int, *, max_width: int | None = None
        ) -> bytes:
            raise RuntimeError("unexpected backend failure")

    broken = BrokenSession(fake_metadata(initialized))
    stream = open_working_window(
        request_for(initialized, 0, 2),
        assets=assets,
        session_factory=lambda _path: broken,
    )
    with pytest.raises(RuntimeError, match="unexpected backend"):
        with stream:
            list(stream)
    assert stream.outcome is not None
    assert stream.outcome.kind is WorkingWindowOutcomeKind.FAILED
    assert stream.outcome.delivered_stop == 0
    assert broken.closed


def test_media_session_marks_clean_short_read_as_eof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import antscihub_sieve.media.session as session_module

    metadata = {
        "width": 2,
        "height": 2,
        "fps_num": 1,
        "fps_den": 1,
        "decoded_frame_count": None,
        "packet_frame_count": None,
        "container_frame_count": 1,
        "duration_seconds": 1.0,
    }

    class EmptyPipe:
        def read(self, _size: int | None = None) -> bytes:
            return b""

    class CleanDecoder:
        stdout = EmptyPipe()
        stderr = EmptyPipe()

        def poll(self) -> int:
            return 0

        def wait(self, timeout: int) -> int:
            return 0

        def terminate(self) -> None:
            raise AssertionError("cleanly exited decoder was terminated")

        def kill(self) -> None:
            raise AssertionError("cleanly exited decoder was killed")

    monkeypatch.setattr(
        session_module,
        "run_ffprobe",
        lambda _path: metadata,
    )
    monkeypatch.setattr(
        session_module.subprocess,
        "Popen",
        lambda *args, **kwargs: CleanDecoder(),
    )
    session = MediaSession(tmp_path / "fixture.mkv")
    with pytest.raises(SieveError) as error:
        session.read_frame_rgb(0)
    assert error.value.context["reason"] == "clean_eof"
    assert error.value.context["returncode"] == 0
    assert error.value.context["bytes_read"] == 0
    assert error.value.context["expected_bytes"] == 12
    session.close()


def test_gui_snapshot_is_immutable_and_does_not_open_source(
    qtbot,
    video: Path,
) -> None:  # type: ignore[no-untyped-def]
    from antscihub_sieve.application.active_asset import ActiveAssetController
    from antscihub_sieve.gui.isolate_session import IsolateSession

    controller = ActiveAssetController()
    asset = controller.open_asset(video)
    session = IsolateSession()
    session.asset = asset
    session.window_start = 2
    session.window_stop = 5
    request = session.snapshot_working_window_request()

    assert request.expected_asset_id == asset.asset_id
    assert request.expected_content_sha256 == asset.content_sha256
    assert (request.start_frame, request.stop_frame) == (2, 5)
    assert session.media is None
    assert session.decoder is None

    session._generation += 1
    session.window_start = 7
    session.window_stop = 9
    assert (request.start_frame, request.stop_frame) == (2, 5)
    assert not hasattr(request, "asset_generation")
    session.close()


def test_child_working_window_uses_child_media_and_coordinates(
    video: Path,
    tmp_path: Path,
) -> None:
    from antscihub_sieve.application.derivation import DerivationService
    from antscihub_sieve.application.layouts import LayoutService

    assets = AssetService()
    assets.initialize(video, label="source")
    layouts = LayoutService(assets)
    region = layouts.add(video, [1, 2, 12, 10], "child")["region"]
    child = DerivationService(assets, layouts).run(
        video,
        region_ids=[region["region_id"]],
        out=tmp_path / "children",
    )["children"][0]
    child_registered = assets.inspect(child["asset_path"])

    with open_working_window(
        request_for(child_registered, 0, 2),
        batch_size=2,
        assets=assets,
    ) as stream:
        batches = list(stream)
    assert stream.resolved.media_path == Path(child["media_path"])
    assert (stream.resolved.width, stream.resolved.height) == (11, 8)
    assert batches[0].shape == (2, 8, 11, 3)


def test_working_window_diagnostic_reports_structured_outcome(
    video: Path,
) -> None:
    initialized = AssetService().initialize(video, label="source")
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_working_window.py",
            str(initialized["sidecar_path"]),
            "2",
            "5",
            "--batch-size",
            "2",
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["requested_span"] == [2, 5]
    assert result["plane"]["plane_id"] == "rgb24"
    assert [
        batch["absolute_frame_indices"] for batch in result["batches"]
    ] == [[2, 3], [4]]
    assert result["outcome"]["kind"] == "complete"
    assert result["outcome"]["delivered_span"] == [2, 5]
