







from __future__ import annotations

from fractions import Fraction

import pytest

from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    ElementKind,
    ElementRelation,
    FilterSpec,
    Mode,
    ParamsBase,
    TableSpec,
    input_warmup_frames,
    node_element,
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


    factor: int = 2
    anti_alias: bool = True


class DecimateParams(ParamsBase):


    stride: int = 10

    def output_rate(self) -> Fraction:
        return Fraction(1, self.stride)


class InterpolateParams(ParamsBase):







    numerator: int = 3
    denominator: int = 2

    def output_rate(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)


class DownsampleParams(ParamsBase):


    factor: int = 2

    def frame_bytes_ratio(self) -> float:
        return 1.0 / (self.factor**2)


class WindowParams(ParamsBase):







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
        "element": ElementRelation.PRESERVED,
        "cost": COST,
    }
    fields.update(overrides)
    return FilterSpec(**fields)





DECIMATOR = make_spec(filter_id="decimate", params_model=DecimateParams, rate_changing=True)
DOWNSAMPLER = make_spec(filter_id="downsample", params_model=DownsampleParams)
IIR = make_spec(filter_id="iir", warmup_frames=5)
INTERPOLATOR = make_spec(
    filter_id="interpolate", params_model=InterpolateParams, rate_changing=True
)

WINDOWED = make_spec(filter_id="window", params_model=WindowParams, warmup_frames=99)


class TestFilterSpec:
    def test_backend_agnostic_requires_deterministic(self) -> None:




        with pytest.raises(ValueError, match="backend_agnostic requires deterministic"):
            make_spec(backend_agnostic=True, deterministic=False)

    def test_primary_params_must_name_real_fields(self) -> None:

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




        path = [(DECIMATOR, DecimateParams()), (IIR, SampleParams())]

        assert source_warmup_frames(path) == 50
        assert sum(spec.warmup_frames for spec, _ in path) == 5

    def test_rate_is_read_from_params_not_from_the_spec(self) -> None:


        by_three = source_warmup_frames(
            [(DECIMATOR, DecimateParams(stride=3)), (IIR, SampleParams())]
        )
        assert by_three == 15

    def test_a_partial_input_frame_rounds_up(self) -> None:






        assert input_warmup_frames((INTERPOLATOR, InterpolateParams()), 5) == 4
        assert input_warmup_frames((INTERPOLATOR, InterpolateParams()), 6) == 4

    def test_a_configured_warmup_is_charged_instead_of_the_bound(self) -> None:







        short = [(DECIMATOR, DecimateParams()), (WINDOWED, WindowParams(length=31))]
        long_window = [(DECIMATOR, DecimateParams()), (WINDOWED, WindowParams(length=91))]

        assert source_warmup_frames(short) == 300
        assert source_warmup_frames(long_window) == 900

        assert WINDOWED.warmup_frames == 99

    def test_a_refinement_above_the_bound_is_refused(self) -> None:




        with pytest.raises(ValueError, match="exceeds the spec's declared bound"):
            input_warmup_frames((WINDOWED, WindowParams(length=101)), 0)


        assert input_warmup_frames((WINDOWED, WindowParams(length=100)), 0) == 99

    def test_undeclared_rate_change_is_refused_at_registration(self) -> None:



        with pytest.raises(ValueError, match="overrides output_rate"):
            make_spec(params_model=DecimateParams)
        with pytest.raises(ValueError, match="does not override output_rate"):
            make_spec(rate_changing=True)


class TestElementMeaning:
    def test_an_array_emitter_without_an_element_is_refused_at_registration(self) -> None:






        with pytest.raises(ValueError, match="declares no element meaning"):
            make_spec(element=None)

    def test_a_table_emitter_declaring_one_is_refused(self) -> None:



        with pytest.raises(ValueError, match="a table has columns, not elements"):
            make_spec(emits=TableSpec(columns=("x",)), element=ElementKind.BLOCK)

    def test_aggregation_keeps_pixels_and_refuses_blocks(self) -> None:




        assert node_element(ElementRelation.AGGREGATED, ElementKind.PIXEL) is ElementKind.PIXEL
        assert node_element(ElementRelation.AGGREGATED, ElementKind.BLOCK) is None

    def test_an_undeclarable_element_never_recovers_downstream(self) -> None:



        assert node_element(ElementRelation.PRESERVED, None) is None

    def test_a_kind_overrides_whatever_arrived(self) -> None:
        assert node_element(ElementKind.BLOCK, ElementKind.PIXEL) is ElementKind.BLOCK


class TestStoredBytes:
    def test_stored_size_multiplies_rate_by_frame_size(self) -> None:




        chained = DECIMATOR.stored_bytes_ratio(DecimateParams()) * DOWNSAMPLER.stored_bytes_ratio(
            DownsampleParams()
        )
        assert chained == pytest.approx(1 / 40)


        assert DOWNSAMPLER.cost.peak_bytes_per_input_byte == 2.0


class TestArraySpec:
    def test_disjoint_channel_sets_do_not_chain(self) -> None:
        gray_only = ArraySpec(channels=(ChannelSpec.GRAY,))
        rgb_only = ArraySpec(channels=(ChannelSpec.RGB,))
        assert not gray_only.admits(rgb_only)

    def test_wildcard_admits_anything(self) -> None:


        assert ArraySpec().admits(ArraySpec(dtypes=("float32",), channels=(ChannelSpec.RGB,)))
        assert ArraySpec(dtypes=("uint8",)).admits(ArraySpec(channels=(ChannelSpec.GRAY,)))

    def test_overlap_is_enough(self) -> None:
        accepts = ArraySpec(dtypes=("uint8", "float32"))
        assert accepts.admits(ArraySpec(dtypes=("float32", "float64")))


class TestStreamKind:
    def test_rows_and_frames_never_chain_in_either_direction(self) -> None:



        assert not ArraySpec().admits(TableSpec())
        assert not TableSpec().admits(ArraySpec())

    def test_missing_columns_are_rejected_where_missing_dtypes_are_not(self) -> None:



        assert TableSpec(columns=("x", "y")).admits(TableSpec(columns=("frame", "x", "y")))
        assert not TableSpec(columns=("x", "y")).admits(TableSpec(columns=("frame", "x")))
        assert TableSpec(columns=("x", "y")).admits(TableSpec())


class TestParamsBase:
    def test_unknown_parameter_is_rejected(self) -> None:


        with pytest.raises(ValueError, match="anti_aliasing"):
            SampleParams(anti_aliasing=False)

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
            primary_params=("factor",),
            registry=registry,
        )
        class BlurParams(SampleParams):
            pass

        spec = registry.latest("blur")
        assert spec.params_model is BlurParams
        assert BlurParams.__filter_spec__ is spec
        assert registry.ids() == ("blur",)
