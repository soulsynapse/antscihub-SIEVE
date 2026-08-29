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
from sieve.contract.nodes import Source

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

    @property
    def sources(self) -> tuple[Tool, ...]:
        return tuple(t for t in self.tools if isinstance(t.role, Source))

    def source_for(self, address: str) -> Tool | None:
        """The first source tool willing to try *address*.

        First rather than best: ranking tools against each other is an opinion
        SIEVE would have to hold about tools, and the order of the search path
        is already the user's to set.
        """
        for tool in self.sources:
            try:
                if tool.role.handles(address):
                    return tool
            except Exception:
                continue
        return None

    def dialog_filter(self) -> str:
        """The filter a file chooser offers, built from the loaded sources.

        A hint, never the gate — `source_for` decides. All files is always
        offered last, so a pattern too narrow costs a click rather than making
        a file SIEVE would happily have taken unreachable.
        """
        patterns = sorted({p for tool in self.sources for p in tool.role.patterns})
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
        if isinstance(tool, Tool) and isinstance(tool.role, Source):
            tools.append(tool)
        else:
            unavailable.append(Unavailable(path, f"{tool!r} is not a Tool"))
