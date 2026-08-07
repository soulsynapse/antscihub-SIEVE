"""`sieve inspect` — what is on the shelf, read off the declarations.

Here for one declaration and no more. `ToolSpec.emissions` says what a tool can
be asked to keep, and its designed consumer is a save screen in Phase 7; a field
whose only reader is two phases out is the shape `adr/declared-means-verified.md`
refuses, so printing it is the consumer that makes it falsifiable now. A list
nobody can read is a list nobody can catch lying.

The rest of v2's `inspect_cmd` is not folded in here: the window contract, the
population kinds, and the guidance path are `docs/todo/inspect-answers-what-is-
on-the-shelf.md`'s to port, and this command gains them there rather than
arriving speculatively complete.

The shelf comes from `discover()`, so a tool that lands tomorrow is listed
without an edit here — the same property `sieve.tools` exists to have.
"""

from __future__ import annotations

import typer

from sieve.core.tool_base import ToolSpec
from sieve.tools import discover


def inspect_tools() -> None:
    """Print every registered tool and the outputs it can be asked to keep."""
    for spec in discover():
        typer.echo(_describe(spec))


def _describe(spec: ToolSpec) -> str:
    """One tool, one block.

    The selecting parameter is named beside the list because without it the four
    signals of a `block_signal` read as four things one node produces at once,
    which is the opposite of what the declaration says: they are what it can be
    configured to produce, one per run.
    """
    selector = spec.emissions[0].selected_by
    chooses = f" ({selector})" if selector is not None else ""
    return (
        f"{spec.tool_id} {spec.version}\n"
        f"  {spec.summary}\n"
        f"  can emit{chooses}: {', '.join(spec.emission_names)}"
    )
