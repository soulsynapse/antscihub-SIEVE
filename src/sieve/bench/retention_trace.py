















































from __future__ import annotations

import json
import os
from collections import OrderedDict, deque
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import IO, Protocol






TRACE_ENV_VAR = "SIEVE_RETENTION_TRACE"


PUT = "put"

GET = "get"


FROM_RING = "ring"



FROM_CACHE = "cache"

FROM_DECODE = "decode"



UNKNOWN_PLAYHEAD = -1






SCRUB_KIND = "scrub"


@dataclass(frozen=True, slots=True)
class AccessEvent:



    op: str

    index: int

    playhead: int

    kind: str

    source: str

    frontier: int | None


class TraceRecorder:

























    def __init__(self, path: Path | None = None) -> None:
        self._lock = Lock()
        self._path = path
        self._stream: IO[str] | None = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._stream = path.open("w", encoding="utf-8", newline="\n", buffering=1)

    @property
    def enabled(self) -> bool:

        return self._stream is not None

    @property
    def path(self) -> Path | None:

        return self._path

    def record(self, event: AccessEvent) -> None:

        stream = self._stream
        if stream is None:
            return
        line = json.dumps(asdict(event), separators=(",", ":"))
        with self._lock:
            stream.write(line + "\n")

    def close(self) -> None:

        with self._lock:
            if self._stream is not None:
                self._stream.close()
                self._stream = None


def recorder_from_env(environ: Mapping[str, str] | None = None) -> TraceRecorder:

    source = os.environ if environ is None else environ
    path = source.get(TRACE_ENV_VAR, "").strip()
    return TraceRecorder(Path(path)) if path else TraceRecorder()






TRACE = recorder_from_env()


def load_trace(path: Path) -> tuple[AccessEvent, ...]:






    events: list[AccessEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            fields = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(AccessEvent(**fields))
    return tuple(events)





class RetentionSim(Protocol):









    name: str

    def get(self, index: int) -> bool:

        ...

    def put(self, index: int, playhead: int, frontier: int | None) -> None:

        ...

    def __len__(self) -> int:

        ...


class RingSim:







    name = "ring"

    def __init__(self, capacity_frames: int) -> None:
        self._capacity = max(capacity_frames, 1)
        self._order: deque[int] = deque()
        self._kept: set[int] = set()

    def get(self, index: int) -> bool:
        return index in self._kept

    def put(self, index: int, playhead: int, frontier: int | None) -> None:
        del playhead, frontier
        if index in self._kept:
            return
        self._kept.add(index)
        self._order.append(index)
        while len(self._order) > self._capacity:
            self._kept.discard(self._order.popleft())

    def __len__(self) -> int:
        return len(self._kept)


class LruSim:


    name = "lru"

    def __init__(self, capacity_frames: int) -> None:
        self._capacity = max(capacity_frames, 1)
        self._kept: OrderedDict[int, None] = OrderedDict()

    def get(self, index: int) -> bool:
        if index not in self._kept:
            return False
        self._kept.move_to_end(index)
        return True

    def put(self, index: int, playhead: int, frontier: int | None) -> None:
        del playhead, frontier
        self._kept[index] = None
        self._kept.move_to_end(index)
        while len(self._kept) > self._capacity:
            self._kept.popitem(last=False)

    def __len__(self) -> int:
        return len(self._kept)


class PlayheadDistanceSim:








    name = "playhead-distance"

    def __init__(self, capacity_frames: int) -> None:
        self._capacity = max(capacity_frames, 1)
        self._kept: set[int] = set()

    def get(self, index: int) -> bool:
        return index in self._kept

    def put(self, index: int, playhead: int, frontier: int | None) -> None:
        self._kept.add(index)
        while len(self._kept) > self._capacity:
            victim = self._victim(playhead, frontier)
            if victim is None:
                break
            self._kept.discard(victim)

    def _victim(self, playhead: int, frontier: int | None) -> int | None:











        candidates = [index for index in self._kept if index != frontier]
        if not candidates:
            return None
        return max(candidates, key=lambda index: (abs(index - playhead), index))

    def __len__(self) -> int:
        return len(self._kept)



POLICIES = (RingSim, LruSim, PlayheadDistanceSim)





@dataclass(frozen=True, slots=True)
class ReplayScore:


    policy: str
    requests: int
    hits: int
    scrub_requests: int
    scrub_hits: int
    worst_miss_run: int

    @property
    def hit_rate(self) -> float:

        return self.hits / self.requests if self.requests else 0.0

    @property
    def scrub_hit_rate(self) -> float:

        return self.scrub_hits / self.scrub_requests if self.scrub_requests else 0.0


def replayable(events: Iterable[AccessEvent]) -> Iterator[AccessEvent]:




    for event in events:
        if event.op == PUT or event.source != FROM_CACHE:
            yield event


def replay(events: Sequence[AccessEvent], policy: RetentionSim) -> ReplayScore:






    playhead = next((event.playhead for event in events if event.playhead != UNKNOWN_PLAYHEAD), 0)
    requests = hits = scrub_requests = scrub_hits = 0
    miss_run = worst_miss_run = 0

    for event in replayable(events):
        if event.op == PUT:
            policy.put(event.index, playhead, event.frontier)
            continue
        requests += 1
        hit = policy.get(event.index)
        if hit:
            hits += 1
            miss_run = 0
        else:
            miss_run += 1
            worst_miss_run = max(worst_miss_run, miss_run)
        if event.kind == SCRUB_KIND:
            scrub_requests += 1
            scrub_hits += int(hit)
        playhead = event.index

    return ReplayScore(
        policy=policy.name,
        requests=requests,
        hits=hits,
        scrub_requests=scrub_requests,
        scrub_hits=scrub_hits,
        worst_miss_run=worst_miss_run,
    )


def compare(events: Sequence[AccessEvent], capacity_frames: int) -> tuple[ReplayScore, ...]:







    return tuple(replay(events, policy(capacity_frames)) for policy in POLICIES)
