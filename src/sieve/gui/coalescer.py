





































from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, auto
from time import perf_counter


class RequestKind(StrEnum):




    EXACT = auto()


    SCRUB = auto()


    PLAYBACK = auto()


@dataclass(frozen=True, slots=True)
class Request:








    index: int
    kind: RequestKind
    sequence: int
    generation: int


@dataclass(frozen=True, slots=True)
class Arrival:









    request: Request | None

    display: bool

    stale: bool


def _outranks(kind: RequestKind, pending: Request) -> bool:

    return pending.kind is not RequestKind.EXACT or kind is RequestKind.EXACT


class RequestCoalescer:













    def __init__(self, *, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock
        self._in_flight: Request | None = None
        self._issued_at = 0.0
        self._pending: Request | None = None



        self._sequence = 0
        self._displayed_sequence = 0





        self._generation = 0



    @property
    def in_flight(self) -> Request | None:

        return self._in_flight

    @property
    def pending(self) -> Request | None:

        return self._pending

    @property
    def generation(self) -> int:

        return self._generation



    def request(self, index: int, kind: RequestKind) -> Request | None:






        if self._in_flight is None:
            return self._issue(self._stamp(index, kind))
        if self._pending is not None and not _outranks(kind, self._pending):
            return None
        self._pending = self._stamp(index, kind)
        return None

    def served_without_decode(self, kind: RequestKind) -> None:








        self._sequence += 1
        self._displayed_sequence = self._sequence
        if self._pending is not None and _outranks(kind, self._pending):
            self._pending = None

    def new_generation(self) -> None:









        self._generation += 1
        self._pending = None



    def arrived(self) -> Arrival:

        request = self._in_flight
        if request is None or request.generation != self._generation:
            return Arrival(request=request, display=False, stale=True)

        display = request.kind is RequestKind.EXACT or request.sequence > self._displayed_sequence
        self._displayed_sequence = max(self._displayed_sequence, request.sequence)
        return Arrival(request=request, display=display, stale=False)

    def round_trip_ms(self) -> float:






        return (self._clock() - self._issued_at) * 1000.0

    def drain(self) -> Request | None:






        self._in_flight = None
        if self._pending is None:
            return None
        request, self._pending = self._pending, None
        return self._issue(request)



    def _stamp(self, index: int, kind: RequestKind) -> Request:
        self._sequence += 1
        return Request(
            index=index,
            kind=kind,
            sequence=self._sequence,
            generation=self._generation,
        )

    def _issue(self, request: Request) -> Request:
        self._in_flight = request
        self._issued_at = self._clock()
        return request
