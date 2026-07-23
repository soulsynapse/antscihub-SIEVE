from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.session import MediaSession


RGB24 = "rgb24"


class ExtentProvenance(str, Enum):
    DECODED_COUNT = "decoded_count"
    PACKET_COUNT = "packet_count"
    CONTAINER_COUNT = "container_count"
    DURATION_ESTIMATE = "duration_estimate"


class WorkingWindowOutcomeKind(str, Enum):
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    TRUNCATED = "truncated"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class WorkingWindowRequest:
    asset_ref: Path
    expected_asset_id: str
    expected_content_sha256: str
    start_frame: int
    stop_frame: int
    plane_id: str = RGB24


@dataclass(frozen=True, slots=True)
class PlaneDescriptor:
    plane_id: str
    width: int
    height: int
    channels: int
    dtype: str
    value_min: int
    value_max: int
    channel_order: tuple[str, ...]
    backend: str
    source_pixel_format: str
    source_color_range: str | None
    source_color_space: str | None
    source_color_transfer: str | None
    source_color_primaries: str | None

    @property
    def per_frame_shape(self) -> tuple[int, int, int]:
        return (self.height, self.width, self.channels)


@dataclass(frozen=True, slots=True)
class ResolvedWorkingWindow:
    sidecar_path: Path
    media_path: Path
    asset_id: str
    content_sha256: str
    identity_status: str
    start_frame: int
    stop_frame: int
    declared_stop: int
    extent_provenance: ExtentProvenance
    fps_num: int
    fps_den: int
    width: int
    height: int
    plane: PlaneDescriptor


@dataclass(frozen=True, slots=True)
class FrameBatch:
    absolute_frame_indices: tuple[int, ...]
    frame_buffers: tuple[bytes, ...]
    plane: PlaneDescriptor

    @property
    def shape(self) -> tuple[int, int, int, int]:
        return (
            len(self.absolute_frame_indices),
            self.plane.height,
            self.plane.width,
            self.plane.channels,
        )


@dataclass(frozen=True, slots=True)
class WorkingWindowOutcome:
    kind: WorkingWindowOutcomeKind
    requested_start: int
    requested_stop: int
    delivered_start: int
    delivered_stop: int
    stopped_at_frame: int | None
    error: SieveError | None = None


class MediaSessionLike(Protocol):
    metadata: dict[str, object]
    frame_count: int
    closed: bool

    def read_frame_rgb(
        self, frame: int, *, max_width: int | None = None
    ) -> bytes: ...

    def close(self) -> None: ...


MediaSessionFactory = Callable[[Path], MediaSessionLike]
CancellationPredicate = Callable[[], bool]


def extent_provenance(metadata: dict[str, object]) -> ExtentProvenance:
    if metadata.get("decoded_frame_count") is not None:
        return ExtentProvenance.DECODED_COUNT
    if metadata.get("packet_frame_count") is not None:
        return ExtentProvenance.PACKET_COUNT
    if metadata.get("container_frame_count") is not None:
        return ExtentProvenance.CONTAINER_COUNT
    return ExtentProvenance.DURATION_ESTIMATE


def _working_window_error(message: str, **context: object) -> SieveError:
    return SieveError("WORKING_WINDOW_INVALID", message, **context)


def _resolve(
    request: WorkingWindowRequest,
    assets: AssetService,
    session_factory: MediaSessionFactory,
) -> tuple[ResolvedWorkingWindow, MediaSessionLike]:
    if isinstance(request.start_frame, bool) or not isinstance(
        request.start_frame, int
    ):
        raise _working_window_error(
            "Working-window start must be an integer",
            start_frame=request.start_frame,
        )
    if isinstance(request.stop_frame, bool) or not isinstance(
        request.stop_frame, int
    ):
        raise _working_window_error(
            "Working-window stop must be an integer",
            stop_frame=request.stop_frame,
        )
    if request.start_frame < 0 or request.stop_frame <= request.start_frame:
        raise _working_window_error(
            "Working-window range must be nonempty and half-open",
            start_frame=request.start_frame,
            stop_frame=request.stop_frame,
        )
    if request.plane_id != RGB24:
        raise SieveError(
            "MEDIA_PLANE_UNSUPPORTED",
            "The current working-window source supports only native rgb24",
            plane_id=request.plane_id,
        )
    if not request.expected_asset_id or not request.expected_content_sha256:
        raise _working_window_error(
            "Working-window requests require stable asset and content identity"
        )

    sidecar_path, _ = assets.resolve(request.asset_ref)
    if not sidecar_path.is_file():
        raise SieveError(
            "ASSET_SIDECAR_MISSING",
            "Working-window requests require a registered asset sidecar",
            path=str(sidecar_path),
        )
    inspected = assets.inspect(sidecar_path)
    asset = inspected["asset"]
    stored_media = asset["media"]
    media_path = Path(inspected["media_path"])

    if (
        asset["asset_id"] != request.expected_asset_id
        or stored_media["content_sha256"]
        != request.expected_content_sha256
    ):
        raise SieveError(
            "ASSET_CONTENT_MISMATCH",
            "Working-window request identity does not match the registered asset",
            path=str(sidecar_path),
            expected_asset_id=request.expected_asset_id,
            actual_asset_id=asset["asset_id"],
            expected_content_sha256=request.expected_content_sha256,
            actual_content_sha256=stored_media["content_sha256"],
        )
    if not media_path.is_file():
        raise SieveError(
            "ASSET_CONTENT_MISMATCH",
            "Registered working-window media is not reachable",
            path=str(media_path),
        )
    if media_path.stat().st_size != int(stored_media["size_bytes"]):
        raise SieveError(
            "ASSET_CONTENT_MISMATCH",
            "Registered working-window media size differs from its sidecar",
            path=str(media_path),
            expected_size=int(stored_media["size_bytes"]),
            actual_size=media_path.stat().st_size,
        )

    session: MediaSessionLike | None = None
    try:
        session = session_factory(media_path)
        metadata = session.metadata
        expected_facts = (
            int(stored_media["width"]),
            int(stored_media["height"]),
            int(stored_media["fps_num"]),
            int(stored_media["fps_den"]),
        )
        actual_facts = (
            int(metadata["width"]),
            int(metadata["height"]),
            int(metadata["fps_num"]),
            int(metadata["fps_den"]),
        )
        if actual_facts != expected_facts:
            raise SieveError(
                "ASSET_CONTENT_MISMATCH",
                "Working-window media facts differ from the registered sidecar",
                path=str(media_path),
                expected=expected_facts,
                actual=actual_facts,
            )

        declared_stop = int(session.frame_count)
        if request.stop_frame > declared_stop:
            raise _working_window_error(
                "Working-window range exceeds the declared media extent",
                start_frame=request.start_frame,
                stop_frame=request.stop_frame,
                declared_stop=declared_stop,
                extent_provenance=extent_provenance(metadata).value,
            )

        width, height, fps_num, fps_den = actual_facts
        plane = PlaneDescriptor(
            plane_id=RGB24,
            width=width,
            height=height,
            channels=3,
            dtype="uint8",
            value_min=0,
            value_max=255,
            channel_order=("R", "G", "B"),
            backend="ffmpeg",
            source_pixel_format=str(metadata.get("pixel_format", "unknown")),
            source_color_range=_optional_text(metadata.get("color_range")),
            source_color_space=_optional_text(metadata.get("color_space")),
            source_color_transfer=_optional_text(
                metadata.get("color_transfer")
            ),
            source_color_primaries=_optional_text(
                metadata.get("color_primaries")
            ),
        )
        resolved = ResolvedWorkingWindow(
            sidecar_path=sidecar_path,
            media_path=media_path,
            asset_id=asset["asset_id"],
            content_sha256=stored_media["content_sha256"],
            identity_status="recorded",
            start_frame=request.start_frame,
            stop_frame=request.stop_frame,
            declared_stop=declared_stop,
            extent_provenance=extent_provenance(metadata),
            fps_num=fps_num,
            fps_den=fps_den,
            width=width,
            height=height,
            plane=plane,
        )
        return resolved, session
    except BaseException:
        if session is not None:
            session.close()
        raise


def _optional_text(value: object) -> str | None:
    return None if value is None else str(value)


class WorkingWindowStream(Iterator[FrameBatch]):
    def __init__(
        self,
        resolved: ResolvedWorkingWindow,
        session: MediaSessionLike,
        *,
        batch_size: int,
        cancelled: CancellationPredicate | None,
    ) -> None:
        self.resolved = resolved
        self._session = session
        self._batch_size = batch_size
        self._cancelled = cancelled
        self._next_frame = resolved.start_frame
        self._delivered_stop = resolved.start_frame
        self._closed = False
        self.outcome: WorkingWindowOutcome | None = None

    @property
    def closed(self) -> bool:
        return self._closed

    def __iter__(self) -> WorkingWindowStream:
        return self

    def __next__(self) -> FrameBatch:
        if self._closed or self.outcome is not None:
            raise StopIteration

        indices: list[int] = []
        buffers: list[bytes] = []
        while (
            len(indices) < self._batch_size
            and self._next_frame < self.resolved.stop_frame
        ):
            if self._cancelled is not None and self._cancelled():
                self._finish(
                    WorkingWindowOutcomeKind.CANCELLED,
                    stopped_at_frame=self._next_frame,
                )
                if indices:
                    return self._batch(indices, buffers)
                raise StopIteration
            frame = self._next_frame
            try:
                raw = self._session.read_frame_rgb(frame)
            except SieveError as exc:
                if exc.context.get("reason") == "clean_eof":
                    self._finish(
                        WorkingWindowOutcomeKind.TRUNCATED,
                        stopped_at_frame=frame,
                        error=exc,
                    )
                    if indices:
                        return self._batch(indices, buffers)
                    raise StopIteration
                self._finish(
                    WorkingWindowOutcomeKind.FAILED,
                    stopped_at_frame=frame,
                    error=exc,
                )
                raise
            except BaseException:
                self._finish(
                    WorkingWindowOutcomeKind.FAILED,
                    stopped_at_frame=frame,
                )
                raise
            indices.append(frame)
            buffers.append(raw)
            self._next_frame += 1

        if not indices:
            self._finish(
                WorkingWindowOutcomeKind.COMPLETE,
                stopped_at_frame=None,
            )
            raise StopIteration

        if self._next_frame >= self.resolved.stop_frame:
            self._finish(
                WorkingWindowOutcomeKind.COMPLETE,
                stopped_at_frame=None,
            )
        return self._batch(indices, buffers)

    def _batch(
        self, indices: list[int], buffers: list[bytes]
    ) -> FrameBatch:
        batch = FrameBatch(
            absolute_frame_indices=tuple(indices),
            frame_buffers=tuple(buffers),
            plane=self.resolved.plane,
        )
        self._delivered_stop = indices[-1] + 1
        if self.outcome is not None:
            self.outcome = WorkingWindowOutcome(
                kind=self.outcome.kind,
                requested_start=self.outcome.requested_start,
                requested_stop=self.outcome.requested_stop,
                delivered_start=self.outcome.delivered_start,
                delivered_stop=self._delivered_stop,
                stopped_at_frame=self.outcome.stopped_at_frame,
                error=self.outcome.error,
            )
        return batch

    def _finish(
        self,
        kind: WorkingWindowOutcomeKind,
        *,
        stopped_at_frame: int | None,
        error: SieveError | None = None,
    ) -> None:
        if self.outcome is None:
            self.outcome = WorkingWindowOutcome(
                kind=kind,
                requested_start=self.resolved.start_frame,
                requested_stop=self.resolved.stop_frame,
                delivered_start=self.resolved.start_frame,
                delivered_stop=self._delivered_stop,
                stopped_at_frame=stopped_at_frame,
                error=error,
            )
        self._close_session()

    def _close_session(self) -> None:
        if not self._closed:
            self._closed = True
            self._session.close()

    def close(self) -> None:
        if self.outcome is None:
            self._finish(
                WorkingWindowOutcomeKind.CANCELLED,
                stopped_at_frame=self._next_frame,
            )
        else:
            self._close_session()

    def __enter__(self) -> WorkingWindowStream:
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()


def open_working_window(
    request: WorkingWindowRequest,
    *,
    batch_size: int = 1,
    cancelled: CancellationPredicate | None = None,
    assets: AssetService | None = None,
    session_factory: MediaSessionFactory = MediaSession,
) -> WorkingWindowStream:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise _working_window_error(
            "Working-window batch size must be an integer",
            batch_size=batch_size,
        )
    if batch_size < 1:
        raise _working_window_error(
            "Working-window batch size must be positive",
            batch_size=batch_size,
        )
    resolved, session = _resolve(
        request,
        assets or AssetService(),
        session_factory,
    )
    return WorkingWindowStream(
        resolved,
        session,
        batch_size=batch_size,
        cancelled=cancelled,
    )
