






















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







    specs = discover()
    if filter_id is None:
        if version is not None:
            typer.echo("--version qualifies a filter; name one.", err=True)
            raise typer.Exit(1)
        _list(specs)
        return
    typer.echo(_describe(_resolve(filter_id, version), guidance=guidance))


def _resolve(filter_id: str, version: str | None) -> FilterSpec:













    try:
        return REGISTRY.latest(filter_id) if version is None else REGISTRY.get(filter_id, version)
    except UnknownFilterError as error:
        typer.echo(str(error), err=True)
        installed = REGISTRY.versions(filter_id)
        if installed:
            typer.echo(f"installed versions of {filter_id}: {', '.join(installed)}", err=True)
        raise typer.Exit(1) from error


def _list(specs: tuple[FilterSpec, ...]) -> None:







    if not specs:



        typer.echo("no filters installed")
        return
    width = max(len(spec.filter_id) for spec in specs)
    for spec in specs:
        typer.echo(f"{spec.filter_id:<{width}}  {spec.version}  {spec.summary}")


def _warmup_note(spec: FilterSpec) -> str:







    if spec.params_model.warmup_frames is ParamsBase.warmup_frames:
        return ""
    return "  (worst case; each configuration is charged its own)"


def _describe(spec: FilterSpec, *, guidance: bool) -> str:







    lines = [
        f"{spec.filter_id} {spec.version}",
        f"  {spec.summary}",
        "",
        f"accepts           {spec.accepts}",
        f"emits             {spec.emits}",
        f"element           {spec.element}",
        f"mode              {spec.mode}",
        f"warmup_frames     {spec.warmup_frames}{_warmup_note(spec)}",
        f"rate_changing     {spec.rate_changing}",
        f"deterministic     {spec.deterministic} (cacheable: {spec.cacheable})",
        f"backend_agnostic  {spec.backend_agnostic}",
        f"cost              {spec.cost.seconds_per_megapixel} s/MP, "
        f"peak {spec.cost.peak_bytes_per_input_byte}x input bytes",
        f"backends          {', '.join(str(b) for b in KERNELS.backends_for(spec)) or 'none'}",
        "",
        "parameters",
    ]
    lines.extend(_parameters(spec))
    if guidance:
        lines.extend(("", *_guidance(spec)))
    return "\n".join(lines)








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







    try:
        path = guidance_path(spec)
    except LookupError as error:
        return [f"guidance: unavailable ({error})"]
    if not path.is_file():
        return [f"guidance: none at {path}"]
    return [f"guidance ({path}):", "", path.read_text(encoding="utf-8").rstrip()]
