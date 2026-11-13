"""The catalogue of tools. README.md beside this file is the spec; `__all__` is what it names."""
import importlib
import os
import re
import sys
import traceback
from dataclasses import dataclass
from typing import Any

MARKER = "SIEVE_TOOL"

# facet -> the literal line a tool adds to supply it. Order: what discovery needs, then the rest.
_HINTS = {
    MARKER: "SIEVE_TOOL = True",
    "NAME": 'NAME = "mytool"',
    "KIND": 'KIND = "frame"  # or "series", or "same": the kind of the node wired into its first input',
    "EXPECTS": 'EXPECTS = "gray"  # or a tuple; the report lists the types in use',
    "PRODUCES": 'PRODUCES = "gray"  # or "same": out as in',
    "DEFAULTS": "DEFAULTS = {}",
    "run": "def run(frames, row, params): ...",
    "fold": "def fold(frame): ...  # a series tool: what the walk stacks per row in place of the frame",
    "step": "def step(state, row, i, params): ...  # a series tool that steps: (the next state, {field: this row's share of run's result}); state is None at the first row",
    "settings": "def settings(parent=None): ...",
    "draw": "def draw(painter, row, result, start, params): ...",
    "pick": "def pick(point, shape, row, result, params): ...  # a drawer answers a left click at point, (x, y) in the displayed frame's pixels, on a frame of shape (height, width): the params to merge, or None for a click it does not claim",
    "INPUTS": 'INPUTS = {"bg": "gray"}  # frame inputs after the first: name -> the types it expects; run reads one as frames(row, name)',
    "OPTIONAL": 'OPTIONAL = ("bg",)  # the INPUTS the node computes without; run reads an unwired one as None',
    "STATIC": "STATIC = True  # the same output at every row: computed once per key, held once, counted per change",
    "PATHS": 'PATHS = {"settings": load_settings}  # path inputs: name -> params from the file',
    "PARAMS": 'PARAMS = {"regions": from_region}  # INPUTS that also carry params: name -> params from the params of the node wired in',
    "select": "def select(folder, params): ...  # a selector: the path it picks under folder, or None",
    "matches": "def matches(folder, params): ...  # a selector: every path its rule matches, picked first",
    "bake": "def bake(params, count): ...  # the node bakes: (the plate rows a bake writes over a clip of count rows, the frame writer's quality); a Bake button under it",
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


def types(entries, extra=()):
    """{type: (producers, expecters)} over the tools that imported, plus `extra` (name, produces,
    expects) rows for nodes that are not tools. "same" is not a type; a PATHS key expects "path"."""
    out = {}
    rows = [(e.name, e.get("PRODUCES"), e.get("EXPECTS"), e.get("PATHS")) for e in entries if e.ok]
    for name, p, ex, paths in rows + [(*r, None) for r in extra]:
        if isinstance(p, str) and p != "same":
            out.setdefault(p, (set(), set()))[0].add(name)
        for t in ((ex,) if isinstance(ex, str) else ex or ()) + (("path",) if paths else ()):
            out.setdefault(t, (set(), set()))[1].add(name)
    return out


CATEGORIES = ("source", "convert", "relate", "transform", "cache", "measure")   # the Tab menu's order: a pipeline's


def category(tool):
    """The group `tool` falls in, read off its facets by the first rule that fits: a source has no
    `EXPECTS`; a cache has `bake`; a measure produces signal and does not expect it; a relate has
    `INPUTS` and produces `same` or a type it expects; a convert produces a type it does not expect;
    the rest transform. Measure sits before convert and cache before transform because each is the
    other by shape."""
    ex = probe(tool, "EXPECTS")
    if ex is None:
        return "source"
    ex = {ex} if isinstance(ex, str) else set(ex)
    p = probe(tool, "PRODUCES")
    if probe(tool, "bake") is not None:
        return "cache"
    if p == "signal" and "signal" not in ex:
        return "measure"
    if probe(tool, "INPUTS") and (p == "same" or p in ex):
        return "relate"
    if p != "same" and p not in ex:
        return "convert"
    return "transform"


_LABEL = re.compile(r"^[A-Za-z ]{1,20}:\s+")
_SENTENCE = re.compile(r"(.*?[.!?])(?=\s+[A-Z`(]|\s*$)", re.S)


def description(tool):
    """The first sentence of `tool`'s own docstring, its leading label ("Frame tool:", "Selector:")
    and final period dropped; "" for a tool without one."""
    doc = (vars(tool).get("__doc__") or "").strip()
    first = " ".join(doc.split("\n\n", 1)[0].split())
    m = _SENTENCE.match(first)
    return _LABEL.sub("", m.group(1) if m else first).rstrip(".")


def signature(tool):
    """What `tool` reads and hands out, as "gray, mask → blobs": a source reads nothing and a
    pass-through hands out "same"."""
    ex = probe(tool, "EXPECTS")
    ins = [ex] if isinstance(ex, str) else list(ex or ())
    return f"{', '.join(ins)} → {probe(tool, 'PRODUCES')}".strip()


__all__ = ["MARKER", "FACETS", "Entry", "is_tool", "probe", "hint", "discover", "types", "CATEGORIES", "category", "description", "signature"]
