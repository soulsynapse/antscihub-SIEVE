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

The console-script entry point (`main`) is deliberately not the Typer callback
(`root_options`). The callback runs inside `CliRunner` too, which drives the
app in-process with `sys.stderr` replaced by its own capture, and
`decode/quiet.py` takes file descriptor 2 — so installing the stderr filter
from the callback would displace a fixture a test is about to read from.
`main` runs only for a real process started by a real invocation, which is
the only time taking fd 2 is anyone's business.
"""

from __future__ import annotations

from typing import Annotated

import typer

from sieve import __version__
from sieve.cli.detect_cmd import detect_project
from sieve.cli.inspect_cmd import inspect_filters
from sieve.cli.materialize_cmd import materialize_replicate
from sieve.cli.preview_cmd import preview_project
from sieve.cli.run_cmd import run_project
from sieve.cli.sweep_cmd import sweep_decode
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

# The one-line summary is passed here rather than left to Typer's fallback of
# reading the command function's docstring. The fallback couples user-facing
# help to a docstring the prose convention deletes — `materialize` and `sweep`
# had already lost their help text that way — and it pastes the whole docstring
# in, so a `Raises:` block reached the terminal as if it were guidance.
app.command("inspect", help="List the installed filters, or describe one of them.")(inspect_filters)
app.command("run", help="Run a project's pipeline over its representative clip.")(run_project)
app.command("preview", help="Render a project's representative clip and report what it cost.")(
    preview_project
)
app.command(
    "materialize", help="Write one replicate's crop to disk and register it on the project."
)(materialize_replicate)
app.command("detect", help="Detect events in a project's replicates and print the intervals.")(
    detect_project
)
app.command(
    "sweep", help="Measure ms/frame across core sets and worker counts, and report the spread."
)(sweep_decode)


def _print_version(value: bool) -> None:
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
    pass


def main() -> None:
    silence_raw_format_warning()
    app()


if __name__ == "__main__":
    main()
