"""The catalogue of tools. README.md beside this file is the spec; `__all__` is what it names."""
import ast
import importlib
import itertools
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
    "select": "def select(folder, params): ...  # a selector: the path it picks under folder, or None",
    "matches": "def matches(folder, params): ...  # a selector: every path its rule matches, picked first",
    "bake": "def bake(params, count): ...  # the node bakes: (the plate rows a bake writes over a clip of count rows, the frame writer's quality); a Bake button under it",
}
FACETS = tuple(_HINTS)

# class -> the types one body may serve alike; `strains` and `verb` read it, nothing else does
CLASSES = {
    "plane": frozenset({"bgr", "gray", "hsv", "mask", "flow"}),
    "table": frozenset({"blobs", "tracks"}),
}


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


def expects(entry):
    """The set of types `EXPECTS` names; empty for a source."""
    ex = entry.get("EXPECTS")
    return {ex} if isinstance(ex, str) else set(ex or ())


def strains(entries, classes=CLASSES):
    """[(tool, class, the class's types it lacks)] for every imported tool whose `EXPECTS` names more
    than one type of a class and not all of them, in entry order. One type alone never strains."""
    out = []
    for e in (e for e in entries if e.ok):
        ex = expects(e)
        for cls, members in classes.items():
            if len(ex & members) > 1 and not members <= ex:
                out.append((e.name, cls, members - ex))
    return out


def verb(name, classes=CLASSES):
    """`name` less every hyphenated word that is a type or a class of `classes`; a name of such words
    alone is its own verb, so the tools named for a wire do not all share an empty one."""
    words = set(classes).union(*classes.values())
    return "-".join(w for w in name.split("-") if w not in words) or name


def names(entry):
    """The names the tool's file binds at top level by def, class or assignment, less `FACETS`. Read
    from the source and not the module, where a constant imported from a shared module looks defined."""
    with open(entry.path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                out |= {n.id for n in (t.elts if isinstance(t, ast.Tuple) else [t]) if isinstance(n, ast.Name)}
    return out - set(FACETS)


def pairs(entries, classes=CLASSES, share=0.6, floor=3):
    """[(a, b, same verb, names shared, names in union)] for every two imported tools whose verbs are
    equal under `classes`, or which share at least `share` of their top-level names and `floor` of
    them at least, in entry order. A pair is a question, one tool declared twice or two operations."""
    tools = [(e.name, names(e)) for e in entries if e.ok]
    out = []
    for (a, na), (b, nb) in itertools.combinations(tools, 2):
        same = verb(a, classes) == verb(b, classes)
        inter, union = len(na & nb), len(na | nb)
        if same or (inter >= floor and inter >= share * union):
            out.append((a, b, same, inter, union))
    return out


__all__ = ["MARKER", "FACETS", "CLASSES", "Entry", "is_tool", "probe", "hint", "discover", "types", "strains", "verb", "pairs"]
