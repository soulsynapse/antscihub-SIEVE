"""One module per tool: a ToolSpec and one plain run function.

Every tool is found by scanning this package, not by listing it. This module is
therefore deliberately empty of tool names — a single `from sieve.tools import
downsample` here would be the manifest that `core.tool_registry`'s docstring
forbids, and the first test in `tests/unit/test_tool_discovery.py` asserts that
no such import exists.

The scan is `pkgutil` over this package's own `__path__`, so a new module drops
in and is found. Importing it is what registers it: `@register_tool` puts the
spec on `core.tool_registry.REGISTRY` at import time.

v2's version of this module also owned the guidance-markdown grammar, because a
step there was one class plus one colocated `.md`. v3 has no per-tool document
— guidance is a `ToolSpec` field arriving with the expander that reads it — so
the two guardrails that checked those files have no subject here and are not
ported.
"""

from __future__ import annotations

import importlib
import pkgutil

from sieve.core.tool_base import ToolSpec
from sieve.core.tool_registry import REGISTRY


def discover() -> tuple[ToolSpec, ...]:
    """Import every tool module, then return what is on the shelf.

    Idempotent, because `importlib.import_module` is: a second call re-reads
    `sys.modules` and registers nothing twice. A test that has cleared
    `REGISTRY` is the one caller this surprises — clearing the registry does not
    unload the modules, so the specs do not come back. Such a test should
    register into a scratch `ToolRegistry` instead.

    Modules whose name starts with an underscore are skipped, so shared helpers
    can sit beside the tools without being imported as if they were one.

    Returns:
        Every registered spec, ordered by `(tool_id, version)` — including any
        registered by something other than this scan, since the shelf is
        process-wide and this returns the shelf rather than the scan's own
        results.
    """
    for module in pkgutil.iter_modules(__path__, f"{__name__}."):
        if module.name.rpartition(".")[2].startswith("_"):
            continue
        importlib.import_module(module.name)
    return tuple(sorted(REGISTRY, key=lambda spec: spec.key))
