"""The retention trace: what it records, and what a replay can tell apart.

Three claims, each of which would fail for a different real reason.

**A trace survives the round trip, including a session that was killed.** The
file is written from two threads and read back by an experiment that runs
later; a `frontier` of None that came back as zero, or a truncated last line
that lost the whole session, would each make the replay quietly wrong.

**The policies disagree where the item said they would.** The observation that
opened `docs/todo/proxy-retention-policy.md` is that a render walking forward
evicts exactly the frames a backward scrub wants. A harness that cannot show
that difference on a trace built to contain it cannot show it on a real one
either — this is the calibration that makes a null result on a real trace mean
something.

**The frontier is pinned.** Follow-the-render mode displays the newest frame,
so a policy that evicted it for being far from the playhead would blank the
pane at the moment the user is watching it fill.

**A kind the build does not know stops the replay.** The scrub hit rate is the
half of a score the item actually argues from, and a trace written by a build
with a different vocabulary would otherwise score every unrecognised request as
not-a-drag — a number that reads as measured.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sieve.bench.retention_trace import (
    FROM_CACHE,
    FROM_DECODE,
    FROM_RING,
    GET,
    PUT,
    UNKNOWN_PLAYHEAD,
    AccessEvent,
    LruSim,
    PlayheadDistanceSim,
    RingSim,
    TraceRecorder,
    compare,
    load_trace,
    recorder_from_env,
    replay,
)
from sieve.core.request_intent import RequestKind


def put(index: int) -> AccessEvent:
    return AccessEvent(
        op=PUT,
        index=index,
        playhead=UNKNOWN_PLAYHEAD,
        kind="",
        source="",
        frontier=index,
    )


def get(
    index: int,
    playhead: int,
    kind: str = RequestKind.SCRUB,
    source: str = FROM_RING,
) -> AccessEvent:
    return AccessEvent(
        op=GET, index=index, playhead=playhead, kind=kind, source=source, frontier=None
    )


class TestTheTraceFile:
    def test_events_survive_the_round_trip_with_a_null_frontier_intact(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "trace.jsonl"
        recorder = TraceRecorder(path)
        assert recorder.enabled
        written = (put(3), get(3, playhead=0), get(9, playhead=3, source=FROM_DECODE))
        for event in written:
            recorder.record(event)
        recorder.close()

        assert load_trace(path) == written

    def test_a_recorder_with_no_path_writes_nothing_and_says_so(self, tmp_path: Path) -> None:
        """The ordinary case. `enabled` is what the hot paths branch on, so it
        has to be false before any event is built, not merely harmless."""
        recorder = TraceRecorder()
        assert not recorder.enabled
        assert recorder.path is None
        recorder.record(put(1))
        recorder.close()
        assert not list(tmp_path.iterdir())

    def test_a_truncated_final_line_costs_one_event_not_the_session(self, tmp_path: Path) -> None:
        """A long render is usually ended by killing the session, so this is
        the shape a real trace arrives in."""
        path = tmp_path / "trace.jsonl"
        recorder = TraceRecorder(path)
        for index in range(4):
            recorder.record(put(index))
        recorder.close()
        path.write_text(path.read_text(encoding="utf-8")[:-12], encoding="utf-8")

        assert [event.index for event in load_trace(path)] == [0, 1, 2]

    def test_the_env_var_is_what_turns_it_on(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "trace.jsonl"
        assert not recorder_from_env({}).enabled
        assert not recorder_from_env({"SIEVE_RETENTION_TRACE": "  "}).enabled
        enabled = recorder_from_env({"SIEVE_RETENTION_TRACE": str(path)})
        try:
            assert enabled.path == path
            assert path.exists(), "the parent directory was not created"
        finally:
            enabled.close()


#: A render filling 0..39 while the user scrubs back to 2 and steps forward.
#: Sized so a capacity of 10 cannot hold both ends: under a ring the early
#: frames are gone by the time they are asked for, and that is the whole
#: observation the item was opened on.
def backward_scrub_trace() -> tuple[AccessEvent, ...]:
    events: list[AccessEvent] = [get(0, playhead=0, kind="exact", source=FROM_DECODE)]
    events += [put(index) for index in range(40)]
    events += [get(index, playhead=index - 1) for index in range(2, 8)]
    return tuple(events)


class TestThePoliciesDisagree:
    def test_the_playhead_rule_serves_a_backward_scrub_the_ring_has_dropped(self) -> None:
        events = backward_scrub_trace()
        ring = replay(events, RingSim(10))
        distance = replay(events, PlayheadDistanceSim(10))

        assert ring.scrub_hits == 0, "the ring kept frames it should have evicted"
        assert distance.scrub_hits == distance.scrub_requests
        assert distance.hit_rate > ring.hit_rate

    def test_a_render_makes_an_lru_degenerate_to_the_ring(self) -> None:
        """The reason the incumbent's baseline is a plain ring: a render
        touches every frame once, in order, so recency *is* production order
        and the LRU has no extra information to use."""
        events = backward_scrub_trace()
        assert replay(events, LruSim(10)).hits == replay(events, RingSim(10)).hits

    def test_the_frontier_is_kept_however_far_the_playhead_is(self) -> None:
        policy = PlayheadDistanceSim(3)
        for index in range(20):
            policy.put(index, playhead=0, frontier=index)
        assert policy.get(19), "the newest frame the render produced was evicted"
        assert policy.get(0), "the playhead's own frame was evicted"

    def test_the_pin_never_stops_the_store_evicting(self) -> None:
        """At most one retained frame is the frontier, so excepting it can
        never leave nothing to drop — the bound holds at a capacity of one."""
        policy = PlayheadDistanceSim(1)
        for index in range(5):
            policy.put(index, playhead=index, frontier=index)
        assert len(policy) == 1


class TestTheReplayScopesWhatItCounts:
    def test_a_cache_hit_is_recorded_and_not_replayed(self) -> None:
        """It costs nothing under every candidate, so counting it would move
        all three scores by the same amount and compare nothing."""
        events = (put(5), get(5, playhead=4), get(99, playhead=5, source=FROM_CACHE))
        score = replay(events, RingSim(10))
        assert score.requests == 1
        assert score.hits == 1

    def test_the_worst_stall_is_counted_in_consecutive_misses(self) -> None:
        events = (
            put(0),
            get(0, playhead=0),
            get(50, playhead=0, source=FROM_DECODE),
            get(51, playhead=50, source=FROM_DECODE),
            get(52, playhead=51, source=FROM_DECODE),
            get(0, playhead=52),
        )
        assert replay(events, RingSim(10)).worst_miss_run == 3

    def test_an_unknown_kind_refuses_rather_than_scoring_as_not_a_drag(self) -> None:
        events = (put(0), get(0, playhead=0, kind="hover"))
        with pytest.raises(ValueError):
            replay(events, RingSim(10))

    def test_compare_scores_every_named_policy_once(self) -> None:
        scores = compare(backward_scrub_trace(), capacity_frames=10)
        assert [score.policy for score in scores] == ["ring", "lru", "playhead-distance"]
        assert all(score.requests == scores[0].requests for score in scores)
