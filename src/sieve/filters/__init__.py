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

**The markdown has a grammar, and it is declared here** — `GUIDANCE_SECTIONS`,
with `parse_guidance` and `guidance_for` reading against it. §3's second half is
a file every filter ships, so what that file is made of is this package's fact
in the same way `guidance_path` is: the two change in one commit whenever the
convention moves. It lived in `gui/wizard_model.py`, where the pane happened to
be the first thing that needed the sections split, and the cost was that the §3
guardrail could only assert the file *existed* — the one module able to say
whether it said anything sat a layer above the test.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from dataclasses import dataclass
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


#: The `## ` headers a guidance file answers, in the order it answers them.
#: Three questions a user asks in front of a filter they have not used: when it
#: helps, where it will disappoint them, and what it costs. A filter is free to
#: add sections; a reader of `Guidance` only ever sees these.
GUIDANCE_SECTIONS = ("When to use it", "What it does not do", "Cost")


@dataclass(frozen=True, slots=True)
class Guidance:
    """A filter's markdown split into the sections above, plus its one-liner.

    `summary` comes off the spec, not out of the file, so the sentence a
    listing shows and the sentence a reader of the guidance sees are the same
    string rather than two that drift.
    """

    summary: str
    when_to_use: str
    not_do: str
    cost: str


def parse_guidance(text: str) -> dict[str, str]:
    """`## ` sections of a guidance file, header → body, reading order.

    The intro before the first `##` lands under `""`. Deliberately dumb — the
    guidance files are house-written markdown, and a parser that understood
    more of it would invite prose that renders in one consumer and nowhere
    else.
    """
    sections: dict[str, str] = {}
    header = ""
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[header] = "\n".join(lines).strip()
            header = line[3:].strip()
            lines = []
        else:
            lines.append(line)
    sections[header] = "\n".join(lines).strip()
    return sections


def guidance_for(spec: FilterSpec) -> Guidance:
    """`spec`'s guidance, degrading to its summary when the file cannot be read.

    Missing guidance is not an error here, the same posture `sieve inspect`
    takes: an out-of-tree filter is allowed to exist before its documentation
    does, and it is the guardrail test's job — not a user's — to insist that
    everything in this package has both halves of §3.
    """
    try:
        path = guidance_path(spec)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
    except (LookupError, OSError):
        text = ""
    sections = parse_guidance(text)
    when_to_use, not_do, cost = (sections.get(name, "") for name in GUIDANCE_SECTIONS)
    return Guidance(summary=spec.summary, when_to_use=when_to_use, not_do=not_do, cost=cost)
