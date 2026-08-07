"""The `sieve` command: argument parsing and nothing else.

Commands are registered here rather than decorated in their own modules so that
this file is the whole of the surface — `sieve --help` and the contents of this
module are the same list, and a command that exists but was never wired in is a
state that cannot be reached. The cost is one line per command, paid once.

Exit codes are Typer's: 0 for success, 2 for a usage error it raises itself, and
1 for everything this package refuses deliberately. There is no code that means
"ran but produced nothing" — a run over an empty graph is a successful run of an
empty graph, and a caller that cares about output counts reads them rather than
a status.

The rest of v2's surface is not missing so much as not yet standing on anything:
`materialize` and the full `run` land in Phase 5 with results at rest,
`preview` and `sweep` in Phase 6 with `bench` (`PLAN.md`). `detect` never
lands — detection is a node (`adr/detector-is-a-node.md`).

The console-script entry point (`main`) is deliberately not the Typer callback
(`_group`). The callback runs inside `CliRunner` too, which drives the app
in-process with `sys.stderr` replaced by its own capture, and `decode/quiet.py`
takes file descriptor 2 — so silencing the decoder's stderr from the callback
would displace a fixture a test is about to read from. `main` runs only for a
real process started by a real invocation, which is the only time taking fd 2 is
anyone's business.
"""

from __future__ import annotations

import typer

from sieve.cli.inspect_cmd import inspect_tools
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

# The one-line summary is passed here rather than left to Typer's fallback of
# reading the command function's docstring. The fallback couples user-facing
# help to a docstring the prose convention rewrites freely, and it pastes the
# whole docstring in, so a `Raises:` block reaches the terminal as if it were
# guidance.
app.command("run", help="Run a project's pipeline over a span of its source video.")(run_project)
app.command("inspect", help="Describe the registered tools, or one of them.")(inspect_tools)


@app.callback()
def _group() -> None:
    """A callback with nothing to do, which is what keeps `run` a subcommand.

    Typer collapses an app holding exactly one command into that command, so
    without this the surface would be `sieve <project>` today and `sieve run
    <project>` the day a second command lands — a rename of the one thing a
    cluster script types, caused by an edit somewhere else.
    """


def main() -> None:
    silence_raw_format_warning()
    app()


if __name__ == "__main__":
    main()
