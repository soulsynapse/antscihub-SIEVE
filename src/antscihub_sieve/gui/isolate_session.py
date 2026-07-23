from __future__ import annotations

import threading
from fractions import Fraction

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from antscihub_sieve.application.active_asset import ActiveAsset
from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.session import MediaSession


ISOLATE_DISPLAY_MAX_WIDTH = 1280


class IsolateDecodeThread(QThread):
    frame_decoded = pyqtSignal(int, int, bytes, int, int)
    decode_failed = pyqtSignal(int, str)

    def __init__(self, generation: int, session: MediaSession) -> None:
        super().__init__()
        self.generation = generation
        self.session = session
        self._condition = threading.Condition()
        self._requested: int | None = None
        self._stopping = False

    def request(self, frame: int) -> None:
        with self._condition:
            self._requested = frame
            self._condition.notify()

    def stop(self) -> None:
        with self._condition:
            self._stopping = True
            self._condition.notify()
        self.session.interrupt()

    def run(self) -> None:
        while True:
            with self._condition:
                while self._requested is None and not self._stopping:
                    self._condition.wait()
                if self._stopping:
                    return
                frame = self._requested
                self._requested = None
            try:
                width, height = self.session.scaled_dimensions(
                    ISOLATE_DISPLAY_MAX_WIDTH
                )
                raw = self.session.read_frame_rgb(
                    frame, max_width=ISOLATE_DISPLAY_MAX_WIDTH
                )
            except SieveError as exc:
                if not self._stopping:
                    self.decode_failed.emit(
                        self.generation, f"{exc.code}: {exc.message}"
                    )
                continue
            with self._condition:
                if self._requested is not None:
                    continue
            self.frame_decoded.emit(
                self.generation, frame, raw, width, height
            )


class IsolateSession(QObject):
    state_changed = pyqtSignal()
    frame_ready = pyqtSignal(int, bytes, int, int)
    error_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.asset: ActiveAsset | None = None
        self.media: MediaSession | None = None
        self.decoder: IsolateDecodeThread | None = None
        self.frame_count = 0
        self.fps_num = 1
        self.fps_den = 1
        self.extent_is_estimated = False
        self.window_start = 0
        self.window_stop = 0
        self.current_frame = 0
        self.displayed_frame: int | None = None
        self.playing = False
        self.error_text = ""
        self._generation = 0
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._play_tick)
        self.scrub_timer = QTimer(self)
        self.scrub_timer.setSingleShot(True)
        self.scrub_timer.setInterval(60)
        self.scrub_timer.timeout.connect(self.settle_timeline_scrub)

    @property
    def loaded(self) -> bool:
        return self.media is not None and self.frame_count > 0

    @property
    def window_length(self) -> int:
        return self.window_stop - self.window_start

    @property
    def can_loop(self) -> bool:
        return self.loaded and self.frame_count >= 2 and self.window_length >= 2

    def frames_for_seconds(self, seconds: float) -> int:
        frames = Fraction(str(seconds)) * self.fps_num / self.fps_den
        return max(1, round(frames))

    def frame_at_seconds(self, seconds: float) -> int:
        frames = Fraction(str(seconds)) * self.fps_num / self.fps_den
        return max(0, round(frames))

    def seconds_for_frame(self, frame: int) -> float:
        return float(Fraction(frame * self.fps_den, self.fps_num))

    def open_asset(self, asset: ActiveAsset) -> None:
        self.scrub_timer.stop()
        self._close_media()
        self._generation += 1
        self.asset = asset
        self.error_text = ""
        self.state_changed.emit()
        try:
            media = MediaSession(asset.video_path)
            frame_count = media.frame_count
            if frame_count < 1:
                raise SieveError(
                    "MEDIA_PROBE_FAILED", "Video contains no decodable frames"
                )
        except SieveError as exc:
            self.asset = asset
            self.error_text = f"{exc.code}: {exc.message}"
            self.error_changed.emit(self.error_text)
            self.state_changed.emit()
            return

        self.media = media
        self.frame_count = frame_count
        self.fps_num = int(media.metadata["fps_num"])
        self.fps_den = int(media.metadata["fps_den"])
        self.extent_is_estimated = (
            media.metadata.get("decoded_frame_count") is None
        )
        default_length = min(frame_count, self.frames_for_seconds(10.0))
        if frame_count >= 2:
            default_length = max(2, default_length)
        self.window_start = 0
        self.window_stop = default_length
        self.current_frame = 0
        self.displayed_frame = None
        self.playing = False
        self.play_timer.setInterval(
            max(1, round(1000 * self.fps_den / self.fps_num))
        )
        self.decoder = IsolateDecodeThread(self._generation, media)
        self.decoder.frame_decoded.connect(self._frame_decoded)
        self.decoder.decode_failed.connect(self._decode_failed)
        self.decoder.start()
        self.state_changed.emit()
        self.request_frame(0)

    def _close_media(self) -> None:
        self.scrub_timer.stop()
        self.pause()
        self._generation += 1
        decoder, self.decoder = self.decoder, None
        media, self.media = self.media, None
        if decoder is not None:
            decoder.stop()
            decoder.wait(3000)
            decoder.deleteLater()
        if media is not None:
            media.close()
        self.frame_count = 0
        self.extent_is_estimated = False
        self.window_start = self.window_stop = self.current_frame = 0
        self.displayed_frame = None

    def close(self) -> None:
        self._close_media()
        self.asset = None
        self.state_changed.emit()

    def ui_minimum_length(self) -> int:
        if self.frame_count < 2:
            return self.frame_count
        return min(self.frame_count, max(2, self.frames_for_seconds(0.2)))

    def ui_maximum_length(self) -> int:
        return min(self.frame_count, max(1, self.frames_for_seconds(60.0)))

    def set_window_start(self, start: int) -> None:
        self._settle_window(start, self.window_length)

    def set_window_length(self, length: int) -> None:
        self._settle_window(self.window_start, length)

    def _settle_window(self, start: int, length: int) -> None:
        if not self.loaded:
            return
        length = min(max(1, length), self.frame_count)
        start = min(max(0, start), self.frame_count - length)
        stop = start + length
        changed = (start, stop) != (self.window_start, self.window_stop)
        self.window_start, self.window_stop = start, stop
        target = min(max(self.current_frame, start), stop - 1)
        if changed or target != self.current_frame:
            self.request_frame(target)
        else:
            self.state_changed.emit()

    def request_frame(self, frame: int) -> None:
        if not self.loaded or self.decoder is None:
            return
        frame = min(max(self.window_start, frame), self.window_stop - 1)
        self.current_frame = frame
        self.state_changed.emit()
        self.decoder.request(frame)

    def timeline_seek(self, frame: int) -> None:
        if not self.loaded:
            return
        self._position_timeline(frame)
        self.request_frame(self.current_frame)

    def timeline_scrub(self, frame: int) -> None:
        if not self.loaded:
            return
        self.pause()
        self._position_timeline(frame)
        self.state_changed.emit()
        self.scrub_timer.start()

    def settle_timeline_scrub(self, frame: int | None = None) -> None:
        self.scrub_timer.stop()
        if frame is not None:
            self._position_timeline(frame)
        self.request_frame(self.current_frame)

    def _position_timeline(self, frame: int) -> None:
        if not self.loaded:
            return
        frame = min(max(0, frame), self.frame_count - 1)
        if not self.window_start <= frame < self.window_stop:
            length = self.window_length
            start = min(
                max(0, frame - length // 2),
                self.frame_count - length,
            )
            self.window_start, self.window_stop = start, start + length
        self.current_frame = frame

    def toggle_play(self) -> None:
        if not self.can_loop:
            return
        self.playing = not self.playing
        if self.playing:
            self.play_timer.start()
        else:
            self.play_timer.stop()
        self.state_changed.emit()

    def pause(self) -> None:
        if self.playing:
            self.playing = False
            self.state_changed.emit()
        self.play_timer.stop()

    def step(self, delta: int) -> None:
        if not self.loaded:
            return
        self.pause()
        self.request_frame(self.current_frame + delta)

    def seek_home(self) -> None:
        self.pause()
        self.request_frame(self.window_start)

    def seek_end(self) -> None:
        self.pause()
        self.request_frame(self.window_stop - 1)

    def _play_tick(self) -> None:
        if not self.playing or not self.can_loop:
            return
        if self.displayed_frame != self.current_frame:
            return
        next_frame = (
            self.window_start
            if self.current_frame >= self.window_stop - 1
            else self.current_frame + 1
        )
        self.request_frame(next_frame)

    def _frame_decoded(
        self,
        generation: int,
        frame: int,
        raw: bytes,
        width: int,
        height: int,
    ) -> None:
        if (
            generation != self._generation
            or self.media is None
            or frame != self.current_frame
        ):
            return
        self.displayed_frame = frame
        self.frame_ready.emit(
            frame,
            raw,
            width,
            height,
        )
        self.state_changed.emit()

    def _decode_failed(self, generation: int, message: str) -> None:
        if generation != self._generation:
            return
        self.pause()
        self.error_text = message
        self.error_changed.emit(message)
        self._close_media()
        self.state_changed.emit()
