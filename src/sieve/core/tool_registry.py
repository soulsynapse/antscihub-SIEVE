"""The shelf tools put themselves on: a container keyed by `(id, version)`.

Core defines the shelf; `sieve.tools` puts things on it, at import time,
through the decorator below. Nothing here enumerates tools and nothing here
imports one — a manifest listing them would be manual wiring that adding a tool
has to edit, and an import would invert the layer stack.

Both id *and* version are part of the key. A pipeline saved against 1.0.0 has
to keep reproducing 1.0.0's output after 1.1.0 ships, so the two coexist rather
than the newer one shadowing the older.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from typing import Any, TypeVar

from sieve.core.tool_base import (
    CaptionPart,
    ElementDeclaration,
    ElementNames,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    StreamSpec,
    ToolRun,
    ToolSpec,
    WarmupKind,
)

#: The decorator returns the class it was given, not `ParamsBase` — erasing the
#: subclass would cost every tool's own fields their static types at the one
#: place they are guaranteed to be read.
ParamsT = TypeVar("ParamsT", bound=ParamsBase)


class UnknownToolError(LookupError):
    """No tool is registered under the requested id or version."""


class DuplicateToolError(LookupError):
    """Two tools claim the same `(tool_id, version)`."""


class ToolRegistry:
    """Lookup over registered specs. Holds no kernels and executes nothing."""

    def __init__(self) -> None:
        self._specs: dict[tuple[str, str], ToolSpec] = {}

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[ToolSpec]:
        return iter(self._specs.values())

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self._specs

    def register(self, spec: ToolSpec) -> ToolSpec:
        """Add `spec`, returning it so a caller can bind the result.

        A repeated key always raises, even for an identical spec. The failure
        it catches is a tool module copy-pasted without changing its id, and
        the cost of that going unnoticed is two different kernels sharing cache
        entries — expensive enough to outweigh the inconvenience of a module
        that cannot be re-imported without clearing the registry first.

        Raises:
            DuplicateToolError: if this `(tool_id, version)` is taken.
        """
        if spec.key in self._specs:
            raise DuplicateToolError(f"{spec.tool_id} {spec.version} is already registered")
        self._specs[spec.key] = spec
        return spec

    def get(self, tool_id: str, version: str) -> ToolSpec:
        """The spec registered under exactly this id and version.

        Raises:
            UnknownToolError: if nothing is registered under the pair.
        """
        try:
            return self._specs[tool_id, version]
        except KeyError:
            raise UnknownToolError(f"no tool {tool_id} at version {version}") from None

    def latest(self, tool_id: str) -> ToolSpec:
        """The highest-versioned spec for `tool_id`.

        Ordered by `version_tuple`, not by the version string: `1.10.0` is
        newer than `1.9.0` and sorts below it as text.

        Raises:
            UnknownToolError: if no version of `tool_id` is registered.
        """
        candidates = [spec for spec in self._specs.values() if spec.tool_id == tool_id]
        if not candidates:
            raise UnknownToolError(f"no tool {tool_id} at any version")
        return max(candidates, key=lambda spec: spec.version_tuple)

    def versions(self, tool_id: str) -> tuple[str, ...]:
        """Registered versions of `tool_id`, oldest first. Empty if unknown."""
        candidates = sorted(
            (spec for spec in self._specs.values() if spec.tool_id == tool_id),
            key=lambda spec: spec.version_tuple,
        )
        return tuple(spec.version for spec in candidates)

    def ids(self) -> tuple[str, ...]:
        """Every registered tool id, sorted, each appearing once."""
        return tuple(sorted({spec.tool_id for spec in self._specs.values()}))

    def clear(self) -> None:
        """Drop every registration. For tests; production registers once."""
        self._specs.clear()


#: The process-wide shelf. `sieve.tools` modules populate it on import.
REGISTRY = ToolRegistry()


def register_tool(
    *,
    tool_id: str,
    version: str,
    summary: str,
    accepts: StreamSpec,
    emits: StreamSpec,
    emissions: tuple[Emission, ...],
    run: ToolRun[Any, Any] | None = None,
    mode: Mode = Mode.STREAMING,
    settling_epsilon: float | None = None,
    warmup_kind: WarmupKind | None = None,
    rate_changing: bool = False,
    selecting: bool = False,
    deterministic: bool = True,
    stateful: bool = False,
    state_factory: Callable[[], Any] | None = None,
    primary_params: tuple[str, ...] = (),
    caption: tuple[CaptionPart, ...] = (),
    param_value_labels: Mapping[str, Mapping[str, str]] | None = None,
    param_stereotypes: Mapping[str, ParamStereotype] | None = None,
    element: ElementDeclaration | None = None,
    element_names: ElementNames | None = None,
    registry: ToolRegistry | None = None,
) -> Callable[[type[ParamsT]], type[ParamsT]]:
    """Decorate a `ParamsBase` subclass to build and register its spec.

    The decorated class *is* the tool's parameter model, so the one thing a
    `ToolSpec` cannot be written without is supplied by the decoration rather
    than repeated in it. The built spec is bound to the class as
    `__tool_spec__`, which is how a tool module reaches its own declaration
    without a second lookup.

    `run` is a keyword rather than a second decorator, which puts one ordering
    constraint on a tool module: the function is written above the params class
    that decorates itself with it. Its own annotations may still name that class,
    since `from __future__ import annotations` leaves them unevaluated.

    `registry` exists so a test can register into a scratch registry instead of
    the process-wide one. Tool modules omit it.
    """

    def decorate(params_model: type[ParamsT]) -> type[ParamsT]:
        spec = ToolSpec(
            tool_id=tool_id,
            version=version,
            summary=summary,
            params_model=params_model,
            accepts=accepts,
            emits=emits,
            emissions=emissions,
            run=run,
            mode=mode,
            warmup_frames=params_model.max_warmup_frames(),
            lookahead_frames=params_model.max_lookahead_frames(),
            settling_epsilon=settling_epsilon,
            warmup_kind=warmup_kind,
            rate_changing=rate_changing,
            selecting=selecting,
            deterministic=deterministic,
            stateful=stateful,
            state_factory=state_factory,
            primary_params=primary_params,
            caption=caption,
            param_value_labels={} if param_value_labels is None else param_value_labels,
            param_stereotypes={} if param_stereotypes is None else param_stereotypes,
            element=element,
            element_names=element_names,
        )
        (registry if registry is not None else REGISTRY).register(spec)
        params_model.__tool_spec__ = spec
        return params_model

    return decorate
