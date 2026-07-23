from __future__ import annotations

import subprocess
import struct
import zlib
from fractions import Fraction
from pathlib import Path
from typing import Any

from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.probe import expected_frame_count, run_ffprobe
from antscihub_sieve.media.process import CREATE_NO_WINDOW


class MediaSession:
    """A reusable metadata/seek facade; FFmpeg performs precise single-frame decode."""

    def __init__(self, media_path: Path) -> None:
        self.path = media_path
        self.metadata = run_ffprobe(media_path)
        self.closed = False
        self._decoder: subprocess.Popen[bytes] | None = None
        self._next_frame: int | None = None
        self._decoder_output_size: tuple[int, int] | None = None

    @property
    def frame_count(self) -> int:
        return expected_frame_count(self.metadata)

    def timestamp_for_frame(self, frame: int) -> Fraction:
        if frame < 0 or frame >= self.frame_count:
            raise SieveError("FRAME_DECODE_FAILED", "Frame index is outside the video", frame=frame)
        return Fraction(frame * self.metadata["fps_den"], self.metadata["fps_num"])

    def resolve_time(self, seconds: float) -> int:
        frame = int(Fraction(str(seconds)) * self.metadata["fps_num"] / self.metadata["fps_den"])
        return min(max(0, frame), self.frame_count - 1)

    def _stop_decoder(self) -> None:
        decoder, self._decoder = self._decoder, None
        self._next_frame = None
        self._decoder_output_size = None
        if decoder is not None:
            if decoder.poll() is None:
                decoder.terminate()
                try:
                    decoder.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    decoder.kill()

    def interrupt(self) -> None:
        """Stop an in-flight frame read so asset navigation does not wait on decoding."""
        self._stop_decoder()

    def scaled_dimensions(self, max_width: int | None = None) -> tuple[int, int]:
        width = int(self.metadata["width"])
        height = int(self.metadata["height"])
        if max_width is None or width <= max_width:
            return width, height
        scaled_height = max(2, round(height * max_width / width))
        if scaled_height % 2:
            scaled_height += 1
        return max_width, scaled_height

    def read_frame_rgb(
        self, frame: int, *, max_width: int | None = None
    ) -> bytes:
        if self.closed:
            raise SieveError("FRAME_DECODE_FAILED", "Media session is closed")
        timestamp = self.timestamp_for_frame(frame)
        output_size = self.scaled_dimensions(max_width)
        if (
            self._decoder is None
            or self._next_frame != frame
            or self._decoder_output_size != output_size
        ):
            self._stop_decoder()
            args = ["ffmpeg", "-v", "error", "-ss", f"{float(timestamp):.12f}", "-i", str(self.path),
                    "-map", "0:v:0"]
            if output_size != (
                int(self.metadata["width"]),
                int(self.metadata["height"]),
            ):
                args += [
                    "-vf",
                    f"scale={output_size[0]}:{output_size[1]}:flags=area",
                ]
            args += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            try:
                self._decoder = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
            except OSError as exc:
                raise SieveError("FRAME_DECODE_FAILED", "FFmpeg decoder could not be started", detail=str(exc)) from exc
            self._next_frame = frame
            self._decoder_output_size = output_size
        decoder = self._decoder; assert decoder.stdout is not None
        expected = output_size[0] * output_size[1] * 3
        chunks = bytearray()
        while len(chunks) < expected:
            chunk = decoder.stdout.read(expected - len(chunks))
            if not chunk:
                break
            chunks.extend(chunk)
        if len(chunks) != expected:
            detail = decoder.stderr.read().decode(errors="replace") if decoder.stderr else ""
            self._stop_decoder()
            raise SieveError("FRAME_DECODE_FAILED", "Could not decode requested frame", frame=frame,
                             path=str(self.path), detail=detail.strip())
        self._next_frame = frame + 1
        return bytes(chunks)

    def read_frame(self, frame: int, out: Path | None = None) -> bytes:
        raw = self.read_frame_rgb(frame)
        width, height = self.metadata["width"], self.metadata["height"]
        signature = b"\x89PNG\r\n\x1a\n"
        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
        scanlines = b"".join(b"\x00" + raw[y * width * 3:(y + 1) * width * 3] for y in range(height))
        png = signature + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b"")
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(png)
        return png

    def seek(self, frame: int) -> bytes:
        return self.read_frame(frame)

    def close(self) -> None:
        self._stop_decoder()
        self.closed = True
