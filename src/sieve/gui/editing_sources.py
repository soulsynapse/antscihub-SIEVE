































from __future__ import annotations


class EditingSources:


    def __init__(self) -> None:
        self._open: set[str] = set()

    @property
    def active(self) -> bool:

        return bool(self._open)

    @property
    def sources(self) -> frozenset[str]:

        return frozenset(self._open)

    def mark(self, source: str, editing: bool) -> None:






        if editing:
            self._open.add(source)
        else:
            self._open.discard(source)

    def clear(self) -> None:

        self._open.clear()
