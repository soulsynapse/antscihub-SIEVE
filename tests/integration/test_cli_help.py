"""Every registered command describes itself, whatever happened to its docstring.

`sieve --help` is the only place a user learns what the subcommands are, and
Typer will happily render a blank line for a command it has no summary for. In
v2 a docstring-stripping sweep took the summaries off two commands and both were
listed with nothing beside them for a stretch — a user-visible regression the
gate passed cleanly, because nothing asserted on help text. `cli/app.py` answers
it by passing `help=` at registration rather than letting Typer fall back to the
command function's docstring; these are what hold that answer in place.

Asserting on emptiness rather than on wording: the summaries are prose and will
be rewritten, but a command that lost its description is always a defect. An
integration test because the claim is about the assembled surface — the app with
every command wired into it — rather than about any one command's behaviour.
"""

from __future__ import annotations

from typer.core import TyperGroup
from typer.main import get_command
from typer.testing import CliRunner

from sieve.cli.app import app

runner = CliRunner()


def _commands() -> TyperGroup:
    # `TyperGroup` is not a `click.Group` in this Typer, which vendors its own
    # click shim under `typer._click` — isinstance against click's own class
    # fails.
    group = get_command(app)
    assert isinstance(group, TyperGroup)
    return group


def test_every_command_has_a_short_help() -> None:
    group = _commands()
    missing = [name for name, command in group.commands.items() if not command.get_short_help_str()]
    assert not missing, f"registered with no help text: {missing}"


def test_the_command_list_names_every_command() -> None:
    """`cli/app.py`'s claim that the module and `sieve --help` are one list.

    Only checkable in this direction: a command wired in and not printed is a
    surface a user cannot find, while the reverse — printed and not wired — is
    the state Typer has no way to reach.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in _commands().commands:
        assert name in result.output


def test_help_does_not_leak_a_docstring_section_header() -> None:
    """The reason the summaries are passed at registration rather than inferred.

    A docstring used as help arrives whole, so the `Raises:` block that documents
    `inspect`'s exit code would reach the terminal as if it were guidance for the
    user. An explicit `help=` is what keeps it out, and this is what notices when
    one is dropped.
    """
    for name in _commands().commands:
        result = runner.invoke(app, [name, "--help"])
        assert result.exit_code == 0
        assert "Raises:" not in result.output
