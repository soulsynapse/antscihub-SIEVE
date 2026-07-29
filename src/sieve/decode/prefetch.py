from __future__ import annotations

from pathlib import Path
from threading import Condition, Thread
from types import TracebackType
from typing import Self


from sieve.core.machine import available_cpus as available_cpus
from sieve.core.pool_meter import PoolMeter
from sieve.core.types import Frame, VideoMetadata
from sieve.decode.reader import VideoDecodeError, VideoReader


INFERRED_WORKER_CAP = 4


LUMA_WORKER_CAP = 2


def resolve_workers(requested: int | None = None, *, luma: bool = False) -> int:
    if requested is not None:
        return max(requested, 1)
    return min(available_cpus(), LUMA_WORKER_CAP if luma else INFERRED_WORKER_CAP)


class PrefetchFrameSource:
    def __init__(
        self,
        path: Path | str,
        *,
        workers: int | None = None,
        lookahead: int | None = None,
        luma: bool = False,
        meter: PoolMeter | None = None,
    ) -> None:
        self._path = Path(path)
        self._luma = luma
        self._meter = PoolMeter() if meter is None else meter
        self._worker_count = resolve_workers(workers, luma=luma)
        self._lookahead = (
            self._worker_count * 2 if lookahead is None else max(lookahead, 1)
        )
        self._readers = self._open_readers()
        self._metadata = self._readers[0].metadata
        self._state = Condition()
        self._started = False
        self._want = 0
        self._claim = 0
        self._epoch = 0
        self._done: dict[int, Frame] = {}
        self._failed: dict[int, VideoDecodeError] = {}
        self._closed = False
        self._threads = [
            Thread(
                target=self._serve,
                args=(reader,),
                name=f"sieve-decode-{number}",
                daemon=True,
            )
            for number, reader in enumerate(self._readers)
        ]
        for thread in self._threads:
            thread.start()

    def _open_readers(self) -> list[VideoReader]:
        readers: list[VideoReader] = []
        try:
            for _ in range(self._worker_count):
                readers.append(VideoReader(self._path, luma=self._luma))
        except VideoDecodeError:
            for reader in readers:
                reader.close()
            raise
        return readers

    @property
    def luma(self) -> bool:
        return self._luma

    @property
    def metadata(self) -> VideoMetadata:
        return self._metadata

    @property
    def workers(self) -> int:
        return self._worker_count

    @property
    def lookahead(self) -> int:
        return self._lookahead

    @property
    def meter(self) -> PoolMeter:
        return self._meter

    def read(self, index: int) -> Frame:
        if not 0 <= index < self._metadata.frame_count:
            raise VideoDecodeError(
                f"Frame {index} out of range 0..{self._metadata.frame_count - 1}"
            )
        with self._state:
            if not self._started or index != self._want:
                self._restart(index)
            while True:
                if self._closed:
                    raise VideoDecodeError(f"Reader for {self._path} is closed")
                frame = self._done.pop(index, None)
                if frame is not None:
                    self._want = index + 1
                    self._meter.set_depth(len(self._done))
                    self._state.notify_all()
                    return frame
                failure = self._failed.pop(index, None)
                if failure is not None:
                    self._restart(index)
                    raise failure
                self._state.wait()

    def _restart(self, index: int) -> None:
        self._started = True
        self._epoch += 1
        self._want = index
        self._claim = index
        self._done.clear()
        self._failed.clear()
        self._meter.set_depth(0)
        self._state.notify_all()

    def _serve(self, reader: VideoReader) -> None:
        while True:
            with self._state:
                while not self._closed and not self._claimable():
                    self._state.wait()
                if self._closed:
                    return
                epoch = self._epoch
                index = self._claim
                self._claim += 1
            try:
                with self._meter.working():
                    frame = reader.read(index)
            except VideoDecodeError as error:
                self._publish(epoch, index, error=error)
                continue
            self._publish(epoch, index, frame=frame)

    def _claimable(self) -> bool:
        return (
            self._started
            and self._claim < self._want + self._lookahead
            and self._claim < self._metadata.frame_count
        )

    def _publish(
        self,
        epoch: int,
        index: int,
        *,
        frame: Frame | None = None,
        error: VideoDecodeError | None = None,
    ) -> None:
        with self._state:
            if epoch == self._epoch:
                if frame is not None:
                    self._done[index] = frame
                    self._meter.set_depth(len(self._done))
                if error is not None:
                    self._failed[index] = error
            self._state.notify_all()

    def close(self) -> None:
        with self._state:
            if self._closed:
                return
            self._closed = True
            self._state.notify_all()
        for thread in self._threads:
            thread.join()
        for reader in self._readers:
            reader.close()
        with self._state:
            self._done.clear()
            self._failed.clear()
            self._meter.set_depth(0)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
