













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



    no_args_is_help=True,
    add_completion=False,
)

app.command("inspect")(inspect_filters)
app.command("run")(run_project)
app.command("preview")(preview_project)
app.command("materialize")(materialize_replicate)
app.command("detect")(detect_project)
app.command("sweep")(sweep_decode)


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
