"""The filter contract: what a spec refuses to claim, and what the shelf holds.

Each test here stands in for a way the contract stops being load-bearing: a
spec that promises more than it can, a params model that swallows a typo, a
cache-key input that is not byte-stable, or a registry that hands back the
wrong version of a filter an old pipeline named.
"""

from __future__ import annotations

import pytest

from sieve.core.filter_base import (
    ArraySpec,
    CostEstimate,
    FilterSpec,
    Mode,
    ParamsBase,
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
