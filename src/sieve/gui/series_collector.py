






















from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

import numpy as np
from numpy.typing import NDArray

from sieve.pipeline.executor import FrameResult


@dataclass(frozen=True, slots=True)
class CollectedSeries:



    start_index: int

    data: NDArray[np.float32]


@dataclass(frozen=True, slots=True)
class CollectedRows:








    start_index: int

    rows: tuple[NDArray[np.float32], ...]


class SeriesCollector:







    def __init__(self, node_id: str) -> None:
        self._node_id = node_id
        self._lock = Lock()
        self._revision: int | None = None
        self._start: int | None = None
        self._rows: list[NDArray[np.float32]] = []

    @property
    def node_id(self) -> str:

        return self._node_id

    def start(self, revision: int) -> None:






        with self._lock:
            self._revision = revision
            self._start = None
            self._rows = []

    def add(self, revision: int, result: FrameResult) -> None:







        frame = result.outputs.get(self._node_id)
        if frame is None:
            return
        row = np.asarray(frame.data, np.float32)
        with self._lock:
            if revision != self._revision:
                return
            if self._start is None:
                self._start = result.index
            expected = self._start + len(self._rows)
            if result.index != expected:
                raise ValueError(
                    f"series for {self._node_id!r} expected frame {expected}, got "
                    f"{result.index}; a gap here would be a silent hole in the detector's input"
                )
            self._rows.append(row)

    def snapshot(self, revision: int) -> CollectedSeries | None:
















        with self._lock:
            if revision != self._revision or self._start is None or not self._rows:
                return None
            return CollectedSeries(
                start_index=self._start, data=np.stack(self._rows).astype(np.float32, copy=False)
            )

    def snapshot_rows(self, revision: int) -> CollectedRows | None:








        with self._lock:
            if revision != self._revision or self._start is None or not self._rows:
                return None
            return CollectedRows(start_index=self._start, rows=tuple(self._rows))

    def take(self, revision: int) -> CollectedSeries | None:













        return self.snapshot(revision)
