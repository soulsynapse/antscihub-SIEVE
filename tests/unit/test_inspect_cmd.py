"""What `sieve inspect` prints once the constraint walk is under it.

`test_cli_inspect.py` holds the command's own claims — every tool listed, every
declaration printed as its own. This file holds the half that is not the
command's: `core.tool_base.resolved_schema` is where a parameter's shape and
bounds are found, the widget generator reads the same function, and the terminal
is where a reader can check that it found them.

The subject is a *composite* parameter, because a scalar's constraints sit on
the property itself and printed correctly before the walk existed. A value that
is a whole rectangle or a whole pair does not: pydantic writes it as a `$ref` or
an `anyOf`, and a reader that stops at the property prints `any` — for exactly
the parameters whose legal range a user is least able to guess.
"""

from __future__ import annotations

from pydantic import Field
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.tool_base import ParamsBase, ParamStereotype, resolved_schema
from sieve.tools import discover

runner = CliRunner()

#: The kinds that are one field per whole value, so their constraints are the
#: ones behind the walk (`adr/one-field-is-one-populated-value.md`).
_COMPOSITE = frozenset(ParamStereotype) - {ParamStereotype.SCALAR_RANGE, ParamStereotype.ENUM}


def _param_line(tool_id: str, name: str) -> str:
    result = runner.invoke(app, ["inspect", tool_id])
    assert result.exit_code == 0, result.output
    _, header, listed = result.output.partition("\nparameters\n")
    assert header, f"no parameters section in {result.output!r}"
    matches = [
        line.strip()
        for line in listed.splitlines()
        if line.strip().lstrip("*").split(" ")[0] == name
    ]
    assert len(matches) == 1, f"expected one {name!r} line, got {matches}"
    return matches[0]


def test_a_composite_param_prints_its_bounds() -> None:
    """A pair prints that it is a pair of two, and no composite prints `any`.

    `detect.count_frac` is the hard one and the reason the walk goes through
    `anyOf` as well as `$ref`: an optional band is two levels of indirection
    from its own `minItems`, and it is the parameter on the shelf a user is
    least able to guess at — an optional threshold whose absence and whose
    bounds are different questions.

    The second assertion is over the shelf rather than over the three
    parameters named here, so a tool landing tomorrow with a composite
    parameter cannot quietly reintroduce the `any` this closes.
    """
    assert "minItems=2" in _param_line("detect", "count_frac")
    assert "maxItems=2" in _param_line("detect", "count_frac")

    for spec in discover():
        for name, kind in spec.param_stereotypes.items():
            if kind in _COMPOSITE:
                assert " any " not in f" {_param_line(spec.tool_id, name)} "


def test_a_composite_param_prints_the_shape_its_annotation_has() -> None:
    """`crop.region` is a rectangle and `span.frames` is a pair, and they print
    as different things — which is the whole of what a reader gets from a walk
    into a `$ref` whose target declares no bounds of its own."""
    assert "object" in _param_line("crop", "region")
    assert "array" in _param_line("span", "frames")


def test_a_union_the_walk_cannot_reduce_is_left_as_it_stands() -> None:
    """Two real branches are two answers, and the walk declines to pick one.

    No tool on the shelf declares one — every optional is a branch and `null` —
    so this is written against a model built here. A resolver that took the
    first branch would print bounds the value is not held to whenever it was
    populated as the other.
    """

    class EitherParams(ParamsBase):
        either: int | str = Field(default=0)

    described = resolved_schema(EitherParams)["properties"]["either"]

    assert "anyOf" in described
    assert "type" not in described
