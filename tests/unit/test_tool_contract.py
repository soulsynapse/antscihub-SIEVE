"""The tool contract: what a spec refuses to claim, and what the shelf holds.

Each test here stands in for a way the contract stops being load-bearing: a
spec that promises more than it can, a params model that swallows a typo, a
cache-key input that is not byte-stable, or a registry that hands back the
wrong version of a tool an old pipeline named.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Mapping
from dataclasses import fields
from enum import StrEnum
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sieve.core.tool_base import (
    ALL_FRAMES,
    SPEC_CHANNELS,
    ArraySpec,
    AxisRelation,
    CaptionPart,
    Channel,
    DisplaySurface,
    ElementKind,
    ElementNames,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    TableSpec,
    ToolSpec,
    WarmupKind,
    caption_for_params,
    input_warmup_frames,
    node_element,
    node_element_names,
    node_lookahead_frames,
    resolved_schema,
    source_warmup_frames,
)
from sieve.core.tool_registry import (
    DuplicateToolError,
    ToolRegistry,
    UnknownToolError,
    register_tool,
)
from sieve.core.types import (
    NO_FRAMES,
    ROI,
    ChannelSpec,
    Frame,
    FrameCount,
    FrameIndex,
    FrameSpan,
)


class SampleParams(ParamsBase):
    # Declared out of alphabetical order on purpose: `canonical_json` has to
    # sort, and a model whose fields were already sorted could not show it.
    factor: int = 2
    anti_alias: bool = True


class DecimateParams(ParamsBase):
    """Keeps every `stride`-th frame: rate changes, frame size does not."""

    stride: int = 10

    def output_rate(self) -> Fraction:
        return Fraction(1, self.stride)


class InterpolateParams(ParamsBase):
    """Emits three frames for every two consumed: a rate above 1.

    Here so the rounding in `input_warmup_frames` has something inexact to
    round. Every decimator divides exactly — `need / (1/n)` is `need * n` — so a
    fixture set of decimators alone leaves `ceil` unexercised.
    """

    numerator: int = 3
    denominator: int = 2

    def output_rate(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)


class StalledParams(ParamsBase):
    """Declares a rate no quantity of input could supply.

    Reachable through the declaration rule rather than in spite of it: a
    `rate_changing` tool *must* override `output_rate`, and nothing constrains
    what the override returns. `rate` is a field so one model covers both
    non-positive directions — zero, which makes `at_input_of` divide by zero,
    and negative, which points the window the wrong way.
    """

    rate: int = 0

    def output_rate(self) -> Fraction:
        return Fraction(self.rate)


class SpanningParams(ParamsBase):
    """Keeps a range of the frames it is handed: neither the rate nor the size.

    The third way a tool can emit less than it consumed, and the one that is
    not arithmetic — the survivors keep their numbering, so nothing in the warmup
    fold has to cross it.
    """

    first: int = 10
    last: int = 20

    def selected_frames(self) -> range:
        return range(self.first, self.last)


class WindowParams(ParamsBase):
    """A trailing window whose length *is* the lead-in.

    The shape `temporal_baseline` has and the reason warmup became
    params-derived: a static declaration would have to be the window's upper
    bound, charged to every run whatever window it asked for.
    """

    length: int = 5

    def warmup_frames(self) -> FrameCount:
        return FrameCount(self.length - 1)


class CenteredWindowParams(ParamsBase):
    """A window centred on its target: half behind it, half in front.

    `detect`'s shape (`adr/detector-is-a-node.md`) and the reason lookahead is
    params-derived for `WindowParams`' reason — the widest window this model
    admits would otherwise be charged to every run whatever length it asked
    for. Both halves refine from the same parameter, which is what makes a
    configuration's warmup and lookahead move together.
    """

    length: int = 5

    def warmup_frames(self) -> FrameCount:
        return FrameCount((self.length - 1) // 2)

    def lookahead_frames(self) -> FrameCount:
        return FrameCount((self.length - 1) // 2)

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        return FrameCount(50)

    @classmethod
    def max_lookahead_frames(cls) -> FrameCount:
        return FrameCount(50)


class CompositeParams(ParamsBase):
    """One field per populated value, in the three shapes the shelf uses.

    `detect`'s bands are bare pairs and its `count_frac` is a pair that can be
    unset; `crop`'s region is a type of its own whose components are its fields.
    """

    band: tuple[float, float] = (0.0, 1.0)
    optional_band: tuple[float, float] | None = None
    region: ROI = ROI(x=0, y=0, width=1, height=1)


#: Total over `CompositeParams`, which every stereotype map must be.
COMPOSITE_KINDS = {
    "band": ParamStereotype.BAND,
    "optional_band": ParamStereotype.BAND,
    "region": ParamStereotype.REGION,
}


class UndeclaredArityParams(ParamsBase):
    """The two annotations the arity rule reasons about and no tool declares.

    `scalar_or_pair` is a union whose branches disagree about arity, and
    `unbounded` a tuple with no length. Neither is on the shelf: `count_frac` is
    `tuple[float, float] | None`, which is a one-branch union once `NoneType` is
    dropped and so cannot see how the reduction over branches was written
    (`findings/2026.08.08-the-arity-guards-two-hardest-branches-are-the-two-nothing-holds.md`).
    """

    scalar_or_pair: int | tuple[int, int] = 0
    unbounded: tuple[int, ...] = ()


class Product(StrEnum):
    """Two different things one tool computes, only one of which leaves it."""

    SOFT = "soft"
    HARD = "hard"


class ProductParams(ParamsBase):
    """`background_ema`'s shape: a parameter that chooses which product is emitted."""

    product: Product = Product.SOFT
    factor: int = 2


class UnenumerableParams(ParamsBase):
    """The three annotations an `ENUM` can be declared over, one of them wrongly.

    A `StrEnum` writes its members into the schema and a `bool` is the pair the
    generator's fallback is right about; a `str` is neither, and no tool on the
    shelf declares one.
    """

    label: str = "left"
    product: Product = Product.SOFT
    anti_alias: bool = True


class ForeignPointerParams(ParamsBase):
    """A params model whose schema points somewhere `$defs` is not.

    Pydantic writes no such pointer and cannot be made to write one property-
    side: a `$ref` injected through `json_schema_extra` or
    `__get_pydantic_json_schema__` is refused by pydantic's own generator, which
    resolves every reference it emits before this module sees the document. The
    `ref_template` is the one way through, and asking for another document is
    what a caller rendering an OpenAPI-shaped schema does.

    The template is `$defs`' own length with a different name, which is the
    pointer the prefix check is *for*: a walk that took the offset on trust
    would slice `ROI` out of it and resolve a definition this document never
    claimed to hold. The realistic `#/components/schemas/{model}` degrades with
    or without the check, because the tail it slices names no definition either
    (`findings/2026.08.08-the-foreign-pointer-guard-is-load-bearing-only-at-its-own-length.md`).
    """

    region: ROI = ROI(x=0, y=0, width=1, height=1)

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs["ref_template"] = "#/$DEFS/{model}"
        return super().model_json_schema(*args, **kwargs)


def stub_display(params: ParamsBase, window: FrameSpan, /) -> dict[DisplaySurface, Frame]:
    """A filler for the fixtures that declare a band and are not about drawing.

    Never called in this module: what registration reads is that the pointer is
    there, and what it draws is checked where it is drawn
    (`tests/unit/test_executor.py`). It exists because a fixture cannot simply
    omit one — a band names a picture and a picture nothing fills is refused,
    which is the rule these fixtures are built under rather than an obstacle to
    them.
    """
    target = window[window.target_row]
    return {
        DisplaySurface.TRACE: Frame(data=target.data, index=target.index, channels=target.channels)
    }


def make_spec(**overrides: object) -> ToolSpec:
    model = overrides.get("params_model", SampleParams)
    assert isinstance(model, type) and issubclass(model, ParamsBase)
    fields: dict[str, object] = {
        "tool_id": "downsample",
        "version": "1.0.0",
        "summary": "Reduce spatial resolution by an integer factor.",
        "params_model": SampleParams,
        "accepts": ArraySpec(),
        "emits": ArraySpec(),
        "emissions": (Emission("out"),),
        "element": ElementRelation.PRESERVED,
        # Derived rather than written out: stereotypes are total over the
        # params model, so every fixture below would otherwise carry a map
        # naming its own fields before it could say the thing it is about.
        "param_stereotypes": dict.fromkeys(model.model_fields, ParamStereotype.SCALAR_RANGE),
    }
    fields.update(overrides)
    # Derived for the stereotypes' reason one step on: a band declares the
    # picture its handles are grabbed on and where they read, and a picture
    # declares what fills it, so a fixture about arity or about a union would
    # otherwise carry three maps and a function before it could say the thing it
    # is about. All are `setdefault`, so a test *about* one still states it.
    stereotypes = fields["param_stereotypes"]
    bands = (
        [name for name, kind in stereotypes.items() if kind is ParamStereotype.BAND]
        if isinstance(stereotypes, Mapping)
        else []
    )
    if bands:
        fields.setdefault("param_surfaces", dict.fromkeys(bands, DisplaySurface.TRACE))
        fields.setdefault("param_axes", dict.fromkeys(bands, AxisRelation.INPUT_VALUES))
        fields.setdefault("display", stub_display)
    return ToolSpec(**fields)  # pyright: ignore[reportArgumentType]


#: The specs the rate tests chain. Built once at module scope because
#: constructing them is what several tests do *before* the thing they are
#: about, not part of it.
DECIMATOR = make_spec(tool_id="decimate", params_model=DecimateParams, rate_changing=True)
IIR = make_spec(
    tool_id="iir",
    warmup_frames=FrameCount(5),
    settling_epsilon=0.0,
    warmup_kind=WarmupKind.BOUNDED,
)
INTERPOLATOR = make_spec(tool_id="interpolate", params_model=InterpolateParams, rate_changing=True)
STALLED = make_spec(tool_id="stalled", params_model=StalledParams, rate_changing=True)
#: Declares a bound of 99 and refines it per configuration.
WINDOWED = make_spec(
    tool_id="window",
    params_model=WindowParams,
    warmup_frames=FrameCount(99),
    settling_epsilon=0.0,
    warmup_kind=WarmupKind.BOUNDED,
)
#: Declares both halves of a centred window as bounds of 50, and refines each
#: from `length`.
CENTERED = make_spec(
    tool_id="detect",
    params_model=CenteredWindowParams,
    mode=Mode.WINDOWED,
    warmup_frames=FrameCount(50),
    settling_epsilon=0.0,
    warmup_kind=WarmupKind.BOUNDED,
    lookahead_frames=FrameCount(50),
)


class TestToolSpec:
    def test_nonzero_warmup_declares_the_epsilon_it_settles_to(self) -> None:
        with pytest.raises(ValueError, match="settling_epsilon must be declared"):
            make_spec(warmup_frames=FrameCount(1), warmup_kind=WarmupKind.BOUNDED)

        settled = make_spec(
            warmup_frames=FrameCount(1),
            settling_epsilon=0.0,
            warmup_kind=WarmupKind.BOUNDED,
        )
        assert settled.settling_epsilon == 0.0

    def test_a_warmup_declares_which_kind_of_warmup_it_is(self) -> None:
        # The declaration `cache_key.cache_policy` reads and nothing else can
        # supply. Both directions refused, and the omission is the one that
        # matters: a default of BOUNDED would key the next EMA that forgot to
        # say so and serve its output to a run that started somewhere else
        # (`adr/cache-admission-is-bounded-warmup.md`).
        with pytest.raises(ValueError, match="no warmup_kind"):
            make_spec(warmup_frames=FrameCount(1), settling_epsilon=0.0)
        with pytest.raises(ValueError, match="no warmup_kind"):
            make_spec(stateful=True)
        # And refused where there is nothing to settle, so the field cannot
        # become a way of opting a stateless tool out of the cache.
        with pytest.raises(ValueError, match="nothing to settle"):
            make_spec(warmup_kind=WarmupKind.BOUNDED)

        assert (
            make_spec(
                stateful=True, warmup_kind=WarmupKind.EPSILON, settling_epsilon=0.25
            ).warmup_kind
            is WarmupKind.EPSILON
        )

    @pytest.mark.parametrize("epsilon", [None, 0.0])
    def test_an_epsilon_warmup_declares_a_nonzero_epsilon(self, epsilon: float | None) -> None:
        """A tolerance of zero is bit-for-bit, which is the other kind.

        `EPSILON` is the claim that two runs meeting at a frame agree to within
        `settling_epsilon` and *not* exactly, so a zero there asserts the
        bit-identity `BOUNDED` exists to mean — and `cache_key` prints the
        number in the refusal a user reads, where it becomes "to within 0.0,
        which is not to within nothing". Both spellings of the absence are
        refused for the reason a nonzero `warmup_frames` with no epsilon is: the
        number is a measurement, and the tool owes it before it may claim to
        settle.
        """
        with pytest.raises(ValueError, match="settling claim with no tolerance"):
            make_spec(stateful=True, warmup_kind=WarmupKind.EPSILON, settling_epsilon=epsilon)

        measured = make_spec(stateful=True, warmup_kind=WarmupKind.EPSILON, settling_epsilon=0.25)
        assert measured.settling_epsilon == 0.25

    @pytest.mark.parametrize("epsilon", [-0.1, float("inf"), float("nan")])
    def test_settling_epsilon_must_be_a_finite_non_negative_number(self, epsilon: float) -> None:
        with pytest.raises(ValueError, match="finite non-negative"):
            make_spec(settling_epsilon=epsilon)

    def test_primary_params_must_name_real_fields(self) -> None:
        # A renamed parameter otherwise leaves the GUI silently short a widget.
        with pytest.raises(ValueError, match=r"no such field.*scale_factor"):
            make_spec(primary_params=("scale_factor",))

    def test_caption_must_name_real_fields(self) -> None:
        with pytest.raises(ValueError, match=r"caption names no such field.*scale_factor"):
            make_spec(caption=(CaptionPart(param="scale_factor"),))

    def test_param_value_labels_must_name_real_fields(self) -> None:
        with pytest.raises(ValueError, match=r"param_value_labels names no such field.*method"):
            make_spec(param_value_labels={"method": {"fast": "fast"}})

    def test_caption_renders_from_declared_presentation(self) -> None:
        spec = make_spec(
            caption=(
                CaptionPart(label="factor", param="factor"),
                CaptionPart(param="anti_alias"),
            ),
            param_value_labels={"anti_alias": {"True": "averaged", "False": "sampled"}},
        )

        assert caption_for_params(spec, SampleParams(factor=4, anti_alias=False)) == (
            "factor 4 · sampled"
        )

    def test_rejects_non_semver_version(self) -> None:
        with pytest.raises(ValueError, match=r"MAJOR\.MINOR\.PATCH"):
            make_spec(version="1.0")

    def test_version_tuple_orders_numerically(self) -> None:
        assert make_spec(version="1.10.0").version_tuple > make_spec(version="1.9.0").version_tuple

    def test_the_id_keeps_v2s_spelling_rule(self) -> None:
        # The rename is names, never values: `crop` and `detect` have to come
        # over as the same strings v2's goldens and saved projects carry, and a
        # loosened pattern is the first way one of them could stop being itself.
        assert make_spec(tool_id="block_signal").tool_id == "block_signal"
        with pytest.raises(ValueError, match="tool_id must match"):
            make_spec(tool_id="BlockSignal")

    def test_defaults_are_the_conservative_claims(self) -> None:
        spec = make_spec()
        assert (spec.deterministic, spec.stateful, spec.mode) == (True, False, Mode.STREAMING)

    def test_every_field_is_in_exactly_one_channel(self) -> None:
        # The direction that earns the test is the first: a field added without
        # a row fails at the moment it is written, so the next `primary_params`
        # cannot arrive as GUI policy in core unclassified. The second direction
        # keeps the mapping from outliving a field it names, which would make
        # the partition read total while covering something gone.
        declared = {f.name for f in fields(ToolSpec)}
        assert declared - set(SPEC_CHANNELS) == set()
        assert set(SPEC_CHANNELS) - declared == set()


class TestState:
    def test_a_state_factory_without_stateful_is_refused(self) -> None:
        # The declaration the cut list admits and the check that earns it: the
        # factory tells whoever starts the run that state exists, `stateful`
        # tells the executor to re-settle it across a served range, and a spec
        # carrying only the first is run by a loop that never does.
        with pytest.raises(ValueError, match="declares a state_factory but not stateful"):
            make_spec(state_factory=dict)

        kept = make_spec(
            state_factory=dict,
            stateful=True,
            warmup_kind=WarmupKind.EPSILON,
            settling_epsilon=0.25,
        )
        assert kept.state_factory is dict


class TestRate:
    def test_warmup_behind_a_decimator_is_counted_in_source_frames(self) -> None:
        # The whole reason rate is declared. Five frames of warmup downstream
        # of a 10:1 decimator is fifty source frames; a plain sum says fifteen,
        # and the resulting preview renders an IIR that never settled rather
        # than failing in any visible way.
        path = [(DECIMATOR, DecimateParams()), (IIR, SampleParams())]

        assert source_warmup_frames(path) == FrameCount(50)
        # What a sum would have said — and `FrameCount` has no `__radd__`, so writing
        # the wrong thing now costs an explicit unwrap per term rather than reading
        # like ordinary arithmetic.
        assert sum(spec.warmup_frames.frames for spec, _ in path) == 5

    def test_rate_is_read_from_params_not_from_the_spec(self) -> None:
        # The factor is a parameter, so two nodes sharing one spec must be able
        # to disagree. A constant on the spec could not express this at all.
        by_three = source_warmup_frames(
            [(DECIMATOR, DecimateParams(stride=3)), (IIR, SampleParams())]
        )
        assert by_three == FrameCount(15)

    def test_a_partial_input_frame_rounds_up(self) -> None:
        # A rate of 3/2 means two input frames buy three output frames, so five
        # output frames want 3.33 inputs and therefore 4. Flooring gives 3, and
        # the node is one frame short of settled — which is why this is an
        # example rather than a property: every rate of the form 1/n divides
        # exactly, so a suite generated from decimators alone cannot tell the
        # two roundings apart no matter how many graphs it draws.
        step = (INTERPOLATOR, InterpolateParams())
        assert input_warmup_frames(step, FrameCount(5)) == FrameCount(4)
        assert input_warmup_frames(step, FrameCount(6)) == FrameCount(4)

    def test_a_configured_warmup_is_charged_instead_of_the_bound(self) -> None:
        # The point of the refinement. Without it every run of a graph holding
        # this node decodes the bound — 99 frames here, 7199 for
        # `temporal_baseline` — whatever window it actually asked for. The
        # decimator is in the path because the refinement has to survive the
        # rate conversion: 30 frames at this node's input is 300 source frames,
        # and a refinement read anywhere other than `node_warmup_frames` would
        # be one the conversion never saw.
        short = [(DECIMATOR, DecimateParams()), (WINDOWED, WindowParams(length=31))]
        long_window = [(DECIMATOR, DecimateParams()), (WINDOWED, WindowParams(length=91))]

        assert source_warmup_frames(short) == FrameCount(300)
        assert source_warmup_frames(long_window) == FrameCount(900)
        # And the bound is what a spec-only reading would have charged both.
        assert WINDOWED.warmup_frames == FrameCount(99)

    def test_a_refinement_above_the_bound_is_refused(self) -> None:
        # The silent direction, and the only one worth an exception. A bound is
        # what `sieve inspect` prints and what a reader checks a tool's cost
        # against; a configuration quietly needing more lead-in than the
        # declaration admits renders a preview from a tool that never settled.
        with pytest.raises(ValueError, match="exceeds the spec's declared bound"):
            input_warmup_frames((WINDOWED, WindowParams(length=101)), NO_FRAMES)

        # The bound itself is legal — it is a bound, not a strict one.
        at_bound = (WINDOWED, WindowParams(length=100))
        assert input_warmup_frames(at_bound, NO_FRAMES) == FrameCount(99)

    def test_a_non_positive_output_rate_is_refused_on_the_warmup_side(self) -> None:
        """The conversion's own `Raises:`, which only its lookahead twin proved.

        Asserted against `input_warmup_frames` directly rather than through
        `source_warmup_frames`: reaching it through a fold proves whichever
        guard the fold hits first, which is how this side came to be the
        unproven one — `plan.py` folds warmup before lookahead, so
        `test_a_non_positive_output_rate_is_refused_on_the_lookahead_side` in
        `tests/unit/test_plan.py` is answered by this function and its own
        refusal survives its deletion.

        What the guard buys over letting `at_input_of` refuse the same rate one
        call later is the tool's name: a graph of fifteen nodes reports which
        one stalled instead of only the number.
        """
        with pytest.raises(ValueError, match=r"stalled: output_rate must be positive"):
            input_warmup_frames((STALLED, StalledParams()), NO_FRAMES)
        # The other non-positive direction, and the one `at_input_of` would not
        # divide by: a negative rate runs the whole graph with the window
        # pointing backwards, which arrives as frames rather than as an error.
        with pytest.raises(ValueError, match=r"stalled: output_rate must be positive"):
            input_warmup_frames((STALLED, StalledParams(rate=-1)), FrameCount(5))

    def test_undeclared_rate_change_is_refused_at_registration(self) -> None:
        # Without this the gap reopens silently: a decimator whose spec forgot
        # `rate_changing` computes a correct rate that nothing is obliged to
        # consult, which is indistinguishable from having no rate at all.
        with pytest.raises(ValueError, match="overrides output_rate"):
            make_spec(params_model=DecimateParams)
        with pytest.raises(ValueError, match="does not override output_rate"):
            make_spec(rate_changing=True)

    def test_undeclared_selection_is_refused_at_registration(self) -> None:
        # The same gap for the other way of emitting fewer frames, and it fails
        # in the quieter direction: a span nobody declared runs over the whole
        # video and produces frames that are all individually right.
        with pytest.raises(ValueError, match="overrides selected_frames"):
            make_spec(params_model=SpanningParams)
        with pytest.raises(ValueError, match="does not override selected_frames"):
            make_spec(selecting=True)

    def test_a_tool_that_says_nothing_keeps_every_frame(self) -> None:
        # `ALL_FRAMES` is a value and not an absence, so the plan's fold is one
        # intersection over every node rather than a branch on which nodes are
        # spans — which is what keeps `pipeline` from having to name one.
        assert SampleParams().selected_frames() == ALL_FRAMES
        assert SpanningParams().selected_frames() == range(10, 20)


class TestLookahead:
    """The other half of a window, which v2's contract could not state.

    Every test name carries `lookahead` because the item's gate selects on it.
    """

    def test_a_lookahead_bound_needs_a_mode_with_a_window(self) -> None:
        # The cross-check that makes the declaration mean something. A
        # streaming node emits a frame as soon as it has consumed one, so
        # there is no later frame it could have read and nothing for the
        # executor to delay — a lookahead declared there is a claim about a
        # window the node does not have, and the tool would run trailing while
        # its declaration said centred.
        with pytest.raises(ValueError, match="lookahead_frames.*mode is"):
            make_spec(lookahead_frames=FrameCount(1))

        windowed = make_spec(mode=Mode.WINDOWED, lookahead_frames=FrameCount(1))
        assert windowed.lookahead_frames == FrameCount(1)

    def test_a_windowed_tool_may_still_declare_no_lookahead(self) -> None:
        # One-directional, like the `state_factory` refusal: v2's trailing
        # windows are windowed and read nothing ahead, and requiring the pair
        # would make every one of them declare a zero.
        assert make_spec(mode=Mode.WINDOWED).lookahead_frames == NO_FRAMES

    def test_a_negative_lookahead_cannot_be_declared_at_all(self) -> None:
        # Refused by `FrameCount` at the return inside the tool that computed
        # it, which is a better place to meet it than a check here that could
        # only see the number once it already had a home.
        class BackwardsParams(ParamsBase):
            def lookahead_frames(self) -> FrameCount:
                return FrameCount(-1)

        with pytest.raises(ValueError, match="non-negative"):
            node_lookahead_frames((CENTERED, BackwardsParams()))

    def test_a_fractional_lookahead_is_refused_as_bound_and_as_refinement(self) -> None:
        # Refused by `FrameCount` now, like the negative one above and in the
        # same place: neither declaration below builds a spec or reaches
        # `node_lookahead_frames`, because the count raises where it is
        # written. The case stays a lookahead case because the two boundaries
        # are what the item asked to be closed, and `TestWholeFrames` is where
        # the refusal itself is pinned.
        class HalfParams(CenteredWindowParams):
            def lookahead_frames(self) -> FrameCount:
                return FrameCount(2.5)  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="whole frames"):
            make_spec(mode=Mode.WINDOWED, lookahead_frames=FrameCount(2.5))
        with pytest.raises(TypeError, match="whole frames"):
            node_lookahead_frames((CENTERED, HalfParams()))

    def test_a_configured_lookahead_is_charged_instead_of_the_bound(self) -> None:
        # Warmup's refinement argument on the other side of the target: a
        # centred detector whose window is a parameter would otherwise delay
        # every emission by the widest window the model admits.
        assert node_lookahead_frames((CENTERED, CenteredWindowParams(length=11))) == FrameCount(5)
        assert CENTERED.lookahead_frames == FrameCount(50)

    def test_a_lookahead_refinement_above_the_bound_is_refused(self) -> None:
        # `node_warmup_frames`' silent direction, and it is silent here too:
        # the bound is what `sieve inspect` prints, and a configuration
        # quietly reading further ahead than the declaration admits is a
        # window the plan never decoded the tail of.
        with pytest.raises(ValueError, match="exceeds the spec's declared lookahead bound"):
            node_lookahead_frames((CENTERED, CenteredWindowParams(length=201)))

        at_bound = (CENTERED, CenteredWindowParams(length=101))
        assert node_lookahead_frames(at_bound) == FrameCount(50)

    def test_a_tool_with_no_lookahead_override_is_charged_the_specs_bound(self) -> None:
        # The half of `node_lookahead_frames` that keeps a constant lookahead
        # declarable once, on the spec, exactly as a constant warmup is.
        constant = make_spec(mode=Mode.WINDOWED, lookahead_frames=FrameCount(3))
        assert node_lookahead_frames((constant, SampleParams())) == FrameCount(3)
        assert node_lookahead_frames((IIR, SampleParams())) == NO_FRAMES

    def test_the_decorator_derives_the_lookahead_bound_from_the_params_model(self) -> None:
        # `max_warmup_frames`' treatment, and for its reason: the bound is a
        # fact about the parameter model's legal range, so writing it a second
        # time in the decoration is a copy that can disagree with the model
        # that owns it.
        registry = ToolRegistry()

        @register_tool(
            tool_id="centered",
            version="1.0.0",
            summary="Reads a window centred on its target.",
            accepts=ArraySpec(),
            emits=ArraySpec(),
            emissions=(Emission("out"),),
            element=ElementRelation.PRESERVED,
            mode=Mode.WINDOWED,
            settling_epsilon=0.0,
            warmup_kind=WarmupKind.BOUNDED,
            param_stereotypes={"length": ParamStereotype.SCALAR_RANGE},
            registry=registry,
        )
        class DecoratedCentered(CenteredWindowParams):
            pass

        assert DecoratedCentered.spec().lookahead_frames == FrameCount(50)

    def test_a_streaming_tool_whose_params_claim_lookahead_is_refused(self) -> None:
        # The mode cross-check reached through the decorator, which is where
        # every real tool meets it — the bound arrives from the params model,
        # so a centred kernel that forgot to say `WINDOWED` is caught by the
        # declaration it did make rather than by the one it omitted.
        with pytest.raises(ValueError, match="lookahead_frames.*mode is"):

            @register_tool(
                tool_id="centered",
                version="1.0.0",
                summary="Reads ahead without admitting to a window.",
                accepts=ArraySpec(),
                emits=ArraySpec(),
                emissions=(Emission("out"),),
                element=ElementRelation.PRESERVED,
                settling_epsilon=0.0,
                warmup_kind=WarmupKind.BOUNDED,
                registry=ToolRegistry(),
            )
            class StreamingCentered(CenteredWindowParams):
                pass

    def test_lookahead_is_an_execution_channel_declaration(self) -> None:
        # Beside `warmup_frames` and for its reason: it decides what the one
        # path decodes and when it emits, and two builds disagreeing about it
        # would produce the same frames at different cost rather than
        # different frames.
        assert SPEC_CHANNELS["lookahead_frames"] is Channel.EXECUTION


class TestWholeFrames:
    """A count that is not a whole number of frames, refused where it is made.

    01.3 guarded `lookahead_frames` alone, at the two boundaries that count
    passes through, and left every other `FrameCount` admitting a fraction. The
    refusal is `FrameCount.__post_init__`'s now — 01.1's anchor widened by
    `todo/a-frame-count-does-not-enforce-its-own-int.md` — so the counts below
    are the ones that were never guarded: a warmup bound, a warmup refinement,
    and the constructor the rate conversion reads through.

    Every test name carries `whole_frames` because the item's gate selects on it.
    """

    def test_a_fractional_warmup_bound_is_not_whole_frames(self) -> None:
        # The count that decides how far back a run decodes, and the one the
        # lookahead guard's twin left open: a bound is written by hand in a
        # decoration, which is exactly where a half of something gets typed.
        with pytest.raises(TypeError, match="whole frames"):
            make_spec(
                warmup_frames=FrameCount(2.5),  # pyright: ignore[reportArgumentType]
                settling_epsilon=0.0,
                warmup_kind=WarmupKind.BOUNDED,
            )

    def test_a_refined_warmup_is_not_whole_frames_either(self) -> None:
        # The refinement is the half that is computed rather than typed, so it
        # is the half a window length divided in two actually comes from.
        class HalfWindowParams(WindowParams):
            def warmup_frames(self) -> FrameCount:
                return FrameCount(self.length / 2)  # pyright: ignore[reportArgumentType]

        with pytest.raises(TypeError, match="whole frames"):
            input_warmup_frames((WINDOWED, HalfWindowParams(length=5)), NO_FRAMES)

    def test_a_count_is_whole_frames_before_the_rate_conversion_can_round_it(self) -> None:
        # Why the refusal had to move to the constructor rather than sit at one
        # more boundary. `at_input_of` ceils, so a fractional count crossing a
        # rate change comes out whole: 2.5 frames behind a 10:1 decimator is 25
        # source frames, a decode range nobody declared, arriving intact from a
        # step whose job is the rate and not the rounding.
        with pytest.raises(TypeError, match="whole frames"):
            FrameCount(2.5)  # pyright: ignore[reportArgumentType]

    def test_a_flag_is_not_whole_frames_however_int_a_bool_is(self) -> None:
        # `bool` subclasses `int`, so this is the one clause an int check does
        # not already cover — 01.3's review found the whole contract green with
        # it deleted. Kept, because it is the silent direction: a truthiness
        # value where a count goes is one frame of warmup, which is a legal
        # declaration nothing downstream has grounds to question.
        with pytest.raises(TypeError, match="whole frames"):
            FrameCount(True)  # pyright: ignore[reportArgumentType]
        assert FrameCount(1).frames == 1


class TestElementMeaning:
    def test_element_kind_docstring_counts_its_own_members(self) -> None:
        # The docstring shipped a count two members under the enum's length,
        # and was read as evidence about which axis a meaning belongs on
        # before it was read as a defect. Reading the number back out of the
        # prose is what makes the paragraph answerable to the enum: a literal
        # ban on the old wording would pass the moment the count is wrong
        # again in different words, and would fail on the fourth member.
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
        assert ElementKind.__doc__ is not None
        counts = re.findall(
            rf"\b({'|'.join(words)}) members?\b", ElementKind.__doc__, flags=re.IGNORECASE
        )
        assert len(counts) == 1, f"docstring should state its member count exactly once: {counts}"
        assert words[counts[0].lower()] == len(ElementKind)

    def test_an_array_emitter_without_an_element_is_refused_at_registration(self) -> None:
        # The whole enforcement. A default here would be free today — every
        # tool on the shelf that preserves would be right by accident — and
        # would turn the next element-redefining tool's omission into a CSV
        # column with an invented noun, which is the failure the declaration
        # exists to close. Refusing at registration is what makes forgetting
        # impossible rather than merely unlikely.
        with pytest.raises(ValueError, match="declares no element meaning"):
            make_spec(element=None)

    def test_the_element_hint_names_every_kind(self) -> None:
        # The refusal above is where a fixture author meets the rule, so the
        # kinds it offers are the whole of what they learn exists. It shipped
        # naming two of three, which is not a wrong count but a member that
        # cannot be reached from the only place it is advertised. Asserting
        # membership rather than a literal string is what makes the hint
        # answerable to the enum: a fourth kind fails here instead of quietly
        # not being offered.
        with pytest.raises(ValueError) as raised:
            make_spec(element=None)
        message = str(raised.value)
        assert [member.name for member in ElementKind if member.name not in message] == []

    def test_a_table_emitter_declaring_one_is_refused(self) -> None:
        # The mirror, and not symmetry for its own sake: `None` has to mean
        # "emits rows" rather than "an array emitter that forgot", or the
        # check above has a hole exactly the shape of a default.
        with pytest.raises(ValueError, match="a table has columns, not elements"):
            make_spec(emits=TableSpec(columns=("x",)), element=ElementKind.BLOCK)

    def test_aggregation_keeps_pixels_and_refuses_blocks(self) -> None:
        # The asymmetry `downsample` declares. A mean of pixels is the scene
        # sampled more coarsely and is still pixels, so a count over it is
        # honest; a mean of blocks is not a block, because a block is already
        # an aggregate, and no count threshold is denominated in it.
        assert node_element(ElementRelation.AGGREGATED, ElementKind.PIXEL) is ElementKind.PIXEL
        assert node_element(ElementRelation.AGGREGATED, ElementKind.BLOCK) is None

    def test_an_undeclarable_element_never_recovers_downstream(self) -> None:
        # Preserving `None` cannot invent a meaning. Without this a chain of
        # `block_signal -> downsample -> normalize` would report blocks again
        # two nodes after the meaning was lost.
        assert node_element(ElementRelation.PRESERVED, None) is None

    def test_a_kind_overrides_whatever_arrived(self) -> None:
        assert node_element(ElementKind.BLOCK, ElementKind.PIXEL) is ElementKind.BLOCK

    def test_names_follow_the_same_preserve_and_aggregate_rules(self) -> None:
        pixels = ElementNames("pixel", "pixels")
        blocks = ElementNames("block", "blocks")
        assert node_element_names(ElementKind.BLOCK, blocks, ElementKind.PIXEL, pixels) is blocks
        assert (
            node_element_names(ElementRelation.PRESERVED, None, ElementKind.BLOCK, blocks) is blocks
        )
        assert (
            node_element_names(ElementRelation.AGGREGATED, None, ElementKind.PIXEL, pixels)
            is pixels
        )
        assert (
            node_element_names(ElementRelation.AGGREGATED, None, ElementKind.BLOCK, blocks) is None
        )

    def test_an_element_redefinition_without_names_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no element_names"):
            make_spec(element=ElementKind.BLOCK)

    def test_relation_declarations_cannot_introduce_names(self) -> None:
        with pytest.raises(ValueError, match="relation declarations read names"):
            make_spec(element_names=ElementNames("block", "blocks"))

    def test_a_table_emitter_declaring_names_is_refused(self) -> None:
        with pytest.raises(ValueError, match="a table has columns"):
            make_spec(
                emits=TableSpec(columns=("x",)),
                element=None,
                element_names=ElementNames("point", "points"),
            )


class TestEmissions:
    """What a node of this tool can be asked to persist, and why the list cannot lie.

    VISION's save screen offers *all the possible* outputs a tool could produce,
    so the two ways the list stops being true are the two things checked here: an
    emission the tool never produces, and a product it produces that the list
    does not offer. Every test name carries `emission` because the item's gate
    selects on it.
    """

    def test_a_tool_declaring_no_emission_is_refused(self) -> None:
        # Required for `element`'s reason. A default would be correct today for
        # the seven single-output tools and would leave the next `block_signal`
        # offering one checkbox where it computes four — a list short by three,
        # which is the failure the declaration exists to close and the one
        # nothing downstream can detect.
        with pytest.raises(ValueError, match="declares no emission"):
            make_spec(emissions=())

    def test_an_emission_name_keeps_the_id_spelling_rule(self) -> None:
        # It becomes a file name and a CSV column, so it may not depend on case
        # folding or shell quoting to stay itself.
        with pytest.raises(ValueError, match="emission name must match"):
            Emission("Flow Speed")

    def test_one_name_cannot_be_two_emissions(self) -> None:
        with pytest.raises(ValueError, match="declares emission 'out' twice"):
            make_spec(emissions=(Emission("out"), Emission("out")))

    def test_two_emissions_need_a_parameter_that_chooses_between_them(self) -> None:
        # A node emits one stream, so a second unselected emission is one the
        # tool never produces — the save screen's lie, spelled as an omission.
        with pytest.raises(ValueError, match="nothing chooses between them"):
            make_spec(emissions=(Emission("first"), Emission("second")))

    def test_emissions_chosen_by_two_parameters_are_refused(self) -> None:
        # Two selecting parameters make the emission set their cross product,
        # which no declaration here states and the save screen would have to
        # invent.
        with pytest.raises(ValueError, match="one parameter"):
            make_spec(
                params_model=ProductParams,
                emissions=(Emission("soft", "product"), Emission("hard", "factor")),
                param_stereotypes={
                    "product": ParamStereotype.ENUM,
                    "factor": ParamStereotype.SCALAR_RANGE,
                },
            )

    def test_an_emission_selected_by_no_such_field_is_refused(self) -> None:
        with pytest.raises(ValueError, match=r"emissions name no such field.*mode"):
            make_spec(emissions=(Emission("soft", "mode"),))

    def test_an_emission_selected_by_an_open_parameter_is_refused(self) -> None:
        # An int has no closed set of values, so nothing could check the list
        # against it — and a list that cannot be checked is the prose this
        # field replaces.
        with pytest.raises(ValueError, match=r"factor.*is not a closed set"):
            make_spec(emissions=(Emission("soft", "factor"),))

    def test_an_emission_the_tool_never_produces_is_refused(self) -> None:
        with pytest.raises(ValueError, match="never produces"):
            make_spec(
                params_model=ProductParams,
                emissions=(
                    Emission("soft", "product"),
                    Emission("hard", "product"),
                    Emission("sideways", "product"),
                ),
                param_stereotypes={
                    "product": ParamStereotype.ENUM,
                    "factor": ParamStereotype.SCALAR_RANGE,
                },
            )

    def test_a_product_no_emission_offers_is_refused(self) -> None:
        # The other direction, and the one a save screen shows as a shorter
        # list rather than as an error: `hard` is reachable by setting the
        # parameter, so a list without it is missing an output the tool has.
        with pytest.raises(ValueError, match="offered by no emission"):
            make_spec(
                params_model=ProductParams,
                emissions=(Emission("soft", "product"),),
                param_stereotypes={
                    "product": ParamStereotype.ENUM,
                    "factor": ParamStereotype.SCALAR_RANGE,
                },
            )

    def test_the_exact_list_registers(self) -> None:
        spec = make_spec(
            params_model=ProductParams,
            emissions=(Emission("soft", "product"), Emission("hard", "product")),
            param_stereotypes={
                "product": ParamStereotype.ENUM,
                "factor": ParamStereotype.SCALAR_RANGE,
            },
        )
        assert spec.emission_names == ("soft", "hard")

    def test_emissions_are_an_identity_channel_declaration(self) -> None:
        # Beside `emits` and `element` rather than with the presentation fields
        # the save screen also reads: what a tool can produce is what the result
        # is, and the label a checkbox shows for one of them is already
        # `param_value_labels`. A tool that changes this set and keeps its
        # version is `run`'s defect, which is why `version` stands proxy for it.
        assert SPEC_CHANNELS["emissions"] is Channel.IDENTITY


class TestParamStereotypes:
    """How a param is populated, declared as data a Qt-free layer can hold.

    Nothing reads these until Phase 7's widget generator, so the checks below
    *are* the consumer for now — the licensed shape in
    `adr/declared-means-verified.md`. Every test name carries `stereotype`
    because the item's gate selects on it.
    """

    def test_the_stereotype_vocabulary_is_closed(self) -> None:
        # Kinds grow slowly and deliberately (`adr/gui-knows-kinds-not-tools.md`)
        # — the asymmetry that lets tools grow fast is that each new kind costs
        # generator work, so a member arriving without a tool that forced it
        # fails here rather than in a review nobody scheduled. `band` was forced
        # by `detect`, whose three interval params are on Hz, a block-power
        # value and a fraction rather than on the timeline `span` reaches.
        # `path` was forced by `pick`, the first tool whose input is a file the
        # user chose rather than an edge — and it is the one member a walk
        # outside the GUI reads, since the list of external files a project
        # needs is derived from this kind and never from a `tool_id`.
        assert [kind.value for kind in ParamStereotype] == [
            "scalar-range",
            "enum",
            "span",
            "band",
            "region",
            "point",
            "path",
        ]

    def test_every_param_field_declares_a_stereotype(self) -> None:
        # Totality is what makes the declaration worth having: a field the map
        # skips is a parameter the generator emits no widget for, and the
        # symptom is a control that is simply not on the panel — `primary_params`'
        # failure mode, minus the chance of noticing it on a tool you use.
        with pytest.raises(ValueError, match=r"declares no stereotype for.*anti_alias"):
            make_spec(param_stereotypes={"factor": ParamStereotype.SCALAR_RANGE})

    def test_a_stereotype_for_no_such_field_is_refused(self) -> None:
        with pytest.raises(ValueError, match=r"param_stereotypes names no such field.*scale"):
            make_spec(
                param_stereotypes={
                    "factor": ParamStereotype.SCALAR_RANGE,
                    "anti_alias": ParamStereotype.ENUM,
                    "scale": ParamStereotype.SCALAR_RANGE,
                }
            )

    def test_an_unknown_stereotype_kind_is_refused_by_name(self) -> None:
        # The vocabulary is closed by identity rather than by spelling: a tool
        # inventing `slider` is refused here, and so is one that wrote the right
        # word as a bare string, because a member is what the generator
        # dispatches on and a string that happens to match today is a match
        # nothing keeps true. `TypeError` rather than the file's usual
        # `ValueError` for `FrameCount.__post_init__`'s reason — this is not a
        # legal value used wrongly, it is not a `ParamStereotype`.
        with pytest.raises(TypeError, match=r"'slider'.*is not a stereotype"):
            make_spec(param_stereotypes={"factor": "slider", "anti_alias": ParamStereotype.ENUM})

    def test_a_composite_stereotype_on_one_bound_of_a_pair_is_refused(self) -> None:
        # `span`'s own shape before `adr/one-field-is-one-populated-value.md`:
        # two int fields each declaring `SPAN`, on the reading that both bounds
        # wear the kind because together they are one value. Refused because the
        # generator would then have to find the other half by adjacency or by
        # name, and — the reason that outlives the generator — a timeline drag on
        # a two-field value is two commands, two undo entries, and an
        # intermediate state this model's own validator refuses.
        with pytest.raises(ValueError, match=r"'first'.*'span'.*one component"):
            make_spec(
                params_model=SpanningParams,
                selecting=True,
                param_stereotypes={
                    "first": ParamStereotype.SPAN,
                    "last": ParamStereotype.SPAN,
                },
            )

    def test_every_composite_stereotype_reads_the_annotation_it_stands_over(self) -> None:
        # Both directions, because a rule that only refuses could be satisfied by
        # refusing every composite kind there is. The refusals are the whole
        # vocabulary minus the two one-field kinds, each on a plain int; the
        # acceptance is the three shapes a whole value actually arrives in on the
        # shelf — `detect`'s bands as bare pairs, its `count_frac` as a pair that
        # can be unset, and `crop`'s region as a type of its own. The optional
        # one is where a union could smuggle a scalar through, so every branch of
        # it is asked rather than the first.
        for kind in (ParamStereotype.BAND, ParamStereotype.REGION, ParamStereotype.POINT):
            with pytest.raises(ValueError, match=rf"'factor'.*{kind.value!r}.*one component"):
                make_spec(param_stereotypes={"factor": kind, "anti_alias": ParamStereotype.ENUM})

        spec = make_spec(params_model=CompositeParams, param_stereotypes=COMPOSITE_KINDS)

        assert spec.param_stereotypes == COMPOSITE_KINDS

    def test_a_composite_stereotype_on_an_arity_the_shelf_does_not_declare_a_union(self) -> None:
        # The case above accepts an optional pair, and an optional pair is one
        # branch wide once `NoneType` is dropped — so it cannot tell a reduction
        # over branches from reading the first one. This is the union the rule was
        # written for: a field that could arrive as a bare int is a field the
        # generator has to emit a spinbox for, so the narrowest branch decides and
        # the pair-shaped branch does not earn the whole field a pair of handles.
        with pytest.raises(ValueError, match=r"'scalar_or_pair'.*'band'.*one component"):
            make_spec(
                params_model=UndeclaredArityParams,
                param_stereotypes={
                    "scalar_or_pair": ParamStereotype.BAND,
                    "unbounded": ParamStereotype.SCALAR_RANGE,
                },
            )

    def test_a_composite_stereotype_on_an_arity_the_shelf_does_not_declare_a_variadic(self) -> None:
        # A `tuple[X, ...]` has as many components as the value happens to be
        # long, which is to say the annotation does not answer the arity question
        # at all — and a kind whose editor draws a fixed number of handles cannot
        # be handed a length nobody has bounded. Refused rather than accepted at
        # the two the default happens to hold.
        with pytest.raises(ValueError, match=r"'unbounded'.*'region'.*one component"):
            make_spec(
                params_model=UndeclaredArityParams,
                param_stereotypes={
                    "scalar_or_pair": ParamStereotype.SCALAR_RANGE,
                    "unbounded": ParamStereotype.REGION,
                },
            )

    def test_a_stereotype_of_enum_over_an_annotation_with_no_choices_is_refused(self) -> None:
        # `ENUM` is the one kind whose control is built from the annotation's
        # *values* rather than from its bounds, and `gui/param_form.py`'s builder
        # falls back to `(True, False)` for a property that writes no `enum`
        # keyword. So a `str` field wearing the kind gets a two-item true/false
        # drop list holding neither of the values it can take — a degradation
        # with no symptom, in a module whose whole argument is that a kind the
        # generator cannot serve is loud.
        #
        # The two annotations the fallback is right about are accepted in the
        # same breath, because refusing every `ENUM` would satisfy a rule
        # written only as a refusal.
        with pytest.raises(ValueError, match=r"'label'.*'enum'.*enumerates nothing"):
            make_spec(
                params_model=UnenumerableParams,
                param_stereotypes={
                    "label": ParamStereotype.ENUM,
                    "product": ParamStereotype.ENUM,
                    "anti_alias": ParamStereotype.ENUM,
                },
            )

        enumerable = {
            "label": ParamStereotype.SCALAR_RANGE,
            "product": ParamStereotype.ENUM,
            "anti_alias": ParamStereotype.ENUM,
        }
        spec = make_spec(params_model=UnenumerableParams, param_stereotypes=enumerable)

        assert spec.param_stereotypes == enumerable

    def test_stereotypes_are_a_presentation_channel_declaration(self) -> None:
        # Beside `primary_params` and for its reason: never hashed, never read
        # by the executor, and the partition is the only thing that can see a
        # field carrying GUI policy in core.
        assert SPEC_CHANNELS["param_stereotypes"] is Channel.PRESENTATION


class TestDisplaySurfaces:
    """A band names the picture it is dragged on, and the picture names a filler.

    One rule with two ends, and each end is a different silence. A band with no
    surface is a control the generator can build and cannot place — the failure
    `detect` carried for two phases, three pairs of handles over no plot. A
    surface with nothing behind it is `adr/declared-means-verified.md`'s own
    case: a declaration stored against a consumer that never arrives, which
    nothing goes red for because a picture that is never drawn looks exactly
    like one nobody opened.
    """

    def test_a_band_with_no_declared_surface_is_refused(self) -> None:
        with pytest.raises(ValueError, match=r"declares a band on \['band'\].*no surface"):
            make_spec(
                params_model=CompositeParams,
                param_stereotypes=COMPOSITE_KINDS,
                param_surfaces={"optional_band": DisplaySurface.COUNT},
                display=stub_display,
            )

        placed = {"band": DisplaySurface.SCALOGRAM, "optional_band": DisplaySurface.COUNT}
        spec = make_spec(
            params_model=CompositeParams,
            param_stereotypes=COMPOSITE_KINDS,
            param_surfaces=placed,
            display=stub_display,
        )

        # Both bands, and only the bands: `region` is populated on the canvas,
        # which the GUI already owns.
        assert spec.param_surfaces == placed
        assert spec.display_surfaces == {DisplaySurface.SCALOGRAM, DisplaySurface.COUNT}

    def test_a_declared_surface_on_a_kind_that_is_not_a_band_is_refused(self) -> None:
        # A region is drawn on the frame and a span on the timeline, and both of
        # those surfaces are the GUI's own. A tool naming a picture for one of
        # them would be a second answer to where it is edited, competing with
        # the editor that already exists for the kind.
        with pytest.raises(ValueError, match=r"surface for \['region'\].*not a band"):
            make_spec(
                params_model=CompositeParams,
                param_stereotypes=COMPOSITE_KINDS,
                param_surfaces={
                    "band": DisplaySurface.TRACE,
                    "optional_band": DisplaySurface.TRACE,
                    "region": DisplaySurface.TRACE,
                },
                display=stub_display,
            )

    def test_a_declared_surface_for_no_such_field_is_refused(self) -> None:
        # `param_stereotypes`' rename case: a band renamed with the surface map
        # left behind would otherwise leave the tool declaring a picture for a
        # parameter that no longer exists, and the band that replaced it
        # unplaced.
        with pytest.raises(ValueError, match=r"param_surfaces names no such field.*hz"):
            make_spec(
                params_model=CompositeParams,
                param_stereotypes=COMPOSITE_KINDS,
                param_surfaces={
                    "band": DisplaySurface.TRACE,
                    "optional_band": DisplaySurface.TRACE,
                    "hz": DisplaySurface.SCALOGRAM,
                },
                display=stub_display,
            )

    def test_a_declared_surface_nothing_fills_is_refused(self) -> None:
        with pytest.raises(ValueError, match=r"points at nothing that fills them"):
            make_spec(
                params_model=CompositeParams,
                param_stereotypes=COMPOSITE_KINDS,
                param_surfaces={
                    "band": DisplaySurface.TRACE,
                    "optional_band": DisplaySurface.COUNT,
                },
                display=None,
            )

    def test_a_filler_for_no_declared_surface_is_refused(self) -> None:
        # The other end, and the one that is pure cost rather than a missing
        # picture: the executor would call it every frame of every watched run
        # and no parameter would read what came back.
        with pytest.raises(ValueError, match=r"declares no surface"):
            make_spec(display=stub_display)

    def test_a_declared_surface_is_an_execution_channel_declaration(self) -> None:
        # Not presentation, though a surface kind is presentation vocabulary in
        # every other respect. That row says the executor never reads it, and
        # the executor reads both of these: it fills the channel and refuses a
        # tool that fills the wrong one.
        assert SPEC_CHANNELS["param_surfaces"] is Channel.EXECUTION
        assert SPEC_CHANNELS["display"] is Channel.EXECUTION


class TestResolvedSchema:
    """The pointer walk's degradation, which is not `sieve inspect`'s claim.

    `tests/unit/test_inspect_cmd.py` holds what a reader sees printed, including
    the union the walk declines to reduce. What is here is the branch no printed
    line can reach: a pointer into something other than `$defs`, which the walk
    argues it degrades over rather than raises on.
    """

    def test_a_pointer_pydantic_does_not_write_leaves_the_property_unresolved(self) -> None:
        # Two claims, and the equality carries both. Degraded means the
        # property's own keys and nothing else — no raise, since neither reader
        # is a place to fail a tool over a schema keyword, and no definition
        # either, since the one this pointer aligns with is a document it never
        # named. The same `ROI` field resolves under pydantic's own template, so
        # what is under test is the pointer and not the annotation.
        described = resolved_schema(ForeignPointerParams)["properties"]["region"]

        assert described == {"default": {"x": 0, "y": 0, "width": 1, "height": 1}}
        assert resolved_schema(CompositeParams)["properties"]["region"]["type"] == "object"


class TestGuidance:
    """What a tool is for, promoted off the module docstring and onto the spec.

    Phase 3 through 6 kept it in the docstring because the expander that shows
    it did not exist (`PLAN.md`, and `tools/__init__.py` on the per-tool `.md`
    v2 had instead). The promotion is what this asserts, and the shape of the
    assertion is the point: a field a reader can hold, not a `__doc__` a widget
    reads at runtime.
    """

    def test_guidance_is_spec_data_every_shelf_tool_declares(self) -> None:
        """Presentation data, one string per tool, and never the docstring.

        Three claims, and the third is the one that would decay silently. The
        channel is `param_stereotypes`' claim for its reason. The shelf sweep is
        what makes the field cost something: a tool registering without guidance
        would leave the expander blank on that step and nothing else would say
        so, and the sweep is over `discover()` so a new module is covered the day
        it lands rather than when somebody remembers this list.

        Not the module docstring, and not the summary either. Both are the
        shortcuts that would make the promotion nominal — a docstring handed
        through carries this repo's ADR citations and v2 archaeology to a user
        who wants to know what the knob does, and a summary repeated is the
        caption they can already read on the collapsed step.
        """
        import sys

        from sieve.tools import discover

        assert SPEC_CHANNELS["guidance"] is Channel.PRESENTATION

        shelf = discover()
        assert shelf, "the scan found no tools, so the sweep below asserts nothing"
        for spec in shelf:
            module = sys.modules[spec.params_model.__module__]
            assert spec.guidance.strip(), f"{spec.tool_id} declares no guidance"
            assert spec.guidance != module.__doc__
            assert spec.guidance != spec.summary

    def test_guidance_defaults_to_nothing_for_a_spec_with_no_user(self) -> None:
        """A spec built without one is legal, for `run`'s reason.

        Every graph test in this repo builds specs nobody will ever open a panel
        on, and requiring help text of them would teach that the field is
        ceremony to be filled in. What makes the default safe rather than silent
        is the sweep above: it is the shelf a user meets, and the shelf is where
        the field is required.
        """
        assert make_spec().guidance == ""


class TestArraySpec:
    def test_disjoint_channel_sets_do_not_chain(self) -> None:
        gray_only = ArraySpec(channels=(ChannelSpec.GRAY,))
        rgb_only = ArraySpec(channels=(ChannelSpec.RGB,))
        assert not gray_only.admits(rgb_only)

    def test_wildcard_admits_anything(self) -> None:
        # Permissive by construction: the static check rejects graphs that
        # cannot work, not graphs that cannot be proven to work.
        assert ArraySpec().admits(ArraySpec(dtypes=("float32",), channels=(ChannelSpec.RGB,)))
        assert ArraySpec(dtypes=("uint8",)).admits(ArraySpec(channels=(ChannelSpec.GRAY,)))

    def test_overlap_is_enough(self) -> None:
        accepts = ArraySpec(dtypes=("uint8", "float32"))
        assert accepts.admits(ArraySpec(dtypes=("float32", "float64")))


class TestStreamKind:
    def test_rows_and_frames_never_chain_in_either_direction(self) -> None:
        # The one mismatch a wildcard cannot rescue: a detector emitting
        # coordinates has nothing an array input can consume, and unstated
        # dtypes on the array side do not make it admissible.
        assert not ArraySpec().admits(TableSpec())
        assert not TableSpec().admits(ArraySpec())

    def test_missing_columns_are_rejected_where_missing_dtypes_are_not(self) -> None:
        # Columns are conjunctive and dtype sets are disjunctive: a tool that
        # needs `x` and `y` cannot run on a table that supplies only `x`, while
        # one accepting uint8 or float32 runs on either.
        assert TableSpec(columns=("x", "y")).admits(TableSpec(columns=("frame", "x", "y")))
        assert not TableSpec(columns=("x", "y")).admits(TableSpec(columns=("frame", "x")))
        assert TableSpec(columns=("x", "y")).admits(TableSpec())


class TestParamsBase:
    def test_unknown_parameter_is_rejected(self) -> None:
        # Accepting it would run the default and produce a cache key identical
        # to the run the user meant to vary.
        with pytest.raises(ValueError, match="anti_aliasing"):
            SampleParams(anti_aliasing=False)  # pyright: ignore[reportCallIssue]

    def test_canonical_json_is_sorted_and_whitespace_free(self) -> None:
        assert SampleParams().canonical_json() == '{"anti_alias":true,"factor":2}'

    def test_params_are_frozen(self) -> None:
        params = SampleParams()
        with pytest.raises(ValueError, match="frozen"):
            params.factor = 4


class TestToolRegistry:
    def test_duplicate_id_and_version_is_refused(self) -> None:
        registry = ToolRegistry()
        registry.register(make_spec())
        with pytest.raises(DuplicateToolError, match="already registered"):
            registry.register(make_spec())

    def test_versions_coexist_and_latest_is_numeric(self) -> None:
        # `1.9.0` sorts above `1.10.0` as text, and an old pipeline naming
        # `1.0.0` must keep getting `1.0.0` after newer versions ship.
        registry = ToolRegistry()
        for version in ("1.0.0", "1.9.0", "1.10.0"):
            registry.register(make_spec(version=version))
        assert registry.latest("downsample").version == "1.10.0"
        assert registry.get("downsample", "1.0.0").version == "1.0.0"
        assert registry.versions("downsample") == ("1.0.0", "1.9.0", "1.10.0")

    def test_unknown_lookups_raise(self) -> None:
        registry = ToolRegistry()
        with pytest.raises(UnknownToolError):
            registry.get("downsample", "1.0.0")
        with pytest.raises(UnknownToolError):
            registry.latest("downsample")

    def test_decorator_registers_and_binds_the_spec(self) -> None:
        registry = ToolRegistry()

        @register_tool(
            tool_id="blur",
            version="2.1.0",
            summary="Gaussian blur.",
            accepts=ArraySpec(),
            emits=ArraySpec(),
            emissions=(Emission("out"),),
            element=ElementRelation.PRESERVED,
            primary_params=("factor",),
            param_stereotypes={
                "factor": ParamStereotype.SCALAR_RANGE,
                "anti_alias": ParamStereotype.ENUM,
            },
            registry=registry,
        )
        class BlurParams(SampleParams):
            pass

        spec = registry.latest("blur")
        assert spec.params_model is BlurParams
        assert BlurParams.__tool_spec__ is spec
        assert BlurParams.spec() is spec
        assert registry.ids() == ("blur",)

    def test_an_undecorated_params_model_refuses_to_name_a_spec(self) -> None:
        with pytest.raises(TypeError, match="never decorated"):
            SampleParams.spec()

    def test_decorator_derives_warmup_bound_from_the_params_model(self) -> None:
        registry = ToolRegistry()

        @register_tool(
            tool_id="settling",
            version="1.0.0",
            summary="Settles before it speaks.",
            accepts=ArraySpec(),
            emits=ArraySpec(),
            emissions=(Emission("out"),),
            element=ElementRelation.PRESERVED,
            settling_epsilon=0.0,
            warmup_kind=WarmupKind.BOUNDED,
            registry=registry,
        )
        class SettlingParams(ParamsBase):
            @classmethod
            def max_warmup_frames(cls) -> FrameCount:
                return FrameCount(7)

        assert SettlingParams.spec().warmup_frames == FrameCount(7)


def decorator_keywords() -> set[str]:
    """`register_tool`'s keywords, less `registry`, which is the decorator's own.

    `params_model` is the other name the two lists differ by, and it is absent
    here rather than removed: the decorated class supplies it, which is the one
    field of a spec that cannot be written in the decoration. `warmup_frames`
    and `lookahead_frames` are absent because the params model derives both
    bounds.
    """
    parameters = inspect.signature(register_tool).parameters.values()
    return {p.name for p in parameters if p.kind is p.KEYWORD_ONLY} - {"registry"}


#: A registration with every optional keyword left at its default, so a probe
#: below can be the only thing that differs from it.
BASE: dict[str, Any] = {
    "tool_id": "blur",
    "version": "2.1.0",
    "summary": "Gaussian blur.",
    "accepts": ArraySpec(),
    "emits": ArraySpec(),
    "emissions": (Emission("out"),),
    "element": ElementRelation.PRESERVED,
}


def probe_run(params: ParamsBase, window: FrameSpan, state: None) -> Frame:
    """A `ToolRun` that does nothing, for the `run` probe below.

    The spec stores the pointer and asks nothing of it, so what this returns is
    never reached; what the probe checks is that the keyword arrives at the
    field, which a shared `None` default cannot show.
    """
    del params, state
    return window.target


class ProbeSource:
    """A `ToolSource` that resolves nothing, for the `source` probe below.

    `probe_run`'s treatment for the other pointer: the spec stores it and asks
    nothing of it, so neither method is ever reached and what the probe checks
    is that the keyword arrives at the field.
    """

    decoded = False

    def file(self, params: ParamsBase, /) -> Path:
        del params
        return Path("nowhere")

    def read(self, params: ParamsBase, index: FrameIndex, /, *, luma: bool) -> Frame:
        del params, luma
        return Frame(data=np.zeros((1, 1), dtype=np.uint8), index=index, channels=ChannelSpec.GRAY)


stub_source = ProbeSource()


#: One legal value per keyword, differing from both that parameter's default
#: and `BASE`'s value — so a keyword the decorator accepts and never forwards
#: leaves the spec holding the other one. Applied one at a time rather than all
#: at once, because several pairs are illegal together: `state_factory` requires
#: `stateful`, and both probes are the non-default.
PROBES: dict[str, Any] = {
    "tool_id": "probe",
    "version": "3.2.1",
    "summary": "Something else entirely.",
    "accepts": ArraySpec(dtypes=("float32",)),
    "emits": ArraySpec(channels=(ChannelSpec.GRAY,)),
    "emissions": (Emission("other"),),
    # Any callable: the spec stores the pointer and checks nothing about it, and
    # what may call it is `pipeline/executor.py`'s question.
    "run": probe_run,
    # `run`'s alternative rather than a second pointer beside it, so this probe
    # is the one row that also drops `BASE`'s — the spec refuses both together.
    "source": stub_source,
    "mode": Mode.WINDOWED,
    "settling_epsilon": 0.25,
    "rate_changing": True,
    "selecting": True,
    "deterministic": False,
    "stateful": True,
    "warmup_kind": WarmupKind.EPSILON,
    "state_factory": dict,
    "guidance": "Turn the factor up until the frames are small enough.",
    "primary_params": ("factor",),
    "caption": (CaptionPart(label="factor", param="factor"),),
    "param_value_labels": {"anti_alias": {"True": "averaged"}},
    "param_stereotypes": {
        "factor": ParamStereotype.SCALAR_RANGE,
        "anti_alias": ParamStereotype.ENUM,
    },
    "element": ElementKind.BLOCK,
    "element_names": ElementNames("block", "blocks"),
    # A co-required trio, like the two element rows: no one of them may stand
    # alone, so each probe carries the others in the loop below.
    "param_surfaces": {"band": DisplaySurface.SCALOGRAM},
    "param_axes": {"band": AxisRelation.INPUT_VALUES},
    "display": stub_display,
}


class TestDecoratorMatchesSpec:
    """The decorator's keywords are `ToolSpec`'s fields, written out twice more.

    The duplication is one field addition away from drifting silently, and the
    drift does not crash: a field added to the spec with a default is simply
    unreachable from the decorator, so every tool gets the default and nothing
    says so. Fixing it — building the spec from `**kwargs`, or generating the
    signature — would cost every keyword the static type a tool author is
    checked against at the one place they write it, so the copies stay and these
    two tests hold them in step.
    """

    def test_the_keywords_are_the_specs_field_list(self) -> None:
        # Set equality, not containment, and each direction catches a different
        # half: the spec growing a field the decorator never learned about, and
        # a keyword left behind after the field it filled was removed.
        assert decorator_keywords() == {f.name for f in fields(ToolSpec)} - {
            "params_model",
            "warmup_frames",
            "lookahead_frames",
        }

    def test_every_keyword_reaches_the_field_it_names(self) -> None:
        # The third copy — `decorate`'s body — which the signature test cannot
        # see. A keyword accepted and then not forwarded to the `ToolSpec(...)`
        # call is the same silent default with the same absence of a symptom.
        assert set(PROBES) == decorator_keywords()

        class ProbeParams(SampleParams):
            pass

        class RateProbeParams(DecimateParams):
            pass

        class SelectProbeParams(SpanningParams):
            pass

        class BandProbeParams(ParamsBase):
            """A pair-shaped field, which is what a band may stand over."""

            band: tuple[float, float] = (0.0, 1.0)

        class PathProbeParams(ParamsBase):
            """A pattern-shaped field, which is what a path may stand over."""

            pattern: str = ""

        # The probes that cannot ride on the shared params model: each names a
        # flag or a pointer the spec refuses unless the decorated class carries
        # the matching override or field, and refuses that without.
        models = {
            "rate_changing": RateProbeParams,
            "selecting": SelectProbeParams,
            "param_surfaces": BandProbeParams,
            "param_axes": BandProbeParams,
            "display": BandProbeParams,
            "source": PathProbeParams,
        }

        for name, probe in PROBES.items():
            registry = ToolRegistry()
            model = models.get(name, ProbeParams)
            # Stereotypes are total over the params model, and the model varies
            # with the probe, so the map is derived before the probe is applied
            # rather than carried in `BASE` — where it would be wrong for the
            # two rows that ride on a different one.
            stereotypes = dict.fromkeys(model.model_fields, ParamStereotype.SCALAR_RANGE)
            values = {**BASE, "param_stereotypes": stereotypes, name: probe}
            if name == "element":
                values["element_names"] = ElementNames("block", "blocks")
            elif name == "element_names":
                values["element"] = ElementKind.BLOCK
            elif name == "state_factory":
                values["stateful"] = True
                values["warmup_kind"] = WarmupKind.EPSILON
                values["settling_epsilon"] = 0.25
            elif name == "stateful":
                values["warmup_kind"] = WarmupKind.EPSILON
                values["settling_epsilon"] = 0.25
            elif name == "warmup_kind":
                values["stateful"] = True
                values["settling_epsilon"] = 0.25
            elif name == "source":
                # The one probe that is an alternative rather than an addition:
                # a source tool names the file it opens and declares no run.
                values["param_stereotypes"] = {"pattern": ParamStereotype.PATH}
            elif name in ("param_surfaces", "param_axes", "display"):
                # The one probe trio that also moves the stereotype map: a
                # surface and an axis may only stand over a band, and the
                # derived map above declares every field a scalar.
                values["param_stereotypes"] = {"band": ParamStereotype.BAND}
                if name != "param_surfaces":
                    values["param_surfaces"] = {"band": DisplaySurface.TRACE}
                if name != "param_axes":
                    values["param_axes"] = {"band": AxisRelation.INPUT_VALUES}
                if name != "display":
                    values["display"] = stub_display
            decorated = register_tool(**values, registry=registry)(model)

            spec = decorated.__tool_spec__
            assert spec is not None
            assert getattr(spec, name) == probe
