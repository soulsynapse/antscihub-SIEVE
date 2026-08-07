"""`sieve inspect` — the declared shelf, printed.

Three of the declarations it prints have their real consumer in Phase 7 and no
reader before it: the emission list belongs to a save screen, the population kind
of a parameter to a widget generator, and the far side of a window to neither.
Printing them is what makes them falsifiable now
(`adr/declared-means-verified.md`): a declaration nobody can read is a
declaration nobody can catch lying. The tests below therefore check what a reader
of that output relies on — that every tool on the shelf is in it, and that what
each one prints is its own declaration rather than a shape this command invented.

The shelf is read through `discover()` rather than written out here, so a tool
landing tomorrow is covered without an edit, and a tool whose declarations change
cannot leave this file asserting the old ones.
"""

from __future__ import annotations

from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.cli.inspect_cmd import _describe
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    ParamsBase,
    ToolSpec,
)
from sieve.tools import discover

runner = CliRunner()


def _output() -> str:
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 0, result.output
    return result.output


def _block(tool_id: str) -> str:
    result = runner.invoke(app, ["inspect", tool_id])
    assert result.exit_code == 0, result.output
    return result.output


def _line(block: str, name: str) -> str:
    """The one declaration line of `block` whose first word is `name`.

    Asserting against a whole line rather than a substring of the block is what
    makes the window cases mean anything: `1972` appears twice in `detect`'s
    output, once per side, and a test that only asked whether it was present
    would pass with both sides printing the same number from the same field.

    Declaration lines are the unindented ones. The indentation is not decoration
    here — `normalize` has a parameter called `mode` and every spec has a field
    called `mode`, so the two halves of a block are told apart the way a reader
    tells them apart, by the column they start in.
    """
    return _one(name, [line for line in block.splitlines() if line[:1] not in (" ", "")])


def _param_line(block: str, name: str) -> str:
    """The one line of the parameters section describing the field `name`."""
    _, header, listed = block.partition("\nparameters\n")
    assert header, f"no parameters section in {block!r}"
    return _one(name, listed.splitlines())


def _one(name: str, lines: list[str]) -> str:
    matches = [line.strip() for line in lines if line.strip().lstrip("*").split(" ")[0] == name]
    assert len(matches) == 1, f"expected one {name!r} line, got {matches}"
    return matches[0]


def test_every_tool_on_the_shelf_prints_every_emission_it_declares() -> None:
    """Totality in both directions, which is the whole claim of the screen.

    A tool missing from the output is one whose outputs a user is never offered;
    a name in the output that no spec declares is the lie the field exists to
    make impossible.
    """
    output = _output()
    declared = {name for spec in discover() for name in spec.emission_names}
    assert declared, "no tool declares an emission"

    for spec in discover():
        assert spec.tool_id in output
        for name in spec.emission_names:
            assert name in output


def test_a_multi_product_tool_prints_all_four_of_its_emissions() -> None:
    """`block_signal` is why the field is a list and not the tool's own name.

    Four different measurements of one structure tensor, one of which leaves the
    node per configuration — so a save screen showing what a *run* emitted would
    show one, and the screen VISION describes shows all four.
    """
    output = _output()
    assert "change_energy, flow_speed, coherence, flow_agreement" in output
    assert "signal" in output


def test_a_single_product_tool_prints_the_one_thing_it_emits() -> None:
    """`detect` computes band power, an in-band count and a windowed mean, and
    emits none of them: the gate is what leaves the node, and the difference
    between what a tool computes and what it can emit is what the list records."""
    output = _output()
    detect = next(spec for spec in discover() if spec.tool_id == "detect")
    assert detect.emission_names == ("gate",)
    assert "gate" in output


def test_each_side_of_a_window_prints_the_number_its_own_field_declares() -> None:
    """The two-sided window, which is the declaration with no other reader.

    v2's contract could state only the lead-in, and the missing half is what kept
    a tool tuned against a centred result out of the graph at all
    (`adr/detector-is-a-node.md`). A reader asking what a window costs is asking
    two questions — how much decode, how much latency — so both numbers are
    matched to their own line rather than to the block.
    """
    lookahead = {spec.tool_id: spec.lookahead_frames.frames for spec in discover()}
    assert any(lookahead.values()), (
        "no tool declares a lookahead, so this case cannot tell the two sides apart"
    )

    for spec in discover():
        block = _block(spec.tool_id)
        assert f"{spec.warmup_frames.frames} before the target" in _line(block, "warmup_frames")
        assert f"{spec.lookahead_frames.frames} after the target" in _line(
            block, "lookahead_frames"
        )


def test_a_bound_a_configuration_can_refine_says_so_and_a_fixed_one_does_not() -> None:
    """`temporal_baseline` declares 7199 and charges a default run 149.

    Printed bare the bound reads as the lead-in every run decodes, which would
    make the tool look unusable to exactly the reader who came to find out
    whether it is. The note is therefore not decoration: it is the difference
    between the worst case over the parameter range and the number this
    configuration pays, and `core/tool_base.py` says only the first is statable
    without a configuration in hand.
    """
    refinable = [
        spec
        for spec in discover()
        if spec.params_model.warmup_frames is not ParamsBase.warmup_frames
    ]
    fixed = [
        spec
        for spec in discover()
        if spec.params_model.warmup_frames is ParamsBase.warmup_frames
        and spec.warmup_frames.frames > 0
    ]
    assert refinable and fixed, "both halves of the contrast need a tool on the shelf"

    for spec in refinable:
        assert "worst case" in _line(_block(spec.tool_id), "warmup_frames")
    for spec in fixed:
        assert "worst case" not in _line(_block(spec.tool_id), "warmup_frames")


def test_every_parameter_prints_the_population_kind_it_declares() -> None:
    """`param_stereotypes` is total over the params model, so the output is too.

    The map is refused at registration unless it covers every field, and a field
    it skipped would be one the Phase-7 generator emits no widget for. Printing
    the kind beside each parameter is what turns that totality from a rule about
    a mapping into something a reader can check against the parameter list they
    are looking at.
    """
    for spec in discover():
        block = _block(spec.tool_id)
        assert spec.param_stereotypes, f"{spec.tool_id} declares no stereotypes"
        for name, kind in spec.param_stereotypes.items():
            assert str(kind) in _param_line(block, name)


def test_naming_a_tool_narrows_the_shelf_rather_than_resolving_a_version() -> None:
    """Every registered version of the id, which is why there is no `--version`.

    The registry is keyed by `(id, version)` because two versions of a tool are
    two different things a project can name, so a listing that collapsed them
    would hide the distinction it is most useful about.
    """
    for spec in discover():
        block = _block(spec.tool_id)
        assert _line(block, spec.tool_id) == f"{spec.tool_id} {spec.version}"
        assert len(_versions(block, spec)) == len(
            [other for other in discover() if other.tool_id == spec.tool_id]
        )


def _versions(block: str, spec: ToolSpec) -> list[str]:
    return [line for line in block.splitlines() if line.startswith(f"{spec.tool_id} ")]


def test_a_tool_with_no_parameters_says_so_rather_than_printing_a_bare_header() -> None:
    """The one branch of the block no tool on the shelf reaches yet.

    A params model with no fields is legal — nothing about a tool requires one to
    be configurable — and the column widths are taken over the field names, so
    the untaken branch is not cosmetic: without it the command raises on the
    first tool that has none. Built here rather than registered, because putting a
    fixture on the process-wide shelf would leave it there for every other case.
    """

    class NoParams(ParamsBase):
        pass

    spec = ToolSpec(
        tool_id="knobless",
        version="1.0.0",
        summary="A tool with nothing to set.",
        params_model=NoParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        element=ElementRelation.PRESERVED,
    )
    assert _param_line(_describe(spec), "(none)")


def test_an_unknown_tool_is_refused_and_the_shelf_is_named() -> None:
    """A wrong id is a typo far more often than a missing install.

    So the refusal prints what is registered: the fix is then on screen rather
    than one more invocation away.
    """
    result = runner.invoke(app, ["inspect", "detekt"])
    assert result.exit_code == 1
    assert "no tool detekt" in result.stderr
    for spec in discover():
        assert spec.tool_id in result.stderr
