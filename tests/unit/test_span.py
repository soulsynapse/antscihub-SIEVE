"""The span tool: the identity value, the half-open convention, and the lead-in.

Each case here stands for a way the span stops being a tool. The identity value
is what keeps `range | None` out of the plan, so a default that is not every
frame is a rule broken rather than a wrong result. The lead-in is the one that
fails quietly: a kernel that refused frames below `start` would leave every
stateful tool downstream unsettled for the whole span, and the frames it emitted
would look entirely plausible.

**The golden is not an array of pixels, and that is not a weakening of 03.7's
mechanism but its subject applied honestly.** This kernel returns the frame it
was handed, so a checked-in copy of the input would agree with any
implementation that returned anything at all — the triviality
`test_downsample.py::test_the_goldens_are_not_trivially_equal` exists to catch,
minted as a golden. What v3 can actually differ from v2 on is the *selection*:
the half-open convention, and the value of `end` that means "all of them". So
`REGENERATE` runs v2's own `SpanParams` over a table of configurations and saves
what each one declared it keeps, in exactly 03.7's shape — a v2-produced
artifact under `tests/goldens/` with the command that made it recorded beside
the assertion.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sieve.core.tool_base import ALL_FRAMES, UNBOUNDED_FRAME, ParamsBase, ParamStereotype
from sieve.core.types import ChannelSpec, Frame, FrameSpan
from sieve.tools.span import SpanParams, run

#: What produced `tests/goldens/span_selected_frames.npy`, run from the repo
#: root. The `git diff --quiet` half makes the second half a statement about
#: `main` rather than about whatever is sitting in the sibling worktree, and it
#: exits nonzero — stopping the `&&` — when the two differ. `filter_base.py` is
#: in the diffed set and not only `span.py`, because the default `end` this
#: golden pins is `UNBOUNDED_FRAME` and that constant lives there.
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- "
    "src/sieve/filters/span.py src/sieve/core/filter_base.py && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import numpy as np; "
    "from sieve.filters.span import SpanParams; "
    "np.save('tests/goldens/span_selected_frames.npy', np.array("
    "[[p.start, p.end, p.selected_frames().start, p.selected_frames().stop] "
    "for p in (SpanParams(), SpanParams(start=5), SpanParams(start=10, end=20), "
    'SpanParams(start=0, end=1))], dtype=np.int64))"'
)

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"

#: The configurations `REGENERATE` builds, in its order, written the same way on
#: both sides. Two of the four are constructed with a default — the whole point
#: of the first two rows is that v2 and v3 agree on what an *unwritten* bound is,
#: which a table of literal numbers could not ask.
GOLDEN_CASES = (
    SpanParams(),
    SpanParams(start=5),
    SpanParams(start=10, end=20),
    SpanParams(start=0, end=1),
)


def gradient_frame(index: int) -> Frame:
    """A frame distinguishable from any other by its contents and its index."""
    data = np.full((4, 5), index, dtype=np.uint16)
    return Frame(data=data, index=index, channels=ChannelSpec.GRAY)


def one(frame: Frame) -> FrameSpan:
    """A streaming tool's window: the single frame it was handed."""
    return FrameSpan((frame,))


def test_the_identity_span_is_every_frame_there_could_be() -> None:
    # What "no span" is spelled as, and the reason `plan._selected` can skip an
    # unconfigured span node without asking which tool it is: the default range
    # is the fold's identity, so the intersection is unchanged by it.
    #
    # Bounds first, and not for redundancy: pytest's rewritten assertion builds a
    # sequence diff when two `range`s compare unequal, which materialises four
    # billion elements — a wrong default here takes three minutes to report and
    # reads as a hang. The cheap comparison fails first and the expensive one
    # never runs.
    kept = SpanParams().selected_frames()

    assert (kept.start, kept.stop, kept.step) == (ALL_FRAMES.start, ALL_FRAMES.stop, 1)
    assert kept == ALL_FRAMES


def test_a_bound_is_one_past_the_last_frame_kept() -> None:
    # The half-open convention, stated where the pair becomes an interval. An
    # inclusive `end` would drop or add exactly one frame at the boundary, which
    # no downstream shape check can see and no graph refuses.
    kept = SpanParams(start=10, end=20).selected_frames()

    assert (kept.start, kept.stop, len(kept)) == (10, 20, 10)
    assert 19 in kept
    assert 20 not in kept


def test_a_backwards_or_empty_range_is_refused_at_the_node() -> None:
    # Refused here rather than folded into an empty intersection: an empty
    # *intersection* is two ranges that each make sense, and the reader has to be
    # told which pair. This one makes no sense alone and the node is the message.
    with pytest.raises(ValueError, match=r"at least one frame, got \[20, 20\)"):
        SpanParams(start=20, end=20)
    with pytest.raises(ValueError, match=r"at least one frame, got \[20, 10\)"):
        SpanParams(start=20, end=10)
    with pytest.raises(ValueError, match="non-negative, got -1"):
        SpanParams(start=-1)


def test_the_kernel_passes_the_lead_in_through_rather_than_refusing_it() -> None:
    # The quiet failure this tool has. Frames below `start` reach the kernel
    # because they are what warms every stateful tool in the graph; they are cut
    # at the yield, after they have done that warming. A kernel that refused them
    # — raised, or emitted a blank — would leave everything downstream unsettled
    # for the whole span, and the frames it did emit would look plausible.
    params = SpanParams(start=100, end=200)

    for index in (0, 99, 100, 150):
        frame = gradient_frame(index)

        assert run(params, one(frame), None) is frame


def test_the_kernel_neither_copies_nor_renumbers() -> None:
    # `crop` and `downsample` copy because a view retains the frame it was cut
    # from; here the output *is* that frame, so a copy would release nothing and
    # cost a frame's worth of memory per node. Identity of the index matters for
    # its own reason: a tool that renumbered would desynchronise every downstream
    # index without changing a pixel.
    frame = gradient_frame(7)

    emitted = run(SpanParams(start=0, end=10), one(frame), None)

    assert np.shares_memory(emitted.data, frame.data)
    assert (emitted.index, emitted.channels) == (7, ChannelSpec.GRAY)


def test_the_span_declares_the_stereotype_the_timeline_handoff_reads() -> None:
    # The GUI reaches a span through the kind, never through `tool_id`
    # (`adr/gui-knows-kinds-not-tools.md`). Both bounds carry it because they are
    # one populated value: a bound declaring `scalar-range` on its own would get
    # a spinbox and take the interval apart.
    stereotypes = SpanParams.spec().param_stereotypes

    assert stereotypes == {"start": ParamStereotype.SPAN, "end": ParamStereotype.SPAN}


def test_the_selection_is_declared_and_the_spec_says_so() -> None:
    # The pair `ToolSpec.__post_init__` refuses apart. Asserted from the tool
    # rather than from a fixture because the failure it closes is this tool's:
    # a span whose spec forgot `selecting` runs over the whole video and its
    # docstring is the only evidence it was meant to cut one down.
    spec = SpanParams.spec()

    assert spec.selecting
    assert SpanParams.selected_frames is not ParamsBase.selected_frames


def test_the_identity_span_is_a_value_in_the_saved_params() -> None:
    # The default has to survive to the cache key as a range rather than as an
    # absence. The bound is asserted literally because it is the number a reader
    # meets in a saved document, and a changed bound silently re-keys every span
    # node that was left at its default.
    canonical = SpanParams().canonical_json()

    assert canonical == '{"end":4294967296,"start":0}'
    assert UNBOUNDED_FRAME == 4294967296
    assert SpanParams.model_validate_json(SpanParams().model_dump_json()) == SpanParams()


def test_every_configuration_selects_what_v2_selected() -> None:
    """v3's `selected_frames` reproduces v2's, defaults included.

    Four rows, and the first two are the ones a reimplementation could get wrong
    without noticing: they are built from *defaults*, so the golden's first two
    columns pin what v2 meant by an unwritten bound against what v3 means by one.
    The last two pin the convention — a ten-frame range and the minimum legal
    one — where an inclusive `end` would show up as a length off by one.
    """
    golden = np.load(GOLDENS / "span_selected_frames.npy")
    produced = np.array(
        [
            [p.start, p.end, p.selected_frames().start, p.selected_frames().stop]
            for p in GOLDEN_CASES
        ],
        dtype=np.int64,
    )

    assert produced.shape == golden.shape
    assert np.array_equal(produced, golden)


def test_the_golden_records_more_than_one_distinct_selection() -> None:
    """A golden whose rows were all one range would pass parity for nothing."""
    golden = np.load(GOLDENS / "span_selected_frames.npy")

    assert len({tuple(row) for row in golden}) == len(golden)


def test_the_regeneration_command_names_every_golden() -> None:
    """A golden the recorded command does not write is a golden nobody can redo."""
    unnamed = sorted(
        path.name for path in GOLDENS.glob("span_*.npy") if path.name not in REGENERATE
    )

    assert unnamed == []
