"""The catalogue of tools. README.md beside this file is the spec; `__all__` is what it names."""
import importlib
import os
import sys
import traceback
from dataclasses import dataclass
from typing import Any

MARKER = "SIEVE_TOOL"

# facet -> the literal line a tool adds to supply it. Order: what discovery needs, then the rest.
_HINTS = {
    MARKER: "SIEVE_TOOL = True",
    "NAME": 'NAME = "mytool"',
    "KIND": 'KIND = "frame"  # or "series"',
    "EXPECTS": 'EXPECTS = "gray"  # or a tuple of types',
    "PRODUCES": 'PRODUCES = "gray"  # or "same": out as in',
    "DEFAULTS": "DEFAULTS = {}",
    "run": "def run(frames, row, params): ...",
    "settings": "def settings(parent=None): ...",
    "draw": "def draw(painter, row, result, start): ...",
    "output_name": "def output_name(src, params): ...",
    "export_command": "def export_command(src, dst, params, fps): ...",
    "describe_output": "def describe_output(src, params, fps): ...",
    "PATHS": 'PATHS = {"settings": load_settings}  # path inputs: name -> params from the file',
    "select": "def select(folder, params): ...  # a selector: the path it picks under folder, or None",
    "matches": "def matches(folder, params): ...  # a selector: every path its rule matches, picked first",
}
FACETS = tuple(_HINTS)


def probe(tool, facet):
    """The attribute, or None: the tool did not say. Reads only; never calls."""
    return getattr(tool, facet, None)


def hint(facet):
    """The line a tool adds to supply `facet`."""
    return _HINTS[facet]


def is_tool(obj):
    return bool(probe(obj, MARKER)) and isinstance(probe(obj, "NAME"), str)


@dataclass
class Entry:
    name: str
    module: Any = None
    path: str = ""
    error: str = ""

    @property
    def ok(self):
        return self.module is not None

    def get(self, facet):
        return probe(self.module, facet)

    @property
    def missing(self):
        return [f for f in FACETS if self.get(f) is None]


def _import(root, stem):
    parent, pkg = os.path.split(os.path.abspath(root))
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return importlib.import_module(f"{pkg}.{stem}")


def discover(*roots):
    """Every tool and every unimportable module under `roots`, in path order. See README."""
    out = []
    for root in roots:
        for fn in sorted(os.listdir(root)):
            stem, ext = os.path.splitext(fn)
            if ext != ".py" or stem.startswith("_"):
                continue
            path = os.path.join(root, fn)
            try:
                mod = _import(root, stem)
            except Exception as e:  # a broken tool is an entry, not a crash
                tb = traceback.extract_tb(e.__traceback__)[-1]
                where = f"{os.path.basename(tb.filename)}:{tb.lineno}"
                out.append(Entry(stem, None, path, f"{type(e).__name__}: {e} ({where})"))
                continue
            if is_tool(mod):
                out.append(Entry(probe(mod, "NAME"), mod, path))
    return out


__all__ = ["MARKER", "FACETS", "Entry", "is_tool", "probe", "hint", "discover"]
