"""Every registered command describes itself, whatever happened to its docstring.

`sieve --help` is the only place a user learns what the subcommands are, and
Typer will happily render a blank line for a command it has no summary for. The
prose convention in `tools/docstring_audit.py` deletes function docstrings, so
for a stretch `materialize` and `sweep` were listed with nothing beside them —
a user-visible regression that `nox -s checks` passed cleanly, because nothing
here asserted on help text.

Asserting on emptiness rather than on wording: the summaries are prose and will
be rewritten, but a command that lost its description is always a defect.
"""

from __future__ import annotations

from typer.core import TyperGroup
from typer.main import get_command
from typer.testing import CliRunner

from sieve.cli.app import app

runner = CliRunner()


def _commands() -> TyperGroup:
    # TyperGroup is not a click.Group in this Typer, which vendors its own click
    # shim under `typer._click` — isinstance against click's own class fails.
    group = get_command(app)
    assert isinstance(group, TyperGroup)
    return group


def test_every_command_has_a_short_help() -> None:
    group = _commands()
    missing = [name for name, command in group.commands.items() if not command.get_short_help_str()]
    assert not missing, f"registered with no help text: {missing}"


def test_the_command_list_names_every_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in _commands().commands:
        assert name in result.output


def test_help_does_not_leak_a_docstring_section_header() -> None:
    # A docstring used as help arrives whole, so `Raises:` reaches the terminal
    # as if it were guidance. An explicit `help=` is what keeps it out.
    for name in _commands().commands:
        result = runner.invoke(app, [name, "--help"])
        assert result.exit_code == 0
        assert "Raises:" not in result.output
