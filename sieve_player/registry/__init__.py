"""The catalogue of tools. README.md beside this file is the spec; `__all__` is what it names."""
import hashlib
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
    "PARAMS": 'PARAMS = {"radius": {"default": 3, "kind": "int", "range": (1, 15)}}  # every param, once, in the order of its rows: its default, the kind of its value among KINDS, and "range" for an int or a float, "decimals" for a float, "choices" for a choice with "unlisted": True where a value outside them is taken; one of a default alone has no row',
    "run": "def run(frames, row, params): ...",
    "fold": "def fold(frame): ...  # a series tool: what the walk stacks per row in place of the frame",
    "step": "def step(state, row, i, params): ...  # a series tool that steps: (the next state, {field: this row's share of run's result}); state is None at the first row",
    "settings": "def settings(parent=None): ...  # a card of the tool's own; unsaid, the player makes the widget of PARAMS",
    "draw": "def draw(painter, row, result, start, params): ...",
    "pick": "def pick(point, shape, row, result, params): ...  # a drawer answers a left click at point, (x, y) in the displayed frame's pixels, on a frame of shape (height, width): the params to merge, or None for a click it does not claim",
    "INPUTS": 'INPUTS = {"bg": "gray"}  # frame inputs after the first: name -> the types it expects; run reads one as frames(row, name)',
    "OPTIONAL": 'OPTIONAL = ("bg",)  # the INPUTS the node computes without; run reads an unwired one as None',
    "STATIC": "STATIC = True  # the same output at every row: computed once per key, held once, counted per change",
    "PATHS": 'PATHS = {"settings": load_settings}  # path inputs: name -> params from the file',
    "key_params": "def key_params(params): ...  # what of params run reads, a JSON value, the same for any two params under which run hands out the same result of the same input: the node is keyed by it in place of its params",
    "select": "def select(folder, params): ...  # a selector: the path it picks under folder, or None",
    "matches": "def matches(folder, params): ...  # a selector: every path its rule matches, picked first",
    "cut_file": "def cut_file(video, footage, params): ...  # the node cuts the video into files: the path of the file the tool wrote of what run hands out of video, whose decoder.footage_print is footage, under params, exact or lossy as the tool wrote it, or None where the node is to run; FileNotFoundError, saying why, where the params say to serve a file and there is none, and the node then does not run; a node that reads the video node, or a node that serves a file, in which case video is that file, serves it; never a file written over",
    "cut_files": "def cut_files(video, footage, params): ...  # beside cut_file: every file the node would serve under some choice of its params",
}
FACETS = tuple(_HINTS)

# What a settings widget may have beside changed, params() and set_params(): the name the pane or
# the window looks for -> the line that supplies it. A name spelled otherwise is never called.
WIDGET_FACETS = {
    "set_source": "def set_source(self, path, fps): ...  # the footage the node's inputs are frames of, the video or the file a cutting node above it serves",
    "set_paths": "def set_paths(self, paths): ...  # {input: the file each wired path input picked}",
    "set_playhead": "def set_playhead(self, row): ...  # a chain node's card: the row shown",
    "show_result": "def show_result(self, result, start, fps): ...  # a chain node's card: its result over the rows from start",
    "set_driven": "def set_driven(self, names, by=None): ...  # the params a wire drives, and the node that drives them",
    "show_matches": "def show_matches(self, folder, found, picked): ...  # a selector's card: every path its rule matches, and the one picked",
    "set_cut_files_in_use": "def set_cut_files_in_use(self, paths): ...  # the files the document's cutting nodes name, see cut_files",
    "storeChanged": "storeChanged = Signal()  # files of the store were written or removed here, the params as they were",
}


def probe(tool, facet):
    """The attribute, or None: the tool did not say. Reads only; never calls."""
    return getattr(tool, facet, None)


def hint(facet):
    """The line a tool adds to supply `facet`."""
    return _HINTS[facet]


def is_tool(obj):
    return bool(probe(obj, MARKER)) and isinstance(probe(obj, "NAME"), str) and bool(probe(obj, "NAME"))     # a node's id is its tool's name, so a name is not empty


def _tuple(types):
    return tuple(types) if isinstance(types, (tuple, list, set)) else (types,)


def name(tool):
    return probe(tool, "NAME")


def by_name(tools):
    """`tools` as a mapping of name to module, whether given as one or as the modules."""
    return tools if hasattr(tools, "get") else {name(t): t for t in tools}


def kind(tool):
    """The tool's KIND, "frame" for one that did not say."""
    return probe(tool, "KIND") or "frame"


def expects(tool):
    """The types the tool's first input expects, a tuple; None for a tool that expects nothing."""
    e = probe(tool, "EXPECTS")
    return None if e is None else _tuple(e)


def produces(tool):
    """PRODUCES as the tool wrote it, "same" among what it may be; None for one that hands out nothing."""
    return probe(tool, "PRODUCES")


KINDS = ("int", "float", "bool", "text", "choice")   # the kinds of value a declared param may say
_SAID = {None: (), "int": ("range",), "float": ("range", "decimals"), "bool": (), "text": (), "choice": ("choices", "unlisted")}


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def params(tool):
    """The tool's PARAMS, name to what it says of the param, a dict of the caller's own in the
    tool's order and empty for a tool that said none. ValueError, naming the param, for a
    declaration that cannot be read."""
    declared = probe(tool, "PARAMS")
    if declared is None:
        return {}
    if not isinstance(declared, dict):
        raise ValueError(f"PARAMS is a {type(declared).__name__}, not a dict")
    for n, said in declared.items():
        if not isinstance(n, str) or not isinstance(said, dict) or "default" not in said:
            raise ValueError(f"PARAMS[{n!r}] is not a dict with a default")
        kind = said.get("kind")
        if kind not in _SAID:
            raise ValueError(f"PARAMS[{n!r}] has no kind {kind!r}; one of {KINDS}")
        extra = set(said) - {"default", "kind", *_SAID[kind]}
        if extra:
            raise ValueError(f"PARAMS[{n!r}] says {sorted(extra)}, which {'a ' + kind if kind else 'a param of no kind'} does not have")
        if kind in ("int", "float"):
            r = said.get("range")
            if not (isinstance(r, (tuple, list)) and len(r) == 2 and all(map(_number, r)) and r[0] <= r[1]):
                raise ValueError(f"PARAMS[{n!r}] has no range (lo, hi)")
        if kind == "choice":
            c = said.get("choices")
            if not (isinstance(c, (tuple, list)) and c and all(isinstance(o, str) for o in c)):
                raise ValueError(f"PARAMS[{n!r}] has no choices, a tuple of strings")
    return {n: dict(said) for n, said in declared.items()}


def defaults(tool):
    """The tool's params as a node of it begins, a dict of its own."""
    return {n: said["default"] for n, said in params(tool).items()}


def settings_of(tool):
    """The tool's settings, the maker of a card of its own, or None."""
    return probe(tool, "settings")


def inputs(tool):
    """The tool's frame inputs after the first, in order: name to the types each expects."""
    return {n: _tuple(t) for n, t in (probe(tool, "INPUTS") or {}).items()}


def optional(tool):
    """The frame inputs after the first that may be unwired."""
    return tuple(probe(tool, "OPTIONAL") or ())


def static(tool):
    """Whether the tool's output is the same at every row."""
    return bool(probe(tool, "STATIC"))


def paths(tool):
    """The tool's path inputs: name to the loader that turns the file into params."""
    return dict(probe(tool, "PATHS") or {})


def is_selector(tool):
    return produces(tool) == "path" and expects(tool) is None


def cuts(tool):
    """Whether the tool cuts the footage into files, by its cut_file."""
    return probe(tool, "cut_file") is not None


def names_cut_files(tool):
    return probe(tool, "cut_files") is not None


def steps(tool):
    return probe(tool, "step") is not None


def draws(tool):
    return probe(tool, "draw") is not None


def fold_of(tool):
    """The tool's fold, or None."""
    return probe(tool, "fold")


def key_params_of(tool):
    """The tool's key_params, or None."""
    return probe(tool, "key_params")


def pick_of(tool):
    """The tool's pick, or None."""
    return probe(tool, "pick")


def matches_of(tool):
    """The tool's matches, or None."""
    return probe(tool, "matches")


# facet -> the readers here that answer of it: what `--check` looks for a call of outside this
# package, beside a call of the facet itself. A facet with neither is one nothing reads.
READERS = {
    "NAME": ("name", "by_name"), "KIND": ("kind",), "EXPECTS": ("expects", "is_selector"),
    "PRODUCES": ("produces", "is_selector"), "PARAMS": ("params", "defaults"), "settings": ("settings_of",), "INPUTS": ("inputs",),
    "OPTIONAL": ("optional",), "STATIC": ("static",), "PATHS": ("paths",), "cut_file": ("cuts",),
    "cut_files": ("names_cut_files",), "step": ("steps",), "draw": ("draws",), "fold": ("fold_of",),
    "key_params": ("key_params_of",), "pick": ("pick_of",), "matches": ("matches_of",),
}


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


_FILES = {}     # path -> ((size, mtime), the digest of its bytes then)
_IMPORTED = {}  # id of a module -> (the module, its code_print when discover first imported it); by id since a tool may be any object, hashable or not


def _file_print(path):
    st = os.stat(path)
    stamp = st.st_size, st.st_mtime_ns
    if _FILES.get(path, (None,))[0] != stamp:
        with open(path, "rb") as f:
            _FILES[path] = (stamp, hashlib.sha1(f.read()).hexdigest())
    return _FILES[path][1]


def code_print(tool):
    """A digest of the code `tool` is made of as it lies on disk now: its own file and every file
    of its folder whose name begins with an underscore, what the tools there share. None for a
    module of no file, or one whose file is gone."""
    path = getattr(tool, "__file__", None)
    if not path:
        return None
    root, own = os.path.split(os.path.abspath(path))
    try:
        shared = sorted(n for n in os.listdir(root) if n.startswith("_") and n.endswith(".py"))
        return hashlib.sha1("|".join(f"{n}:{_file_print(os.path.join(root, n))}" for n in [own, *shared]).encode()).hexdigest()[:16]
    except OSError:
        return None


def imported_print(tool):
    """`tool`'s code_print as discover found it when it first imported the module: the code this
    process runs, whatever the file has become since. None for a module discover did not import."""
    had = _IMPORTED.get(id(tool))
    return had[1] if had is not None and had[0] is tool else None


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
                _IMPORTED.setdefault(id(mod), (mod, code_print(mod)))
                try:
                    params(mod)
                except ValueError as e:
                    out.append(Entry(probe(mod, "NAME"), None, path, str(e)))
                    continue
                out.append(Entry(probe(mod, "NAME"), mod, path))
    return out


def types(entries, extra=()):
    """{type: (producers, expecters)} over the tools that imported, plus `extra` (name, produces,
    expects) rows for nodes that are not tools. "same" is not a type; a PATHS key expects "path"."""
    out = {}
    rows = [(e.name, produces(e.module), expects(e.module), paths(e.module)) for e in entries if e.ok]
    for tool, p, ex, loaders in rows + [(n, p, None if ex is None else _tuple(ex), None) for n, p, ex in extra]:
        if isinstance(p, str) and p != "same":
            out.setdefault(p, (set(), set()))[0].add(tool)
        for t in (ex or ()) + (("path",) if loaders else ()):
            out.setdefault(t, (set(), set()))[1].add(tool)
    return out


CATEGORIES = ("source", "convert", "relate", "transform", "measure")   # the Tab menu's order: a pipeline's


def category(tool):
    """The group `tool` falls in, read off its facets by the first rule that fits: a source has no
    `EXPECTS`; a measure produces signal and does not expect it; a relate has `INPUTS` and produces
    `same` or a type it expects; a convert produces a type it does not expect; the rest transform.
    Measure sits before convert because it is one by shape."""
    ex = expects(tool)
    if ex is None:
        return "source"
    p = produces(tool)
    if p == "signal" and "signal" not in ex:
        return "measure"
    if inputs(tool) and (p == "same" or p in ex):
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
    return f"{', '.join(expects(tool) or ())} → {produces(tool)}".strip()


__all__ = ["MARKER", "FACETS", "WIDGET_FACETS", "READERS", "KINDS", "Entry", "is_tool", "probe", "hint", "discover", "code_print", "imported_print", "types", "CATEGORIES", "category",
           "description", "signature", "name", "by_name", "kind", "expects", "produces", "params", "defaults", "settings_of", "inputs", "optional", "static", "paths",
           "is_selector", "cuts", "names_cut_files", "steps", "draws", "fold_of", "key_params_of", "pick_of", "matches_of"]
