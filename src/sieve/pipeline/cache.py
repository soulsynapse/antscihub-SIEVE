






























from __future__ import annotations

from typing import Protocol, runtime_checkable

from sieve.core.types import Frame


@runtime_checkable
class FrameStore(Protocol):








    def get(self, key: str, index: int) -> Frame | None:






        ...

    def put(self, key: str, index: int, frame: Frame) -> None:








        ...


class MemoryFrameStore:









    def __init__(self) -> None:
        self._frames: dict[tuple[str, int], Frame] = {}

    def __len__(self) -> int:

        return len(self._frames)

    def get(self, key: str, index: int) -> Frame | None:

        return self._frames.get((key, index))

    def put(self, key: str, index: int, frame: Frame) -> None:

        self._frames[(key, index)] = frame

    def clear(self) -> None:

        self._frames.clear()


class NullFrameStore:








    def get(self, key: str, index: int) -> Frame | None:

        return None

    def put(self, key: str, index: int, frame: Frame) -> None:
        pass
