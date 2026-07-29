









from __future__ import annotations

import pytest

from sieve.gui.coalescer import Request, RequestCoalescer, RequestKind


class FakeClock:


    def __init__(self) -> None:
        self.seconds = 0.0

    def __call__(self) -> float:
        return self.seconds

    def advance(self, seconds: float) -> None:
        self.seconds += seconds


@pytest.fixture
def coalescer() -> RequestCoalescer:
    return RequestCoalescer()


def issued(request: Request | None) -> int:

    assert request is not None, "expected this request to be issued immediately"
    return request.index


class TestOneInFlightOnePending:
    def test_the_first_request_is_issued_immediately(self, coalescer: RequestCoalescer) -> None:
        assert issued(coalescer.request(7, RequestKind.EXACT)) == 7
        assert coalescer.pending is None

    def test_a_burst_keeps_only_the_last_and_discards_the_middle(
        self, coalescer: RequestCoalescer
    ) -> None:

        coalescer.request(0, RequestKind.SCRUB)
        for index in range(1, 40):
            assert coalescer.request(index, RequestKind.SCRUB) is None

        pending = coalescer.pending
        assert pending is not None
        assert pending.index == 39

        coalescer.arrived()
        assert issued(coalescer.drain()) == 39
        assert coalescer.pending is None

    def test_draining_an_empty_pending_slot_issues_nothing(
        self, coalescer: RequestCoalescer
    ) -> None:
        coalescer.request(3, RequestKind.EXACT)
        coalescer.arrived()
        assert coalescer.drain() is None
        assert coalescer.in_flight is None


class TestRank:


    def test_a_guess_does_not_displace_a_pending_commitment(
        self, coalescer: RequestCoalescer
    ) -> None:
        coalescer.request(0, RequestKind.EXACT)
        coalescer.request(33, RequestKind.EXACT)
        coalescer.request(12, RequestKind.SCRUB)

        pending = coalescer.pending
        assert pending is not None
        assert pending.index == 33, "a drag position evicted a committed one"

    def test_a_playback_tick_does_not_displace_a_pending_commitment(
        self, coalescer: RequestCoalescer
    ) -> None:

        coalescer.request(0, RequestKind.PLAYBACK)
        coalescer.request(33, RequestKind.EXACT)
        coalescer.request(1, RequestKind.PLAYBACK)

        pending = coalescer.pending
        assert pending is not None
        assert pending.index == 33

    def test_a_later_commitment_displaces_an_earlier_one(self, coalescer: RequestCoalescer) -> None:
        coalescer.request(0, RequestKind.EXACT)
        coalescer.request(33, RequestKind.EXACT)
        coalescer.request(41, RequestKind.EXACT)

        pending = coalescer.pending
        assert pending is not None
        assert pending.index == 41

    def test_a_guess_displaces_a_guess(self, coalescer: RequestCoalescer) -> None:
        coalescer.request(0, RequestKind.EXACT)
        coalescer.request(12, RequestKind.SCRUB)
        coalescer.request(19, RequestKind.SCRUB)

        pending = coalescer.pending
        assert pending is not None
        assert pending.index == 19


class TestDisplayOrdering:
    def test_a_decode_overtaken_by_a_local_display_is_not_painted(
        self, coalescer: RequestCoalescer
    ) -> None:

        coalescer.request(5, RequestKind.SCRUB)
        coalescer.served_without_decode(RequestKind.SCRUB)

        arrival = coalescer.arrived()
        assert not arrival.stale
        assert not arrival.display

    def test_a_commitment_is_painted_even_when_overtaken(self, coalescer: RequestCoalescer) -> None:

        coalescer.request(33, RequestKind.EXACT)
        coalescer.served_without_decode(RequestKind.SCRUB)

        assert coalescer.arrived().display

    def test_a_guess_served_locally_drops_a_pending_guess(
        self, coalescer: RequestCoalescer
    ) -> None:
        coalescer.request(5, RequestKind.SCRUB)
        coalescer.request(12, RequestKind.SCRUB)
        coalescer.served_without_decode(RequestKind.SCRUB)
        assert coalescer.pending is None

    def test_a_guess_served_locally_keeps_a_pending_commitment(
        self, coalescer: RequestCoalescer
    ) -> None:
        coalescer.request(5, RequestKind.SCRUB)
        coalescer.request(33, RequestKind.EXACT)
        coalescer.served_without_decode(RequestKind.SCRUB)

        pending = coalescer.pending
        assert pending is not None
        assert pending.index == 33


class TestGeneration:
    def test_a_frame_from_the_previous_source_is_stale(self, coalescer: RequestCoalescer) -> None:
        coalescer.request(30, RequestKind.EXACT)
        coalescer.new_generation()

        arrival = coalescer.arrived()
        assert arrival.stale
        assert not arrival.display

    def test_the_stale_frame_still_frees_the_slot_for_the_new_source(
        self, coalescer: RequestCoalescer
    ) -> None:

        coalescer.request(30, RequestKind.EXACT)
        coalescer.new_generation()
        assert coalescer.request(0, RequestKind.EXACT) is None, "issued behind a live decode"

        coalescer.arrived()
        assert issued(coalescer.drain()) == 0

    def test_a_new_generation_discards_the_pending_request(
        self, coalescer: RequestCoalescer
    ) -> None:
        coalescer.request(10, RequestKind.EXACT)
        coalescer.request(20, RequestKind.EXACT)
        coalescer.new_generation()
        assert coalescer.pending is None

    def test_sequence_numbers_do_not_restart_with_the_source(
        self, coalescer: RequestCoalescer
    ) -> None:

        coalescer.request(9, RequestKind.SCRUB)
        first = coalescer.in_flight
        assert first is not None

        coalescer.new_generation()
        coalescer.arrived()
        coalescer.drain()
        second = coalescer.request(0, RequestKind.SCRUB)
        assert second is not None
        assert second.sequence > first.sequence


class TestTiming:
    def test_the_round_trip_is_timed_from_issue_not_from_creation(self) -> None:





        clock = FakeClock()
        coalescer = RequestCoalescer(clock=clock)

        coalescer.request(0, RequestKind.EXACT)
        coalescer.request(5, RequestKind.SCRUB)
        clock.advance(0.500)

        coalescer.arrived()
        coalescer.drain()
        clock.advance(0.020)

        assert coalescer.round_trip_ms() == pytest.approx(20.0)
