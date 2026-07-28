"""The `sieve` command: argument parsing and nothing else.

Commands are registered here rather than decorated in their own modules so that
this file is the whole of the surface — `sieve --help` and the contents of this
module are the same list, and a command that exists but was never wired in is a
state that cannot be reached. The cost is one line per command, paid once.

Exit codes are Typer's: 0 for success, 2 for a usage error it raises itself,
and 1 for everything this package refuses deliberately. There is no code that
means "ran but produced nothing" — a run over an empty graph is a successful
run of an empty graph, and a caller that cares about output counts reads them
rather than a status.
"""

from __future__ import annotations

from typing import Annotated

import typer

from sieve import __version__
from sieve.cli.inspect_cmd import inspect_filters
from sieve.cli.materialize_cmd import materialize_replicate
from sieve.cli.preview_cmd import preview_project
from sieve.cli.run_cmd import run_project
from sieve.decode.quiet import silence_raw_format_warning

app = typer.Typer(
    name="sieve",
    help="Signal Isolation for Ethological Video Events.",
    # A bare `sieve` is a user who does not yet know what the commands are, and
    # printing help is the answer to that. Non-zero exit for it is Typer's, and
    # correct: nothing was run.
    no_args_is_help=True,
    add_completion=False,
)

app.command("inspect")(inspect_filters)
app.command("run")(run_project)
app.command("preview")(preview_project)
app.command("materialize")(materialize_replicate)


def _print_version(value: bool) -> None:
    """Eager `--version`, so it answers without a subcommand being required."""
    if value:
        typer.echo(f"sieve {__version__}")
        raise typer.Exit()


@app.callback()
def root_options(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_print_version, is_eager=True, help="Print the version."
        ),
    ] = False,
) -> None:
    """Root callback. Exists to carry `--version`; the commands do the work.

    Named for what it carries rather than `main`, which is the console script
    below: Typer takes the options from the signature and the help text from
    `Typer(help=...)`, so the name is free, and leaving it as `main` would have
    put the entry point and the option carrier under one name that only one of
    them can have. Public because a leading underscore makes it look unused to
    a type checker that cannot see the decorator registering it.
    """


def main() -> None:
    """The `sieve` console script: install the stderr filter, then run.

    Deliberately not the Typer callback, and the distinction is the whole reason
    this function exists. The callback runs inside `CliRunner` too, which drives
    the app in-process with `sys.stderr` replaced by its own capture — and
    `decode/quiet.py` takes file descriptor 2, so installing from there displaces
    the fixture a test is about to read from. This runs only when a real process
    was started by a real invocation, which is the only time taking fd 2 is
    anyone's business.
    """
    silence_raw_format_warning()
    app()


if __name__ == "__main__":
    main()
