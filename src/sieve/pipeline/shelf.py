"""Who fills the shelf, for a front end that may not reach a tool.

`Dag.build` resolves a document's nodes against a `ToolRegistry`, and something
has to have imported the tool modules for that registry to hold anything. The
CLI calls `tools.discover()` itself; `sieve.gui` may not — `gui-computes-nothing`
forbids that import outright, so that a widget cannot learn tool identity
(`adr/gui-knows-kinds-not-tools.md`). This is the same call made one layer down,
from the layer whose whole job is running what it loads.

A module of its own rather than a function on `dag.py`, because importing it
*is* the effect: `from sieve.tools import discover` at the top of a module the
executor imports would load every tool on the shelf for anything that touched a
graph. Here the import edge and the intent are the same line.
"""

from __future__ import annotations

from sieve.core.tool_registry import REGISTRY, ToolRegistry
from sieve.tools import discover


def loaded_shelf() -> ToolRegistry:
    """The process-wide registry, with every tool module imported into it.

    Idempotent, because `discover` is.
    """
    discover()
    return REGISTRY
