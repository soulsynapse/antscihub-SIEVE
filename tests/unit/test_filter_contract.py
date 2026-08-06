"""The filter contract: what a spec refuses to claim, and what the shelf holds.

Each test here stands in for a way the contract stops being load-bearing: a
spec that promises more than it can, a params model that swallows a typo, a
cache-key input that is not byte-stable, or a registry that hands back the
wrong version of a filter an old pipeline named.
"""

from __future__ import annotations

import inspect
from dataclasses import fields
from fractions import Fraction
from typing import Any

import pytest

from sieve.core.filter_base import (
    ALL_FRAMES,
    SPEC_CHANNELS,
    ArraySpec,
    AuthoringGroup,
    CaptionPart,
    CostEstimate,
    ElementKind,
    ElementNames,
    ElementRelation,
    FilterSpec,
    Mode,
    ParamsBase,
    TableSpec,
    caption_for_params,
    input_warmup_frames,
    node_element,
    node_element_names,
    source_warmup_frames,
)
from sieve.core.filter_registry import (
    DuplicateFilterError,
    FilterRegistry,
    UnknownFilterError,
    register_filter,
)
from sieve.core.types import NO_FRAMES, WORK_UNIT_ANCHOR, ChannelSpec, FrameCount, WorkUnits

COST = CostEstimate(work_per_megapixel=WorkUnits(1.0))


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


class SpanningParams(ParamsBase):
    """Keeps a range of the frames it is handed: neither the rate nor the size.

    The third way a filter can emit less than it consumed, and the one that is
    not arithmetic — the survivors keep their numbering, so nothing in the warmup
    fold has to cross it.
    """

    first: int = 10
    last: int = 20

    def selected_frames(self) -> range:
        return range(self.first, self.last)


class DownsampleParams(ParamsBase):
    """Halves both axes per `factor`: frame size changes, rate does not."""

    factor: int = 2

    def frame_bytes_ratio(self) -> float:
        return 1.0 / (self.factor**2)


class WindowParams(ParamsBase):
    """A trailing window whose length *is* the lead-in.

    The shape `temporal_baseline` has and the reason warmup became
    params-derived: a static declaration would have to be the window's upper
    bound, charged to every run whatever window it asked for.
    """

    length: int = 5

    def warmup_frames(self) -> FrameCount:
        return FrameCount(self.length - 1)


def make_spec(**overrides: object) -> FilterSpec:
    fields: dict[str, object] = {
        "filter_id": "downsample",
        "version": "1.0.0",
        "summary": "Reduce spatial resolution by an integer factor.",
        "params_model": SampleParams,
        "accepts": ArraySpec(),
        "emits": ArraySpec(),
        "element": ElementRelation.PRESERVED,
        "cost": COST,
        "authoring_group": AuthoringGroup.SPATIAL_PREP,
    }
    fields.update(overrides)
    return FilterSpec(**fields)  # pyright: ignore[reportArgumentType]


#: The three specs the rate and storage tests chain. Built once at module scope
#: because constructing them is what several tests do *before* the thing they
#: are about, not part of it.
DECIMATOR = make_spec(filter_id="decimate", params_model=DecimateParams, rate_changing=True)
DOWNSAMPLER = make_spec(filter_id="downsample", params_model=DownsampleParams)
IIR = make_spec(filter_id="iir", warmup_frames=FrameCount(5), settling_epsilon=0.0)
INTERPOLATOR = make_spec(
    filter_id="interpolate", params_model=InterpolateParams, rate_changing=True
)
#: Declares a bound of 99 and refines it per configuration.
WINDOWED = make_spec(
    filter_id="window",
    params_model=WindowParams,
    warmup_frames=FrameCount(99),
    settling_epsilon=0.0,
)


class TestFilterSpec:
    def test_backend_agnostic_requires_deterministic(self) -> None:
        # The incoherent pair: a filter that cannot reproduce its own output
        # cannot agree bit for bit with another backend's. Allowed through, it
        # would drop backend identity from the cache key of the one kind of
        # filter whose output nothing can reproduce.
        with pytest.raises(ValueError, match="backend_agnostic requires deterministic"):
            make_spec(backend_agnostic=True, deterministic=False)

    def test_nonzero_warmup_declares_the_epsilon_it_settles_to(self) -> None:
        with pytest.raises(ValueError, match="settling_epsilon must be declared"):
            make_spec(warmup_frames=FrameCount(1))

        assert make_spec(warmup_frames=FrameCount(1), settling_epsilon=0.0).settling_epsilon == 0.0

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

    def test_authoring_hidden_params_must_name_real_fields(self) -> None:
        with pytest.raises(ValueError, match=r"authoring_hidden_params names no such field"):
            make_spec(authoring_hidden_params=("scale_factor",))

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

    def test_defaults_are_the_conservative_claims(self) -> None:
        spec = make_spec()
        assert (spec.backend_agnostic, spec.deterministic, spec.mode) == (
            False,
            True,
            Mode.STREAMING,
        )

    def test_every_field_is_in_exactly_one_channel(self) -> None:
        # The direction that earns the test is the first: a field added without
        # a row fails at the moment it is written, so the next `primary_params`
        # cannot arrive as GUI policy in core unclassified. The second direction
        # keeps the mapping from outliving a field it names, which would make
        # the partition read total while covering something gone.
        declared = {f.name for f in fields(FilterSpec)}
        assert declared - set(SPEC_CHANNELS) == set()
        assert set(SPEC_CHANNELS) - declared == set()


class TestRate:
    def test_warmup_behind_a_decimator_is_counted_in_source_frames(self) -> None:
        # The whole reason rate is declared. Five frames of warmup downstream
        # of a 10:1 decimator is fifty source frames; ARCHITECTURE's plain sum
        # says fifteen, and the resulting preview renders an IIR that never
        # settled rather than failing in any visible way.
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
        # what `sieve inspect` prints and what a reader checks a filter's cost
        # against; a configuration quietly needing more lead-in than the
        # declaration admits renders a preview from a filter that never settled.
        with pytest.raises(ValueError, match="exceeds the spec's declared bound"):
            input_warmup_frames((WINDOWED, WindowParams(length=101)), NO_FRAMES)

        # The bound itself is legal — it is a bound, not a strict one.
        at_bound = (WINDOWED, WindowParams(length=100))
        assert input_warmup_frames(at_bound, NO_FRAMES) == FrameCount(99)

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

    def test_a_filter_that_says_nothing_keeps_every_frame(self) -> None:
        # `ALL_FRAMES` is a value and not an absence, so the plan's fold is one
        # intersection over every node rather than a branch on which nodes are
        # spans — which is what keeps `pipeline` from having to name one.
        assert SampleParams().selected_frames() == ALL_FRAMES
        assert SpanningParams().selected_frames() == range(10, 20)


class TestElementMeaning:
    def test_an_array_emitter_without_an_element_is_refused_at_registration(self) -> None:
        # The whole enforcement. A default here would be free today — every
        # filter on the shelf that preserves would be right by accident — and
        # would turn the next element-redefining filter's omission into a CSV
        # column with an invented noun, which is the failure the declaration
        # exists to close. Refusing at registration is what makes forgetting
        # impossible rather than merely unlikely.
        with pytest.raises(ValueError, match="declares no element meaning"):
            make_spec(element=None)

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


class TestStoredBytes:
    def test_cost_is_work_units_against_one_anchor(self) -> None:
        # This is the item boundary: a filter may declare relative work and a
        # peak working set, but not a reference-machine timing coefficient that
        # an uncalibrated install could print as if it meant seconds.
        assert {field.name for field in fields(CostEstimate)} == {
            "work_per_megapixel",
            "peak_bytes_per_input_byte",
        }
        assert COST.work_per_megapixel == WorkUnits(1.0)
        assert CostEstimate.anchor == WORK_UNIT_ANCHOR
        assert "seconds_per_megapixel" not in dir(COST)

    def test_stored_size_multiplies_rate_by_frame_size(self) -> None:
        # Two filters that know nothing about each other: one drops nine frames
        # in ten, the other quarters what is left. Applying either alone is off
        # by the other's factor, which is the shape of the storage prediction
        # VISION step 4 asks for and step 5 drives a suggestion off.
        chained = DECIMATOR.stored_bytes_ratio(DecimateParams()) * DOWNSAMPLER.stored_bytes_ratio(
            DownsampleParams()
        )
        assert chained == pytest.approx(1 / 40)
        # Working set is a different quantity and stays one: `CostEstimate`
        # describes what is held at once, not what is written.
        assert DOWNSAMPLER.cost.peak_bytes_per_input_byte == 2.0


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
        # Columns are conjunctive and dtype sets are disjunctive: a filter that
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


class TestFilterRegistry:
    def test_duplicate_id_and_version_is_refused(self) -> None:
        registry = FilterRegistry()
        registry.register(make_spec())
        with pytest.raises(DuplicateFilterError, match="already registered"):
            registry.register(make_spec())

    def test_versions_coexist_and_latest_is_numeric(self) -> None:
        # `1.9.0` sorts above `1.10.0` as text, and an old pipeline naming
        # `1.0.0` must keep getting `1.0.0` after newer versions ship.
        registry = FilterRegistry()
        for version in ("1.0.0", "1.9.0", "1.10.0"):
            registry.register(make_spec(version=version))
        assert registry.latest("downsample").version == "1.10.0"
        assert registry.get("downsample", "1.0.0").version == "1.0.0"
        assert registry.versions("downsample") == ("1.0.0", "1.9.0", "1.10.0")

    def test_unknown_lookups_raise(self) -> None:
        registry = FilterRegistry()
        with pytest.raises(UnknownFilterError):
            registry.get("downsample", "1.0.0")
        with pytest.raises(UnknownFilterError):
            registry.latest("downsample")

    def test_decorator_registers_and_binds_the_spec(self) -> None:
        registry = FilterRegistry()

        @register_filter(
            filter_id="blur",
            version="2.1.0",
            summary="Gaussian blur.",
            accepts=ArraySpec(),
            emits=ArraySpec(),
            element=ElementRelation.PRESERVED,
            cost=COST,
            authoring_group=AuthoringGroup.SPATIAL_PREP,
            primary_params=("factor",),
            registry=registry,
        )
        class BlurParams(SampleParams):
            pass

        spec = registry.latest("blur")
        assert spec.params_model is BlurParams
        assert BlurParams.__filter_spec__ is spec
        assert registry.ids() == ("blur",)

    def test_decorator_derives_warmup_bound_from_the_params_model(self) -> None:
        registry = FilterRegistry()

        @register_filter(
            filter_id="settling",
            version="1.0.0",
            summary="Settles before it speaks.",
            accepts=ArraySpec(),
            emits=ArraySpec(),
            element=ElementRelation.PRESERVED,
            cost=COST,
            authoring_group=AuthoringGroup.SPATIAL_PREP,
            settling_epsilon=0.0,
            registry=registry,
        )
        class SettlingParams(ParamsBase):
            @classmethod
            def max_warmup_frames(cls) -> FrameCount:
                return FrameCount(7)

        assert SettlingParams.spec().warmup_frames == FrameCount(7)


def decorator_keywords() -> set[str]:
    """`register_filter`'s keywords, less `registry`, which is the decorator's own.

    `params_model` is the other name the two lists differ by, and it is absent
    here rather than removed: the decorated class supplies it, which is the one
    field of a spec that cannot be written in the decoration. `warmup_frames`
    is absent because the params model derives the spec bound.
    """
    parameters = inspect.signature(register_filter).parameters.values()
    return {p.name for p in parameters if p.kind is p.KEYWORD_ONLY} - {"registry"}


#: A registration with every optional keyword left at its default, so a probe
#: below can be the only thing that differs from it.
BASE: dict[str, Any] = {
    "filter_id": "blur",
    "version": "2.1.0",
    "summary": "Gaussian blur.",
    "accepts": ArraySpec(),
    "emits": ArraySpec(),
    "cost": COST,
    "element": ElementRelation.PRESERVED,
    "authoring_group": AuthoringGroup.SPATIAL_PREP,
}

#: One legal value per keyword, differing from both that parameter's default
#: and `BASE`'s value — so a keyword the decorator accepts and never forwards
#: leaves the spec holding the other one. Applied one at a time rather than all
#: at once, because several pairs are illegal together: `backend_agnostic`
#: requires `deterministic`, and both probes are the non-default.
PROBES: dict[str, Any] = {
    "filter_id": "probe",
    "version": "3.2.1",
    "summary": "Something else entirely.",
    "accepts": ArraySpec(dtypes=("float32",)),
    "emits": ArraySpec(channels=(ChannelSpec.GRAY,)),
    "cost": CostEstimate(work_per_megapixel=WorkUnits(2.0)),
    "authoring_group": AuthoringGroup.DETECTION,
    "authoring_order": 7,
    "mode": Mode.WINDOWED,
    "settling_epsilon": 0.25,
    "rate_changing": True,
    "selecting": True,
    "deterministic": False,
    "stateful": True,
    "backend_agnostic": True,
    "primary_params": ("factor",),
    "authoring_hidden_params": ("anti_alias",),
    "caption": (CaptionPart(label="factor", param="factor"),),
    "param_value_labels": {"anti_alias": {"True": "averaged"}},
    "element": ElementKind.BLOCK,
    "element_names": ElementNames("block", "blocks"),
}


class TestDecoratorMatchesSpec:
    """The decorator's keywords are `FilterSpec`'s fields, written out twice more.

    ARCHITECTURE §3 calls the duplication one field addition away from drifting
    silently, and the drift does not crash: a field added to the spec with a
    default is simply unreachable from the decorator, so every filter gets the
    default and nothing says so. Fixing it — building the spec from `**kwargs`,
    or generating the signature — would cost every keyword the static type a
    filter author is checked against at the one place they write it, so the
    copies stay and these two tests hold them in step.
    """

    def test_the_keywords_are_the_specs_field_list(self) -> None:
        # Set equality, not containment, and each direction catches a different
        # half: the spec growing a field the decorator never learned about, and
        # a keyword left behind after the field it filled was removed.
        assert decorator_keywords() == {f.name for f in fields(FilterSpec)} - {
            "params_model",
            "warmup_frames",
        }

    def test_every_keyword_reaches_the_field_it_names(self) -> None:
        # The third copy — `decorate`'s body — which the signature test cannot
        # see. A keyword accepted and then not forwarded to the `FilterSpec(...)`
        # call is the same silent default with the same absence of a symptom.
        assert set(PROBES) == decorator_keywords()

        class ProbeParams(SampleParams):
            pass

        class RateProbeParams(DecimateParams):
            pass

        class SelectProbeParams(SpanningParams):
            pass

        # The two probes that cannot ride on the shared params model: each names
        # a flag the spec refuses unless the decorated class overrides the
        # matching method, and refuses the override without.
        models = {"rate_changing": RateProbeParams, "selecting": SelectProbeParams}

        for name, probe in PROBES.items():
            registry = FilterRegistry()
            model = models.get(name, ProbeParams)
            values = {**BASE, name: probe}
            if name == "element":
                values["element_names"] = ElementNames("block", "blocks")
            elif name == "element_names":
                values["element"] = ElementKind.BLOCK
            decorated = register_filter(**values, registry=registry)(model)

            spec = decorated.__filter_spec__
            assert spec is not None
            assert getattr(spec, name) == probe
