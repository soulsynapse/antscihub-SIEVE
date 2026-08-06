"""`sieve inspect` — what filters this build has, and what one of them declares.

The first command deliberately, because it proves the two things every later
command assumes and neither of which any unit test can: that `discover()`
finds filters from an installed entry point rather than only from a test that
imported the module itself, and that the spec a filter registers is complete
enough to be read by something that was not written alongside it.

**It prints declarations, never measurements.** Everything here is on
`FilterSpec` or on the params model, so the command runs on a machine with no
codec, no CUDA, and no footage — which is the property `filter_base.py` split
itself in half to preserve, and this is the first caller in a position to
demonstrate it. The one line that touches a machine rather than a declaration
is `backends`, and it says *registered*, not runnable, for the same reason
`KernelRegistry.backends_for` does.

**Guidance is a path, not an embedded string.** Guardrail §3 makes the markdown
beside the filter the documentation, so this prints it from disk. A filter whose
guidance is missing prints its absence rather than failing: an out-of-tree
filter is allowed to have none, and it is the guardrail test's job — not a
user's — to insist that everything in `sieve.filters` does.
"""

from __future__ import annotations

from typing import Annotated

import typer

from sieve.backend.dispatch import KERNELS
from sieve.core.filter_base import FilterSpec, ParamsBase
from sieve.core.filter_registry import REGISTRY, UnknownFilterError
from sieve.filters import discover, guidance_path


def inspect_filters(
    filter_id: Annotated[
        str | None,
        typer.Argument(help="A filter to describe. Omitted, every filter is listed."),
    ] = None,
    version: Annotated[
        str | None,
        typer.Option("--version", "-v", help="Which version. Defaults to the newest installed."),
    ] = None,
    guidance: Annotated[
        bool,
        typer.Option("--guidance/--no-guidance", help="Print the filter's markdown guidance."),
    ] = True,
) -> None:
    """List the installed filters, or describe one of them.

    Raises:
        typer.Exit: code 1 if `filter_id` names nothing installed, or if
            `--version` is given without one — a version with no filter to
            qualify is a mistake with no reading under which it is correct.
    """
    specs = discover()
    if filter_id is None:
        if version is not None:
            typer.echo("--version qualifies a filter; name one.", err=True)
            raise typer.Exit(1)
        _list(specs)
        return
    typer.echo(_describe(_resolve(filter_id, version), guidance=guidance))


def _resolve(filter_id: str, version: str | None) -> FilterSpec:
    """The spec named, newest version when unqualified.

    `latest` rather than refusing to choose, because the overwhelmingly common
    question is "what does this filter take" and answering it with a list of
    versions to pick from would be a worse answer than the one this gives. The
    version is printed in the output, so an answer about the wrong one is
    visible rather than assumed.

    Raises:
        typer.Exit: code 1, with the message naming what is installed under
            that id when the id itself resolves — a wrong version is a typo far
            more often than it is a missing install, and the fix is on screen.
    """
    try:
        return REGISTRY.latest(filter_id) if version is None else REGISTRY.get(filter_id, version)
    except UnknownFilterError as error:
        typer.echo(str(error), err=True)
        installed = REGISTRY.versions(filter_id)
        if installed:
            typer.echo(f"installed versions of {filter_id}: {', '.join(installed)}", err=True)
        raise typer.Exit(1) from error


def _list(specs: tuple[FilterSpec, ...]) -> None:
    """One line per registered `(id, version)`, id and version column-aligned.

    Every version on its own line rather than one line per id with the versions
    collapsed: two versions of a filter are two different things a project can
    name — that is why the registry is keyed by the pair — and a listing that
    hid the distinction would be hiding the one it is most useful about.
    """
    if not specs:
        # Reachable: `sieve.filters` is scanned, so an install with the package
        # emptied has a registry and nothing on it. Saying so beats printing
        # nothing, which reads as a command that failed silently.
        typer.echo("no filters installed")
        return
    width = max(len(spec.filter_id) for spec in specs)
    for spec in specs:
        typer.echo(f"{spec.filter_id:<{width}}  {spec.version}  {spec.summary}")


def _warmup_note(spec: FilterSpec) -> str:
    """Say when the number above is a bound rather than what a run pays.

    `temporal_baseline` declares 7199 — a 30 s window at 240 fps — and charges a
    default configuration 149. Printed bare, the bound reads as the lead-in every
    run decodes, which would make the filter look unusable to exactly the reader
    who came here to find out whether it is.
    """
    if spec.params_model.warmup_frames is ParamsBase.warmup_frames:
        return ""
    return "  (worst case; each configuration is charged its own)"


def _describe(spec: FilterSpec, *, guidance: bool) -> str:
    """Everything `spec` declares, as text.

    A function returning a string rather than a sequence of `echo` calls so the
    test can assert against the whole block at once, and so the ordering is
    visible in one place: identity, then what it does to a stream, then what
    the executor and the cache key need from it, then parameters.
    """
    lines = [
        f"{spec.filter_id} {spec.version}",
        f"  {spec.summary}",
        "",
        f"accepts           {spec.accepts}",
        f"emits             {spec.emits}",
        f"element           {spec.element}",
        f"mode              {spec.mode}",
        f"warmup_frames     {spec.warmup_frames.frames}{_warmup_note(spec)}",
        f"rate_changing     {spec.rate_changing}",
        f"selecting         {spec.selecting}",
        f"deterministic     {spec.deterministic} (cacheable: {spec.cacheable})",
        f"backend_agnostic  {spec.backend_agnostic}",
        f"cost              {spec.cost.work_per_megapixel}/MP (uncalibrated)",
        f"work_anchor       {spec.cost.anchor}",
        f"peak_memory       {spec.cost.peak_bytes_per_input_byte}x input bytes",
        f"backends          {', '.join(str(b) for b in KERNELS.backends_for(spec)) or 'none'}",
        "",
        "parameters",
    ]
    lines.extend(_parameters(spec))
    if guidance:
        lines.extend(("", *_guidance(spec)))
    return "\n".join(lines)


#: JSON Schema keywords worth showing beside a parameter. A bound is the
#: difference between "factor is an integer" and "factor is an integer between
#: 2 and 64", and the second is the one that stops a user submitting a value
#: the model will reject. Kept as an explicit list rather than printing every
#: keyword because `title` and `type` are already rendered and `default` is
#: rendered differently.
_CONSTRAINT_KEYS = (
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "enum",
)


def _parameters(spec: FilterSpec) -> list[str]:
    """One line per field of the params model, primaries marked with `*`.

    Read out of the model's own JSON Schema rather than out of `model_fields`,
    because the constraints are the half a user most needs and pydantic stores
    them as `annotated_types` objects whose reprs this module would have to
    learn to unpack. The schema is the model's canonical self-description, it
    is what a GUI would build widgets from, and using it here means the terminal
    and a future dialog are reading one thing.

    `primary_params` is a marker rather than a separate section: the GUI's
    "before Advanced" split is a presentation decision made for a panel with
    limited height, and a terminal has no reason to inherit it.
    """
    schema = spec.params_model.model_json_schema()
    properties: dict[str, dict[str, object]] = schema.get("properties", {})
    if not properties:
        return ["  (none)"]
    required: set[str] = set(schema.get("required", ()))
    width = max(len(name) for name in properties)
    lines: list[str] = []
    for name, described in properties.items():
        marker = "*" if name in spec.primary_params else " "
        parts = [str(described.get("type", "any"))]
        parts.append("required" if name in required else f"default {described.get('default')!r}")
        parts.extend(f"{key}={described[key]!r}" for key in _CONSTRAINT_KEYS if key in described)
        description = str(described.get("description", "")).strip()
        if description:
            parts.append(description)
        lines.append(f" {marker}{name:<{width}}  {'  '.join(parts)}")
    return lines


def _guidance(spec: FilterSpec) -> list[str]:
    """The colocated markdown, or a line saying where it would be.

    Printed verbatim. Rendering it would mean choosing a renderer for a file
    whose whole purpose is to be read by a human who has already chosen a
    terminal, and the guardrail asks for markdown *because* it is legible
    unrendered.
    """
    try:
        path = guidance_path(spec)
    except LookupError as error:
        return [f"guidance: unavailable ({error})"]
    if not path.is_file():
        return [f"guidance: none at {path}"]
    return [f"guidance ({path}):", "", path.read_text(encoding="utf-8").rstrip()]
