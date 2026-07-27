"""The filter contract: what a spec refuses to claim, and what the shelf holds.

Each test here stands in for a way the contract stops being load-bearing: a
spec that promises more than it can, a params model that swallows a typo, a
cache-key input that is not byte-stable, or a registry that hands back the
wrong version of a filter an old pipeline named.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    FilterSpec,
    Mode,
    ParamsBase,
    TableSpec,
    input_warmup_frames,
    source_warmup_frames,
)
from sieve.core.filter_registry import (
    DuplicateFilterError,
    FilterRegistry,
    UnknownFilterError,
    register_filter,
)
from sieve.core.types import ChannelSpec

COST = CostEstimate(seconds_per_megapixel=0.001)


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

    def warmup_frames(self) -> int:
        return self.length - 1


def make_spec(**overrides: object) -> FilterSpec:
    fields: dict[str, object] = {
        "filter_id": "downsample",
        "version": "1.0.0",
        "summary": "Reduce spatial resolution by an integer factor.",
        "params_model": SampleParams,
        "accepts": ArraySpec(),
        "emits": ArraySpec(),
        "cost": COST,
    }
    fields.update(overrides)
    return FilterSpec(**fields)  # pyright: ignore[reportArgumentType]


#: The three specs the rate and storage tests chain. Built once at module scope
#: because constructing them is what several tests do *before* the thing they
#: are about, not part of it.
DECIMATOR = make_spec(filter_id="decimate", params_model=DecimateParams, rate_changing=True)
DOWNSAMPLER = make_spec(filter_id="downsample", params_model=DownsampleParams)
IIR = make_spec(filter_id="iir", warmup_frames=5)
INTERPOLATOR = make_spec(
    filter_id="interpolate", params_model=InterpolateParams, rate_changing=True
)
#: Declares a bound of 99 and refines it per configuration.
WINDOWED = make_spec(filter_id="window", params_model=WindowParams, warmup_frames=99)


class TestFilterSpec:
    def test_backend_agnostic_requires_deterministic(self) -> None:
        # The incoherent pair: a filter that cannot reproduce its own output
        # cannot agree bit for bit with another backend's. Allowed through, it
        # would drop backend identity from the cache key of the one kind of
        # filter whose output nothing can reproduce.
        with pytest.raises(ValueError, match="backend_agnostic requires deterministic"):
            make_spec(backend_agnostic=True, deterministic=False)

    def test_primary_params_must_name_real_fields(self) -> None:
        # A renamed parameter otherwise leaves the GUI silently short a widget.
        with pytest.raises(ValueError, match=r"no such field.*scale_factor"):
            make_spec(primary_params=("scale_factor",))

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


class TestRate:
    def test_warmup_behind_a_decimator_is_counted_in_source_frames(self) -> None:
        # The whole reason rate is declared. Five frames of warmup downstream
        # of a 10:1 decimator is fifty source frames; ARCHITECTURE's plain sum
        # says fifteen, and the resulting preview renders an IIR that never
        # settled rather than failing in any visible way.
        path = [(DECIMATOR, DecimateParams()), (IIR, SampleParams())]

        assert source_warmup_frames(path) == 50
        assert sum(spec.warmup_frames for spec, _ in path) == 5  # what a sum would have said

    def test_rate_is_read_from_params_not_from_the_spec(self) -> None:
        # The factor is a parameter, so two nodes sharing one spec must be able
        # to disagree. A constant on the spec could not express this at all.
        by_three = source_warmup_frames(
            [(DECIMATOR, DecimateParams(stride=3)), (IIR, SampleParams())]
        )
        assert by_three == 15

    def test_a_partial_input_frame_rounds_up(self) -> None:
        # A rate of 3/2 means two input frames buy three output frames, so five
        # output frames want 3.33 inputs and therefore 4. Flooring gives 3, and
        # the node is one frame short of settled — which is why this is an
        # example rather than a property: every rate of the form 1/n divides
        # exactly, so a suite generated from decimators alone cannot tell the
        # two roundings apart no matter how many graphs it draws.
        assert input_warmup_frames((INTERPOLATOR, InterpolateParams()), 5) == 4
        assert input_warmup_frames((INTERPOLATOR, InterpolateParams()), 6) == 4

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

        assert source_warmup_frames(short) == 300
        assert source_warmup_frames(long_window) == 900
        # And the bound is what a spec-only reading would have charged both.
        assert WINDOWED.warmup_frames == 99

    def test_a_refinement_above_the_bound_is_refused(self) -> None:
        # The silent direction, and the only one worth an exception. A bound is
        # what `sieve inspect` prints and what a reader checks a filter's cost
        # against; a configuration quietly needing more lead-in than the
        # declaration admits renders a preview from a filter that never settled.
        with pytest.raises(ValueError, match="exceeds the spec's declared bound"):
            input_warmup_frames((WINDOWED, WindowParams(length=101)), 0)

        # The bound itself is legal — it is a bound, not a strict one.
        assert input_warmup_frames((WINDOWED, WindowParams(length=100)), 0) == 99

    def test_undeclared_rate_change_is_refused_at_registration(self) -> None:
        # Without this the gap reopens silently: a decimator whose spec forgot
        # `rate_changing` computes a correct rate that nothing is obliged to
        # consult, which is indistinguishable from having no rate at all.
        with pytest.raises(ValueError, match="overrides output_rate"):
            make_spec(params_model=DecimateParams)
        with pytest.raises(ValueError, match="does not override output_rate"):
            make_spec(rate_changing=True)


class TestStoredBytes:
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
            cost=COST,
            primary_params=("factor",),
            registry=registry,
        )
        class BlurParams(SampleParams):
            pass

        spec = registry.latest("blur")
        assert spec.params_model is BlurParams
        assert BlurParams.__filter_spec__ is spec
        assert registry.ids() == ("blur",)
