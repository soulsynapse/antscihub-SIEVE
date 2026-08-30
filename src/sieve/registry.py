"""Which tools this SIEVE found, and which it could not load.

Substrate machinery, held apart from `sieve.contract` on purpose: this needs
the settings, and a contract that pulled the settings in behind it would put
every tool one import from the application.

Tools are loaded **by path**, not imported by name. That is what lets somebody
drop a file into a directory of their own, and it is the honest arrangement
given that `tools/` is not in the wheel — hatchling packages `src/sieve` and
nothing else.

**A tool may be absent and must not be fatal.** Its dependencies are its own,
so a missing one is a fact to report rather than a crash. Nothing here raises;
same posture as the settings and the library.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sieve import settings
from sieve.contract import Tool

#: Overrides the search path entirely, so a check loading a fixture tool does
#: not also pick up whatever the person keeps in their own directory.
_OVERRIDE = "SIEVE_TOOLS"

#: Where a user's own tool directories are remembered.
_SETTING = "tool_directories"

#: What a tool module exposes.
_EXPORT = "TOOLS"


@dataclass(frozen=True)
class Unavailable:
    """A tool file that could not be loaded, and why in a person's terms."""

    path: Path
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class Registry:
    """What was found. Empty is a legitimate answer, not an error."""

    tools: tuple[Tool, ...] = ()
    unavailable: tuple[Unavailable, ...] = ()

    def of_kind(self, kind: str) -> tuple[Tool, ...]:
        """Every loaded tool filling *kind*, in search-path order.

        Asking by role name rather than by class is what keeps this file
        from having to be edited when SIEVE contracts another role — the
        table in `contract.nodes` is the one place that changes.
        """
        return tuple(t for t in self.tools if t.kind == kind)

    @property
    def sources(self) -> tuple[Tool, ...]:
        """The tools that bring a file in. `offering` and `source_for` ask
        source-only questions of these — `handles`, `offers`, `patterns` —
        which is why they narrow here and not over every role."""
        return self.of_kind("source")

    def offering(self, kind: str) -> tuple[Tool, ...]:
        """The sources that serve *kind*, in search-path order.

        Asked before an address is in hand, which is the point: what a caller
        wants a file *for* narrows the tools long before it narrows the files.
        """
        return tuple(t for t in self.sources if kind in t.role.offers)

    def source_for(self, address: str, kind: str | None = None) -> Tool | None:
        """The first source tool willing to try *address*.

        First rather than best: ranking tools against each other is an opinion
        SIEVE would have to hold about tools, and the order of the search path
        is already the user's to set.

        `kind` narrows to sources that offer that edge kind, so a caller that
        needs frames is not handed the tool that reads parameter documents.
        Omitted, the question is the old one — anything that will open it.
        """
        for tool in (self.sources if kind is None else self.offering(kind)):
            try:
                if tool.role.handles(address):
                    return tool
            except Exception:
                continue
        return None

    def dialog_filter(self, kind: str | None = None) -> str:
        """The filter a file chooser offers, built from the loaded sources.

        A hint, never the gate — `source_for` decides. All files is always
        offered last, so a pattern too narrow costs a click rather than making
        a file SIEVE would happily have taken unreachable.

        Narrowed by `kind` alongside the gate that follows it, or the two come
        apart: a chooser offering patterns the gate then refuses is a dialog
        that hands somebody a file and takes it back.
        """
        pool = self.sources if kind is None else self.offering(kind)
        patterns = sorted({p for tool in pool for p in tool.role.patterns})
        if not patterns:
            return "All files (*)"
        return f"Sources ({' '.join(patterns)});;All files (*)"


def bundled() -> Path:
    """The tools that ship in the tree, found relative to this file."""
    return Path(__file__).resolve().parents[2] / "tools"


def directories() -> list[Path]:
    """Where to look, in order. Missing directories are skipped."""
    override = os.environ.get(_OVERRIDE)
    if override:
        found = [Path(p) for p in override.split(os.pathsep) if p]
    else:
        found = [bundled()]
        found += [Path(p) for p in settings.stored(_SETTING, []) or []]
    seen: set[Path] = set()
    ordered: list[Path] = []
    for directory in found:
        resolved = directory.expanduser()
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def load(dirs: list[Path] | None = None) -> Registry:
    """Load every tool on the search path, collecting failures not raising."""
    tools: list[Tool] = []
    unavailable: list[Unavailable] = []
    for directory in (directories() if dirs is None else dirs):
        for candidate in sorted(directory.glob("*.py")):
            if not candidate.name.startswith("_"):
                _load_file(candidate, tools, unavailable)
    return Registry(tuple(tools), tuple(unavailable))


def _load_file(
    path: Path, tools: list[Tool], unavailable: list[Unavailable]
) -> None:
    name = f"_sieve_tool_{path.stem}_{abs(hash(str(path))) & 0xFFFFFF:06x}"
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            unavailable.append(Unavailable(path, "not importable"))
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    except ImportError as error:
        # The ordinary case: a tool whose dependency is not installed. Its
        # dependencies are its own, so this is a fact, not a bug.
        unavailable.append(
            Unavailable(path, f"needs {error.name or 'a package'}", str(error))
        )
        sys.modules.pop(name, None)
        return
    except Exception as error:
        unavailable.append(
            Unavailable(path, f"failed to load: {error}", traceback.format_exc())
        )
        sys.modules.pop(name, None)
        return
    exported: Any = getattr(module, _EXPORT, ())
    if not exported:
        unavailable.append(Unavailable(path, f"exports no {_EXPORT}"))
        return
    for tool in exported:
        #: `Tool` refuses an unknown role when it is built, inside the
        #: tool's own module, so anything arriving here is already a
        #: contracted role. What is left to check is that it is a `Tool` at
        #: all — and the report says which, because "is not a Tool" was
        #: also what a perfectly good tool filling a role this file had not
        #: been taught about used to get.
        if isinstance(tool, Tool):
            tools.append(tool)
        else:
            unavailable.append(
                Unavailable(path, f"{tool!r} is not a {Tool.__name__}"))
