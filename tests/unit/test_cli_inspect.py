"""`sieve inspect` — the declared shelf, printed.

The emission list is a declaration whose real consumer is a save screen that
does not exist, so printing it is what makes it falsifiable now
(`adr/declared-means-verified.md`): a list nobody can read is a list nobody can
catch lying. The tests below therefore check the two things a reader of that
output relies on — that every tool on the shelf is in it, and that what each one
prints is its own declaration rather than a shape this command invented.

The shelf is read through `discover()` rather than written out here, so a tool
landing tomorrow is covered without an edit, and a tool whose emission list
changes cannot leave this file asserting the old one.
"""

from __future__ import annotations

from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.tools import discover

runner = CliRunner()


def _output() -> str:
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 0, result.output
    return result.output


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
