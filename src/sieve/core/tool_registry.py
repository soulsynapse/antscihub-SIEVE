"""The shelf tools put themselves on: a container keyed by `(id, version)`.

Core defines the shelf; `sieve.tools` puts things on it, at import time,
through the decorator below. Nothing here enumerates tools and nothing here
imports one — a manifest listing them would be manual wiring that adding a tool
has to edit, and an import would invert the layer stack.

Both id *and* version are part of the key. A pipeline saved against 1.0.0 has
to keep reproducing 1.0.0's output after 1.1.0 ships, so the two coexist rather
than the newer one shadowing the older.

`offered_tools` is the one question asked *of* the shelf rather than about one
entry, and it lives here rather than in a module of its own because a new direct
child of `core` is a revision of `adr/core-membership-is-closed.md` and this is
not a decision an offer needs.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any, TypeVar

from sieve.core.tool_base import (
    CaptionPart,
    DisplaySurface,
    ElementDeclaration,
    ElementKind,
    ElementNames,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    StreamSpec,
    ToolDisplay,
    ToolRun,
    ToolSource,
    ToolSpec,
    WarmupKind,
    node_element,
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


def offered_tools(
    produced: StreamSpec,
    element: ElementKind | None,
    shelf: Iterable[ToolSpec],
) -> tuple[ToolSpec, ...]:
    """The shelf narrowed to what could plausibly go after `produced`.

    VISION's new-project scenario puts an add-tool box below the last step
    "holding what could go there", and its swap sibling asks the same of a
    position that already has a tool in it. Neither is the question
    `Dag._edge_faults` asks: that one is legality, false only on proven
    disjointness, and a shortlist computed from it would hold nearly every
    registered tool — which is a tool list, and the user already has one
    (`todo/the-offering-predicate-is-not-the-edge-legality-check.md`).

    **Derived, never declared.** No tool carries a plausibility field and
    nothing here reads a `tool_id`. The offer is computed from what the
    position resolved to — the stream flowing in, and the element meaning
    `Dag.elements` folded forward to it — against declarations tools already
    carry for other reasons, so a tool arrives offerable without having said
    anything about offers. That is `adr/gui-knows-kinds-not-tools.md`'s
    asymmetry one layer down, and this is the layer: `gui` renders the
    shortlist it is handed (`gui-computes-nothing`).

    Two refusals, both about the position rather than about the tool.
    `StreamSpec.matches` is the first. The second is the element meaning — a
    tool that aggregates is implausible over blocks, because a mean of blocks
    is a quantity no count threshold is denominated in, and `node_element`
    already says so by resolving to `None`. A tool declaring no element meaning
    at all emits a table and is exempt: it has nothing to lose. So is every
    tool at a position whose own element meaning is `None` — the noun was lost
    upstream and never recovers, so there is none left here for a tool to lose,
    and the leg that exists to protect it has no subject.

    The source site is not here. Offering against a folder of picked files
    needs their count and extension class, which arrive with
    `todo/the-first-source-tool-moves-the-three-single-root-assumptions.md`;
    the add-tool and swap sites have their facts already.

    Args:
        produced: What flows into the position — the upstream node's `emits`,
            or a source's.
        element: What one value of that stream is a value of. `None` where the
            walk lost it or the stream is a table, and a `None` refuses
            nothing: a position whose elements have no meaning is one where
            this leg has no opinion, not one where every tool is implausible.
        shelf: The specs to consider. Passed rather than taken from `REGISTRY`
            because which shelf — the process-wide one, one version per tool, a
            scratch one in a test — is not a question the predicate has an
            opinion about.

    Returns:
        The plausible specs, tightest `match_slack` first and ties broken by
        id, so the display is a function of the declarations and not of
        registration order. Empty is a real answer and the common one where the
        position produced a wildcard: nothing was proven, so nothing is
        offered.
    """
    scored: list[tuple[int, str, ToolSpec]] = []
    for spec in shelf:
        slack = spec.accepts.match_slack(produced)
        if slack is None:
            continue
        if (
            element is not None
            and spec.element is not None
            and node_element(spec.element, element) is None
        ):
            continue
        scored.append((slack, spec.tool_id, spec))
    return tuple(spec for _, _, spec in sorted(scored, key=lambda row: row[:2]))


def register_tool(
    *,
    tool_id: str,
    version: str,
    summary: str,
    accepts: StreamSpec,
    emits: StreamSpec,
    emissions: tuple[Emission, ...],
    run: ToolRun[Any, Any] | None = None,
    source: ToolSource[Any] | None = None,
    mode: Mode = Mode.STREAMING,
    settling_epsilon: float | None = None,
    warmup_kind: WarmupKind | None = None,
    rate_changing: bool = False,
    selecting: bool = False,
    deterministic: bool = True,
    stateful: bool = False,
    state_factory: Callable[[], Any] | None = None,
    guidance: str = "",
    primary_params: tuple[str, ...] = (),
    caption: tuple[CaptionPart, ...] = (),
    param_value_labels: Mapping[str, Mapping[str, str]] | None = None,
    param_stereotypes: Mapping[str, ParamStereotype] | None = None,
    param_surfaces: Mapping[str, DisplaySurface] | None = None,
    display: ToolDisplay[Any] | None = None,
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
            source=source,
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
            guidance=guidance,
            primary_params=primary_params,
            caption=caption,
            param_value_labels={} if param_value_labels is None else param_value_labels,
            param_stereotypes={} if param_stereotypes is None else param_stereotypes,
            param_surfaces={} if param_surfaces is None else param_surfaces,
            display=display,
            element=element,
            element_names=element_names,
        )
        (registry if registry is not None else REGISTRY).register(spec)
        params_model.__tool_spec__ = spec
        return params_model

    return decorate
