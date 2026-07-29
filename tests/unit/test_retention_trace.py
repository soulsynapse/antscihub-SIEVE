



















from __future__ import annotations

from pathlib import Path

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


def put(index: int) -> AccessEvent:
    return AccessEvent(
        op=PUT,
        index=index,
        playhead=UNKNOWN_PLAYHEAD,
        kind="",
        source="",
        frontier=index,
    )


def get(index: int, playhead: int, kind: str = "scrub", source: str = FROM_RING) -> AccessEvent:
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


        recorder = TraceRecorder()
        assert not recorder.enabled
        assert recorder.path is None
        recorder.record(put(1))
        recorder.close()
        assert not list(tmp_path.iterdir())

    def test_a_truncated_final_line_costs_one_event_not_the_session(self, tmp_path: Path) -> None:


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



        events = backward_scrub_trace()
        assert replay(events, LruSim(10)).hits == replay(events, RingSim(10)).hits

    def test_the_frontier_is_kept_however_far_the_playhead_is(self) -> None:
        policy = PlayheadDistanceSim(3)
        for index in range(20):
            policy.put(index, playhead=0, frontier=index)
        assert policy.get(19), "the newest frame the render produced was evicted"
        assert policy.get(0), "the playhead's own frame was evicted"

    def test_the_pin_never_stops_the_store_evicting(self) -> None:


        policy = PlayheadDistanceSim(1)
        for index in range(5):
            policy.put(index, playhead=index, frontier=index)
        assert len(policy) == 1


class TestTheReplayScopesWhatItCounts:
    def test_a_cache_hit_is_recorded_and_not_replayed(self) -> None:


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

    def test_compare_scores_every_named_policy_once(self) -> None:
        scores = compare(backward_scrub_trace(), capacity_frames=10)
        assert [score.policy for score in scores] == ["ring", "lru", "playhead-distance"]
        assert all(score.requests == scores[0].requests for score in scores)
