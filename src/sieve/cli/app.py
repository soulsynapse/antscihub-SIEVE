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
from sieve.cli.run_cmd import run_project

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


def _print_version(value: bool) -> None:
    """Eager `--version`, so it answers without a subcommand being required."""
    if value:
        typer.echo(f"sieve {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_print_version, is_eager=True, help="Print the version."
        ),
    ] = False,
) -> None:
    """Root callback. Exists to carry `--version`; the commands do the work."""


if __name__ == "__main__":
    app()
