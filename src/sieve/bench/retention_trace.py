"""What the viewport asked for, what it got, and what the render kept.

`docs/todo/proxy-retention-policy.md` proposes replacing the render ring's LRU
with a distance-from-playhead rule, and then refuses to adopt it on the
strength of the argument: the rule is a reasoned guess, and the stated check is
to record a real tuning session and replay it through candidate policies. This
module is that check's two halves — the recorder that produces a trace and the
simulator that scores one — with the policy question itself left open.

**Why a trace at all, rather than instrumenting the ring in place.** Comparing
retention policies by running each one is comparing sessions, not policies: a
human does not scrub the same way twice, and the difference between two runs is
larger than the difference the experiment is looking for. One trace replayed
three times holds the session fixed.

**Two operations, because a retention store has two inputs.** The ring is
filled by the render (`put`) and queried by the player (`get`), and a trace of
queries alone cannot be replayed — a policy needs to know what was offered to
it before it can be scored on what it kept. So both are recorded, through one
process-wide recorder, exactly as `bench/metrics.py` holds one process-wide
bus: the render thread and the GUI thread write to the same file, in the order
the two actually interleaved, which is the ordering the eviction arithmetic
depends on.

**What the replay cannot know, stated up front.** Three limits, none of them
fixable by a bigger trace:

* *The get sequence is mildly counterfactual.* Playback folds at the render
  frontier, which is policy-independent; but scrub degradation
  (`gui/transport/scrub_policy.py`) triggers on measured latency, so a policy with a
  better hit rate would have degraded later and asked for slightly different
  frames. The put sequence is not affected — the render produces what it
  produces.
* *Stall is counted in misses, not milliseconds.* A replay cannot know what a
  decode would have cost for a frame that run never decoded, so
  `ReplayScore.worst_miss_run` is the longest run of consecutive misses. It is
  a proxy, and it is the honest one: reporting a millisecond figure derived
  from an average decode would be a number that looks measured.
* *The playhead at eviction time is reconstructed.* A `put` happens on the
  render thread, which does not know where the user is looking, so the
  simulator carries the playhead forward from the last `get`. That is not an
  artefact of the trace: a distance-from-playhead policy in the real ring would
  learn the playhead the same way, from the player telling it.

Qt-free, and the `headless` contract in `.importlinter` enforces it — the ring
and the player import this, never the reverse.
"""

from __future__ import annotations

import json
import os
from collections import OrderedDict, deque
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import IO, Protocol

from sieve.core.request_intent import RequestKind

#: Environment variable holding the path a session writes its trace to. An
#: environment variable rather than a preference on purpose: this is a
#: developer's instrument for one experiment, not a setting a user of the
#: application would ever have a reason to find, and a preference would have to
#: be explained in the dialog that `gui/preferences_dialog.py` renders.
TRACE_ENV_VAR = "SIEVE_RETENTION_TRACE"

#: The render produced a frame and offered it to the ring.
PUT = "put"
#: The player asked for a frame.
GET = "get"

#: Served from the render ring — the frames this experiment is about.
FROM_RING = "ring"
#: Served from the scrub proxy cache, before the ring was consulted. Recorded
#: for context and excluded from the replay: a cache hit costs nothing under
#: every candidate policy, so counting it would dilute all of them equally.
FROM_CACHE = "cache"
#: Not retained anywhere; the decode thread was asked.
FROM_DECODE = "decode"

#: `playhead` on a `put`: the render thread does not know where the user is
#: looking. See the module docstring on reconstruction.
UNKNOWN_PLAYHEAD = -1


@dataclass(frozen=True, slots=True)
class AccessEvent:
    """One thing that happened to the retention store, in session order."""

    #: `PUT` or `GET`.
    op: str
    #: The frame index offered or asked for.
    index: int
    #: Where the playhead was *before* this request, or `UNKNOWN_PLAYHEAD`.
    playhead: int
    #: `RequestKind`'s value for a get; empty for a put.
    kind: str
    #: `FROM_RING` / `FROM_CACHE` / `FROM_DECODE` for a get; empty for a put.
    source: str
    #: The render frontier at the moment, or None when no render has produced.
    frontier: int | None


class TraceRecorder:
    """Appends events to a JSON Lines file, or does nothing.

    JSON Lines rather than a binary format or a CSV for one reason each: the
    file is appended to from two threads and must stay readable if the session
    is killed mid-render, which rules out anything with a trailer; and the
    `frontier` column is genuinely nullable, which a CSV would render as an
    empty field indistinguishable from frame zero.

    A recorder with no path is the ordinary case and must cost nothing — the
    `enabled` check is a bare attribute read, ahead of any event construction,
    so an unmonitored session does not allocate a dataclass per decoded frame.

    **Line buffered on purpose, so nothing owns closing it.** The two writers
    shut down independently — the player's decode thread and the preview
    runner's render thread — and whichever closed the recorder first would
    silently drop the other's remaining events, which is a trace that looks
    complete and is not. A write syscall per event is a price an instrument
    that is off by default can pay; `close` exists for tests, not for the
    trace's integrity.

    Not silent about failure. A path that cannot be opened raises here, at
    construction, rather than leaving a session that appears to be recording
    and produces an empty file — rule 6 applies to instruments too.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._lock = Lock()
        self._path = path
        self._stream: IO[str] | None = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._stream = path.open("w", encoding="utf-8", newline="\n", buffering=1)

    @property
    def enabled(self) -> bool:
        """Whether anything is being written. Check before building an event."""
        return self._stream is not None

    @property
    def path(self) -> Path | None:
        """Where the trace is being written, or None."""
        return self._path

    def record(self, event: AccessEvent) -> None:
        """Append `event`. Safe from any thread; a no-op when disabled."""
        stream = self._stream
        if stream is None:
            return
        line = json.dumps(asdict(event), separators=(",", ":"))
        with self._lock:
            stream.write(line + "\n")

    def close(self) -> None:
        """Flush and close. Idempotent, because teardown runs on two paths."""
        with self._lock:
            if self._stream is not None:
                self._stream.close()
                self._stream = None


def recorder_from_env(environ: Mapping[str, str] | None = None) -> TraceRecorder:
    """A recorder writing to `TRACE_ENV_VAR`'s path, or a disabled one."""
    source = os.environ if environ is None else environ
    path = source.get(TRACE_ENV_VAR, "").strip()
    return TraceRecorder(Path(path)) if path else TraceRecorder()


#: The process-wide recorder. A default rather than a requirement, for the
#: reason `bench/metrics.py`'s `METRICS` is: every writer takes a recorder, so
#: a test holds its own and hears only itself, and the ordinary case is not two
#: subsystems each constructing one and writing two half-traces.
TRACE = recorder_from_env()


def load_trace(path: Path) -> tuple[AccessEvent, ...]:
    """Read a trace file back. A truncated final line is dropped, not raised.

    Truncation is the expected shape of a trace from a session that was killed
    — which is how a long render is usually ended — and refusing to load one
    would throw away the whole session for its last event.
    """
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


# ---- the candidate policies ------------------------------------------------


class RetentionSim(Protocol):
    """A retention policy under simulation: what it keeps and what it drops.

    Deliberately not the interface `RenderFrameRing` would implement. These
    hold indices, not images, because the experiment is about *which* frames a
    rule keeps and a QImage would make the harness need a Qt runtime to answer
    a question that has none in it.
    """

    #: How the policy is named in a `ReplayScore` and in the finding.
    name: str

    def get(self, index: int) -> bool:
        """Whether `index` is retained. A hit may update the policy's state."""
        ...

    def put(self, index: int, playhead: int, frontier: int | None) -> None:
        """Offer `index`, evicting to capacity under this policy's rule."""
        ...

    def __len__(self) -> int:
        """How many frames are currently retained."""
        ...


class RingSim:
    """Plain ring: the oldest frame produced is the first dropped.

    The incumbent's honest baseline and the one to beat. `RenderFrameRing`
    today is an LRU, but under a *render* — which touches every frame once, in
    order — an LRU with no reads degenerates to exactly this.
    """

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
    """What the ring is today: least *recently used*, reads counting as use."""

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
    """The proposal: drop the retained frame farthest from the playhead.

    Keeps one contiguous interval around where the user is looking, growing
    toward the frontier. The frontier itself is pinned regardless of distance,
    because follow-the-render mode displays it and evicting it would blank the
    pane at the one moment the user is watching it fill.
    """

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
        """The farthest retained frame from the playhead, frontier excepted.

        Ties broken toward the higher index, so a playhead sitting between a
        warmed region behind it and the render's advance ahead of it gives up
        the newer frame — the render is about to produce it again anyway.

        `None` is the empty-candidates case, which cannot happen while the
        capacity is at least one (at most one retained frame is the frontier,
        so the exception can never exclude everything). It is here because the
        caller's loop has to terminate on something other than an assumption.
        """
        candidates = [index for index in self._kept if index != frontier]
        if not candidates:
            return None
        return max(candidates, key=lambda index: (abs(index - playhead), index))

    def __len__(self) -> int:
        return len(self._kept)


#: Every policy the item named, in the order the finding should report them.
POLICIES = (RingSim, LruSim, PlayheadDistanceSim)


# ---- the replay ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReplayScore:
    """How one policy would have served one recorded session."""

    policy: str
    requests: int
    hits: int
    scrub_requests: int
    scrub_hits: int
    worst_miss_run: int

    @property
    def hit_rate(self) -> float:
        """Fraction of replayed requests served without a decode."""
        return self.hits / self.requests if self.requests else 0.0

    @property
    def scrub_hit_rate(self) -> float:
        """The same, over drag requests only — the latency the user feels."""
        return self.scrub_hits / self.scrub_requests if self.scrub_requests else 0.0


def replayable(events: Iterable[AccessEvent]) -> Iterator[AccessEvent]:
    """The events a replay acts on: every put, and every get the ring saw.

    Gets served from the scrub proxy cache are dropped — see `FROM_CACHE`.
    """
    for event in events:
        if event.op == PUT or event.source != FROM_CACHE:
            yield event


def replay(events: Sequence[AccessEvent], policy: RetentionSim) -> ReplayScore:
    """Score `policy` against a recorded session.

    The playhead is carried forward from each get — see the module docstring on
    reconstruction — starting at the first event's own playhead so a trace that
    opens mid-video is not scored against an imaginary position at zero.
    """
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
        # Raises on a kind this build does not know. A trace hand-edited or
        # written by an older build would otherwise score every unrecognised
        # request as not-a-drag, which is a scrub hit rate that reads as
        # measured and is not.
        if RequestKind(event.kind).is_felt_latency:
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
    """Every candidate policy scored against one trace at one capacity.

    Capacity is in frames rather than bytes because the experiment sweeps it:
    the interesting output is the curve — where, if anywhere, the proposal's
    advantage over the plain ring survives — and a single byte figure from
    `mutual/shares.py` would report one point on it.
    """
    return tuple(replay(events, policy(capacity_frames)) for policy in POLICIES)
