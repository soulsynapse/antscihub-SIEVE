"""`sieve inspect` — what is on the shelf, read off the declarations.

**It prints declarations, never measurements.** Everything here is on `ToolSpec`
or on the params model, so the command runs on a machine with no codec and no
footage — the property `core/tool_base.py` split itself in half to preserve, and
this is the caller in a position to demonstrate it.

Two of the declarations it prints have no other reader on the tree. A tool's
window is two-sided (`lookahead_frames`) and each of its parameters says how it
is populated (`param_stereotypes`); the consumers of both are Phase 7's — an
emission checkbox, a widget generator — and a field whose only reader is two
phases out is the shape `adr/declared-means-verified.md` refuses. Printing them
is what makes them falsifiable now. A declaration nobody can read is a
declaration nobody can catch lying.

What v2's `inspect_cmd` printed and this does not: the kernel table, dropped
with the apparatus behind it (`adr/no-kernel-apparatus.md`); the cost estimate
and `backend_agnostic`, which fed machinery v3 has not built; and the guidance
markdown, which has no referent — guidance is a spec field arriving in Phase 7
(`docs/todo/per-tool-documents-are-decided-or-dropped.md`), so what `inspect`
will print then is a declaration and what it prints now is nothing.

**The argument narrows the shelf; it does not resolve a version.** v2 took a
`--version` option because naming a tool there collapsed to one spec and
something had to choose. Here a named id prints every registered version of it,
which is the listing narrowed rather than a second question to answer — the
registry is keyed by the pair, and two versions of a tool are two different
things a project can name.

The shelf comes from `discover()`, so a tool that lands tomorrow is listed
without an edit here — the same property `sieve.tools` exists to have.
"""

from __future__ import annotations

from typing import Annotated

import typer

from sieve.core.tool_base import ArraySpec, ParamsBase, StreamSpec, ToolSpec, resolved_schema
from sieve.pipeline.cache_key import is_cacheable
from sieve.tools import discover


def inspect_tools(
    tool_id: Annotated[
        str | None,
        typer.Argument(help="A tool to describe. Omitted, every tool is described."),
    ] = None,
) -> None:
    """Print what each registered tool declares.

    Raises:
        typer.Exit: code 1 if `tool_id` names nothing registered. The message
            lists the shelf, because a wrong id here is a typo far more often
            than it is a missing install and the fix is then on screen.
    """
    specs = discover()
    if tool_id is not None:
        named = tuple(spec for spec in specs if spec.tool_id == tool_id)
        if not named:
            typer.echo(f"no tool {tool_id} at any version", err=True)
            typer.echo(f"on the shelf: {', '.join(sorted({s.tool_id for s in specs}))}", err=True)
            raise typer.Exit(1)
        specs = named
    typer.echo("\n\n".join(_describe(spec) for spec in specs))


def _describe(spec: ToolSpec) -> str:
    """Everything `spec` declares, as text.

    A function returning a string rather than a sequence of `echo` calls so a
    test can assert against a whole block at once, and so the ordering is
    visible in one place: identity, then what it does to a stream, then what the
    executor and the cache key need from it, then parameters.
    """
    lines = [
        *_headline(spec),
        "",
        f"accepts           {_stream(spec.accepts)}",
        f"emits             {_stream(spec.emits)}",
        f"element           {_element(spec)}",
        f"mode              {spec.mode}",
        f"warmup_frames     {_window(spec)}",
        f"lookahead_frames  {_window(spec, lookahead=True)}",
        f"settling_epsilon  {_settling_epsilon(spec)}",
        f"rate_changing     {spec.rate_changing}",
        f"selecting         {spec.selecting}",
        f"stateful          {spec.stateful}",
        f"deterministic     {spec.deterministic} (cacheable: {is_cacheable(spec)})",
        "",
        "parameters",
        *_parameters(spec),
    ]
    return "\n".join(lines)


def _headline(spec: ToolSpec) -> list[str]:
    """Who the tool is and what it can be asked to keep.

    The selecting parameter is named beside the emission list because without it
    the four signals of a `block_signal` read as four things one node produces at
    once, which is the opposite of what the declaration says: they are what it
    can be configured to produce, one per run.
    """
    selector = spec.emissions[0].selected_by
    chooses = f" ({selector})" if selector is not None else ""
    return [
        f"{spec.tool_id} {spec.version}",
        f"  {spec.summary}",
        f"  can emit{chooses}: {', '.join(spec.emission_names)}",
    ]


def _stream(stream: StreamSpec) -> str:
    """One side of the edge contract, without the dataclass repr.

    An empty tuple is a wildcard on both fields, and `dtypes=()` reads as a tool
    that accepts nothing rather than one that accepts anything — the inversion is
    worth a word to close, since it is the declaration a reader consults to find
    out whether two tools can be wired together.
    """
    if not isinstance(stream, ArraySpec):
        return f"rows: {', '.join(stream.columns) or 'any columns'}"
    dtypes = ", ".join(stream.dtypes) or "any dtype"
    channels = ", ".join(str(channel) for channel in stream.channels) or "any channel layout"
    return f"frames: {dtypes} / {channels}"


def _element(spec: ToolSpec) -> str:
    """What one emitted value is a value of, and the noun a count over it uses.

    A relation declaration has no noun of its own — it preserves or loses the one
    upstream — so saying where the noun comes from is the whole content of the
    line for the tools that declare one.
    """
    if spec.element is None:
        return "none (this tool emits rows)"
    if spec.element_names is None:
        return f"{spec.element} (names come from upstream)"
    return f"{spec.element} ({spec.element_names.singular}/{spec.element_names.plural})"


def _window(spec: ToolSpec, *, lookahead: bool = False) -> str:
    """One side of the window, and whether the number is a bound or a cost.

    The side is named on every tool including the ones declaring zero, because
    the shape of the contract is what a reader is here to learn: v2 could state
    only the lead-in, and the missing half is what kept a tool tuned against a
    centred result out of the graph at all (`adr/detector-is-a-node.md`).

    `temporal_baseline` is why the note exists. It declares 7199 — a 30 s window
    at 240 fps — and charges a default configuration 149. Printed bare the bound
    reads as the lead-in every run decodes, which would make the tool look
    unusable to exactly the reader who came here to find out whether it is.
    """
    count = spec.lookahead_frames if lookahead else spec.warmup_frames
    side = "after" if lookahead else "before"
    declared = spec.params_model.lookahead_frames if lookahead else spec.params_model.warmup_frames
    base = ParamsBase.lookahead_frames if lookahead else ParamsBase.warmup_frames
    note = "" if declared is base else "  (worst case; each configuration is charged its own)"
    return f"{count.frames} {side} the target{note}"


def _settling_epsilon(spec: ToolSpec) -> str:
    """Render the epsilon field without making absence look numeric."""
    return "none" if spec.settling_epsilon is None else f"{spec.settling_epsilon:g}"


#: JSON Schema keywords worth showing beside a parameter. A bound is the
#: difference between "factor is an integer" and "factor is an integer between 2
#: and 64", and the second is the one that stops a user submitting a value the
#: model will reject. An explicit list rather than every keyword because `title`
#: and `type` are already rendered and `default` is rendered differently.
_CONSTRAINT_KEYS = (
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    # How many components a composite value has, which is the whole of what a
    # pair-shaped parameter bounds. They sit behind `resolved_schema`'s walk —
    # a scalar field never carries one, so the two arrived with the first
    # reader that could see past an `anyOf`.
    "minItems",
    "maxItems",
    "pattern",
    "enum",
)


def _parameters(spec: ToolSpec) -> list[str]:
    """One line per field of the params model, primaries marked with `*`.

    The population kind leads each line, ahead of the JSON Schema half. It is the
    answer to "how does a user set this", which is the question someone reading a
    parameter list is asking, and it is the declaration on this line that nothing
    else on the tree reads.

    The rest is read out of the model's own JSON Schema rather than out of
    `model_fields`, because the constraints are the half a user most needs and
    pydantic stores them as `annotated_types` objects whose reprs this module
    would have to learn to unpack. The schema is the model's canonical
    self-description, it is what the widget generator builds widgets from, and
    using it here means the terminal and that panel read one thing — including
    the walk into `$ref` and `anyOf` that a composite parameter's shape and
    bounds sit behind, which is `resolved_schema`'s and not this module's.

    `primary_params` is a marker rather than a separate section: the GUI's
    "before Advanced" split is a decision made for a panel with limited height,
    and a terminal has no reason to inherit it.

    v2's version also printed each field's schema `description`. No params model
    here carries one — v3 documents a field in the `#:` comment above it, which
    pydantic never sees — so that is a branch with no subject, and it returns
    with the guidance field that gives a tool prose in the first place.
    """
    schema = resolved_schema(spec.params_model)
    properties: dict[str, dict[str, object]] = schema.get("properties", {})
    if not properties:
        return ["  (none)"]
    required: set[str] = set(schema.get("required", ()))
    width = max(len(name) for name in properties)
    kind_width = max(len(str(kind)) for kind in spec.param_stereotypes.values())
    lines: list[str] = []
    for name, described in properties.items():
        marker = "*" if name in spec.primary_params else " "
        kind = str(spec.param_stereotypes[name])
        parts = [str(described.get("type", "any"))]
        parts.append("required" if name in required else f"default {described.get('default')!r}")
        parts.extend(f"{key}={described[key]!r}" for key in _CONSTRAINT_KEYS if key in described)
        lines.append(f" {marker}{name:<{width}}  {kind:<{kind_width}}  {'  '.join(parts)}")
    return lines
