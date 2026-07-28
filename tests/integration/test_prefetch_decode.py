"""The parallel reader against the sequential one, on a real file.

An integration test because the claim is an equivalence between two decoders and
there is no way to fake half of it: the whole point of `PrefetchFrameSource` is
that it returns what `VideoReader` returns, and a stub reader would be asserting
that two copies of the stub agree.

Three failures, each invisible from above:

**A frame that is not byte-identical.** `cache_key.source_key` folds
`decoder_identity()` in, and this reader deliberately does not change it — so a
positioning error of one frame would write a wrong frame under a right key and
serve it back forever. This is the test that permits the whole route.

**A window that is not bounded.** The reader would work, be fast, and hold the
span in memory; on 5312x2988 footage that is 47.6 MB a frame and the symptom is
an out-of-memory kill on the reference source rather than anything a small
fixture would show.

**A jump that answers with a neighbour.** Reading out of order has to move the
window and leave the consumer waiting on an index somebody claimed; getting it
wrong hangs or hands back the frame that was prefetched instead.

*The third of those was originally written as "a stale frame served after a
jump", and the mutation pass that checks these tests fail for the reasons claimed
showed that they cannot catch it — and that nothing can, because the stale frame
for index `i` is byte-identical to the fresh one. The epoch stamp is hygiene, not
correctness. The claim was corrected rather than the test being stretched to cover
something that is not a defect.*
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter, sleep

import numpy as np
import pytest

from sieve.decode.prefetch import (
    INFERRED_WORKER_CAP,
    LUMA_WORKER_CAP,
    PrefetchFrameSource,
    available_cpus,
)
from sieve.decode.reader import VideoDecodeError, VideoReader

#: The fixture is 40 frames; a span in the middle so a positioning error has
#: somewhere to be wrong in both directions.
SPAN = range(8, 32)


def test_every_frame_is_byte_identical_to_the_sequential_reader(synthetic_video: Path) -> None:
    """Four workers, one span, and not one differing byte.

    The claim that lets this be turned on without a cache generation. Fails on
    any positioning error, any dropped frame, any frame served from the wrong
    epoch — and would fail loudly here rather than as a wrong number in a
    published result six months later.
    """
    with VideoReader(synthetic_video) as reader:
        expected = [reader.read(index) for index in SPAN]

    with PrefetchFrameSource(synthetic_video, workers=4) as source:
        got = [source.read(index) for index in SPAN]

    assert [frame.index for frame in got] == list(SPAN)
    for frame, reference in zip(got, expected, strict=True):
        assert frame.index == reference.index
        assert frame.channels == reference.channels
        assert np.array_equal(frame.data, reference.data)
    # And they are not 24 copies of one frame, which the comparison above would
    # not notice if both readers had stalled on the same frame.
    assert len({frame.data.tobytes() for frame in got}) == len(list(SPAN))


def test_an_inferred_count_follows_the_format_the_source_was_opened_in(
    synthetic_video: Path,
) -> None:
    """The luma cap reaches the pool, not just `resolve_workers`.

    The unit test pins the function; this pins the wiring, and the wiring is
    where it can actually be lost — `resolve_workers(workers)` without the
    keyword type-checks, passes every other test here, and silently runs the
    luma path at four workers, which is 21% slower than two on the reference
    source. Nothing above would notice: every frame is still correct.

    Skipped rather than asserted-around on an allocation too small to tell the
    two caps apart, because on one or two cores they resolve to the same number
    and the test would pass with the keyword deleted.
    """
    if available_cpus() < INFERRED_WORKER_CAP:
        pytest.skip(f"{available_cpus()} cpus cannot distinguish the two caps")

    with PrefetchFrameSource(synthetic_video, luma=True) as source:
        assert source.luma
        assert source.workers == LUMA_WORKER_CAP

    with PrefetchFrameSource(synthetic_video) as source:
        assert not source.luma
        assert source.workers == INFERRED_WORKER_CAP


def test_the_window_never_runs_further_ahead_than_lookahead(synthetic_video: Path) -> None:
    """`claim - want` stays inside `lookahead` at every observation.

    Stated as an invariant checked repeatedly rather than as a count taken once,
    which is what the first version of this test did — and that version passed
    with the bound deleted, because it stopped looking the moment the window
    reached its limit instead of letting the pool run away. Asserting the
    invariant after every read fails immediately when the bound is gone: `claim`
    goes straight to the end of the file.

    The bound is the difference between a reader and a buffer of the whole span.
    The fixture is 160x120, so a runaway window here is a few megabytes; on the
    5312x2988 reference source it is 47.6 MB a frame.

    **Measured at quiescence, with the consumer deliberately not consuming, and
    both halves of that are necessary.** Sampling between reads catches nothing:
    the pool advances its claim once per completed read, so with the consumer
    reading as fast as the workers produce, `claim - want` stays around the worker
    count whether or not any bound exists — a version of this test that read the
    span in a tight loop passed with the bound deleted. The window only runs away
    when the producer outruns the consumer, which is the real case, because the
    real consumer runs filters on every frame.

    Waiting for the claim to stop moving then makes the assertion exact rather than
    a race: at quiescence the pool has claimed everything it is allowed to and
    nothing is in motion, so `claim - want` is `lookahead` precisely. Unbounded, it
    is the rest of the file.
    """
    lookahead = 3
    with PrefetchFrameSource(synthetic_video, workers=2, lookahead=lookahead) as source:
        assert source.lookahead == lookahead
        source.read(0)

        # Private, because the invariant is about internal bookkeeping: there is
        # no public reading of the window that would move when the bound is gone.
        def ahead() -> int:
            return source._claim - source._want  # pyright: ignore[reportPrivateUsage]

        settled = _quiesce(ahead)
        assert settled == lookahead, f"window settled {settled} ahead of a {lookahead} bound"

        # And the span still reads correctly from a full window.
        assert [source.read(index).index for index in range(1, 16)] == list(range(1, 16))


def _quiesce(sample: Callable[[], int], *, timeout_s: float = 3.0) -> int:
    """Poll `sample` until it stops changing, and return the settled value.

    Three consecutive equal readings rather than one sleep of a guessed length:
    the pool's claims stop when it hits its bound, and how long that takes is a
    property of the machine. Raises rather than returning a moving value, because
    a caller asserting on a number that had not settled would be asserting on a
    race.
    """
    deadline = perf_counter() + timeout_s
    stable = 0
    last = sample()
    while perf_counter() < deadline:
        sleep(0.01)
        current = sample()
        stable = stable + 1 if current == last else 0
        last = current
        if stable >= 3:
            return current
    raise AssertionError(f"never settled within {timeout_s}s; last value {last}")


def test_reading_out_of_order_answers_the_index_asked_for(synthetic_video: Path) -> None:
    """A jump, then forwards, then backwards — each returning the frame requested.

    Four workers are decoding 1..8 when the caller asks for 30 instead, so this
    covers the restart path: the window has to move, the consumer has to end up
    waiting on an index somebody claimed, and neither the forward nor the backward
    jump may hang or answer with a neighbour.

    It deliberately does *not* claim to pin the epoch stamp. Deleting the epoch
    comparison passes this test and every other one here, because a frame for
    index `i` is the same frame whichever position asked for it — the stamp is
    hygiene, and the module docstring says so rather than this test implying
    otherwise.
    """
    with VideoReader(synthetic_video) as reader:
        expected = {index: reader.read(index).data.copy() for index in (0, 30, 31, 5)}

    with PrefetchFrameSource(synthetic_video, workers=4) as source:
        assert np.array_equal(source.read(0).data, expected[0])
        # The jump. Workers are mid-flight on 1..8 at this point.
        assert np.array_equal(source.read(30).data, expected[30])
        # Sequential again from the new position.
        assert np.array_equal(source.read(31).data, expected[31])
        # And backwards, which is the other direction a restart has to handle.
        assert np.array_equal(source.read(5).data, expected[5])


def test_a_frame_outside_the_video_is_refused_the_way_the_reader_refuses_it(
    synthetic_video: Path,
) -> None:
    """One message for one condition, whichever source the caller happened to hold.

    Not a formatting preference: `pipeline/executor.py` takes a `FrameSource`
    protocol and a caller cannot tell which implementation it was given, so two
    different refusals for one mistake would make the error depend on a
    performance option.
    """
    with VideoReader(synthetic_video) as reader:
        frames = reader.metadata.frame_count
        with pytest.raises(VideoDecodeError) as sequential:
            reader.read(frames)

    with (
        PrefetchFrameSource(synthetic_video, workers=2) as source,
        pytest.raises(VideoDecodeError) as parallel,
    ):
        source.read(frames)

    assert str(parallel.value) == str(sequential.value)
