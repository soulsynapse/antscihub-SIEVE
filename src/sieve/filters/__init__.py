"""Every filter, found by scanning this package rather than by listing it.

Guardrail §3: a filter is one class plus one colocated markdown file, and
discovery finds it without edits to any registry, manifest, or import list.
This module is therefore deliberately empty of filter names — a single `from
sieve.filters import downsample` here would be the manual wiring the guardrail
forbids, and a test asserts that no such import exists.

The scan is `pkgutil` over this package's own `__path__`, so a new module drops
in and is found. Importing it is what registers it: `@register_filter` puts the
spec on `core.filter_registry.REGISTRY` and `@kernel` puts the implementations
on `backend.dispatch.KERNELS`, both at import time.

Kernels live in the filter's module, not in a shared `backend/cpu.py`, for the
same reason: if adding a filter meant editing a shared file, §3 is broken
whether that file is a manifest or a dispatch table.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

from sieve.core.filter_base import FilterSpec
from sieve.core.filter_registry import REGISTRY

#: Convention, not configuration: `downsample.py` is documented by
#: `downsample.md` beside it. A filter whose guidance is missing fails the
#: guardrail test rather than shipping undocumented.
GUIDANCE_SUFFIX = ".md"


def discover() -> tuple[FilterSpec, ...]:
    """Import every filter module, then return what is on the shelf.

    Idempotent, because `importlib.import_module` is: a second call re-reads
    `sys.modules` and registers nothing twice. A test that has cleared
    `REGISTRY` is the one caller this surprises — clearing the registry does not
    unload the modules, so the specs do not come back. Such a test should
    register into a scratch `FilterRegistry` instead.

    Modules whose name starts with an underscore are skipped, so a filter
    package can keep shared helpers beside its filters without them being
    imported as if they were one.

    Returns:
        Every registered spec, ordered by `(filter_id, version)` — including any
        registered by something other than this scan, since the shelf is
        process-wide and this returns the shelf rather than the scan's own
        results.
    """
    for module in pkgutil.iter_modules(__path__, f"{__name__}."):
        if module.name.rpartition(".")[2].startswith("_"):
            continue
        importlib.import_module(module.name)
    return tuple(sorted(REGISTRY, key=lambda spec: spec.key))


def guidance_path(spec: FilterSpec) -> Path:
    """Where `spec`'s guidance markdown lives, whether or not it is there.

    Located from the params model's defining module rather than from
    `filter_id`, so a filter whose module name and id differ still resolves —
    and so a filter registered from outside this package resolves to beside its
    own source rather than to a path in here that could never exist.

    Returns a path that may not exist; the caller decides whether that is a
    guardrail failure (it is, for every filter in this package) or a filter that
    simply has no guidance yet.

    Raises:
        LookupError: if the defining module cannot be located on disk, which
            means the filter was declared somewhere with no source file — a
            REPL, an `exec`, or a namespace package.
    """
    module = sys.modules.get(spec.params_model.__module__)
    source = getattr(module, "__file__", None)
    if source is None:
        raise LookupError(
            f"{spec.filter_id} {spec.version} is defined in "
            f"{spec.params_model.__module__!r}, which has no file to find guidance beside"
        )
    return Path(source).with_suffix(GUIDANCE_SUFFIX)
