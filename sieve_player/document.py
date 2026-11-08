"""The saved form of a pipeline: nodes, wires, the display, overlay and pinned flags, the video path
as written, and nothing of the canvas's view or the runtime's memo.

Imports neither Qt nor cv2 nor any other part of the player. The document stores tool names only;
a function that needs a tool's facets is handed the tools, a mapping of name to module or the
modules themselves. The video is a node under the reserved name VIDEO_TOOL so wires can name it;
its path lives on the document, resolved against the document's folder on load. A node's band is
read by the runtime before anything downstream sees the node, so it is saved with the node.
"""
import json
import os
from dataclasses import dataclass, field
from typing import NamedTuple

VERSION = 2                 # 2: the video node's scale is a rescale node's; a 1 with one loads with that node inserted
VIDEO_TOOL = "video"        # the reserved tool name of the node the decoder is
VIDEO_OUTPUT = "output"     # the video node's one param: what the decoder hands out, applied before its cache
VIDEO_OUTPUTS = ("bgr", "gray", "luma")    # luma: the decoder's own plane, a gray left in the stream's range
VIDEO_PRODUCES = "bgr"      # what it hands out unless its output param names another of VIDEO_OUTPUTS
RESCALE_TOOL, RESCALE_PARAM = "rescale", "scale"    # the tool and param a format-1 video node's scale becomes on load
PATH = "path"               # the type the video node's input expects and a selector produces
INPUT = "in"                # every tool's first input; INPUTS declares more
OVERLAYABLE = ("gray", "mask")  # the types the overlay flag is offered on: a single plane the frame can be heated with
LAYOUT_STEP = 100.0         # vertical spacing of a list-built document
OPEN = (0.0, float("inf"))  # where a series node's handles rest while it has no band; without one nothing is gated


class FormatError(ValueError):
    """The file is not a document this module can read."""


class Plate(NamedTuple):
    """How a bake's rows lie on the plate's: plate row = first + increment × row. Plate(0, 1) is the
    plate's own."""
    first: int
    increment: int

    def to_plate(self, row):
        return self.first + self.increment * row

    def from_plate(self, row):
        return max(0, (row - self.first) // self.increment)


@dataclass(frozen=True)
class Bake:
    """A bake as the node that serves it saves it: everything that makes the node a source, so
    nothing need look in the store. `rows` is (first, last) of the plate, `count` the plate's rows,
    `shape` the plane's or () for a series kind."""
    key: str
    kind: str
    series: bool
    rows: tuple
    increment: int
    fps: float
    written_fps: float
    shape: tuple
    count: int

    @classmethod
    def from_dict(cls, d):
        return cls(str(d["key"]), str(d["kind"]), bool(d["series"]), tuple(int(r) for r in d["rows"]), int(d["increment"]),
                   float(d["fps"]), float(d["written_fps"]), tuple(int(x) for x in d["shape"]), int(d["count"]))

    def to_dict(self):
        return {"key": self.key, "kind": self.kind, "series": self.series, "rows": list(self.rows), "increment": self.increment,
                "fps": self.fps, "written_fps": self.written_fps, "shape": list(self.shape), "count": self.count}

    @property
    def plate(self):
        return Plate(self.rows[0], self.increment)

    @property
    def aligned(self):
        """Whether the rows are the plate's: every row from the first to the last, so a document is
        in the same row space served or live."""
        return self.increment == 1 and self.rows == (0, self.count - 1)

    @property
    def written(self):
        """The rows the file holds."""
        return len(range(self.rows[0], self.rows[1] + 1, self.increment))


@dataclass
class Node:
    id: str
    tool: str
    params: dict = field(default_factory=dict)
    pos: tuple = (0.0, 0.0)
    band: tuple | None = None                                       # (lo, hi) kept, of a plane's pixels or a signal's rows; None keeps every value
    mode: str | None = None                                         # BAKED while the node serves its bake; None or LIVE is live
    baked: Bake | None = None                                       # the bake in the store, once there is one; see served()
    extra: dict = field(default_factory=dict, repr=False)            # keys this module does not know
    unresolved: bool = field(default=False, compare=False)          # set by resolve(); not saved


@dataclass
class Wire:
    src: str
    dst: str
    input: str = INPUT


@dataclass
class Problem:
    kind: str       # "type" | "cycle" | "unfed"
    where: str      # a node id, or "src -> dst" for a wire
    text: str


@dataclass
class Document:
    nodes: list = field(default_factory=list)
    wires: list = field(default_factory=list)
    display: str | None = None
    overlay: str | None = None                                      # heated over the displayed frame; None is off
    pinned: str | None = None                                       # the series node the timeline draws; None is none
    video: str | None = None                                      # as written
    extra: dict = field(default_factory=dict, repr=False)
    path: str | None = field(default=None, compare=False)           # where it was loaded from or saved to

    def node(self, nid):
        for n in self.nodes:
            if n.id == nid:
                return n
        raise KeyError(nid)

    def video_node(self):
        return next((n for n in self.nodes if n.tool == VIDEO_TOOL), None)

    def source(self, dst, input=INPUT):
        """The wire into `dst`'s input, or None."""
        return next((w for w in self.wires if w.dst == dst and w.input == input), None)

    def add_node(self, tool, pos=(0.0, 0.0), params=None, id=None):
        """A new node; its id is the tool name, suffixed if taken."""
        ids = {n.id for n in self.nodes}
        nid = id or tool
        k = 2
        while nid in ids:
            nid, k = f"{tool}_{k}", k + 1
        node = Node(nid, tool, dict(params or {}), tuple(float(v) for v in pos))
        self.nodes.append(node)
        return node

    def remove_node(self, nid):
        """Removes the node, every wire into or out of it, and any flag it carried."""
        self.nodes = [n for n in self.nodes if n.id != nid]
        self.wires = [w for w in self.wires if nid not in (w.src, w.dst)]
        if self.display == nid:
            self.display = None
        if self.overlay == nid:
            self.overlay = None
        if self.pinned == nid:
            self.pinned = None

    def connect(self, src, dst, input=INPUT):
        """Wires `src` into `dst`'s input, replacing whatever fed it."""
        self.disconnect(dst, input)
        self.wires.append(Wire(src, dst, input))

    def disconnect(self, dst, input=INPUT):
        self.wires = [w for w in self.wires if not (w.dst == dst and w.input == input)]

    def resolve(self, known):
        """Marks each node whose tool name `known` does not contain; the video node is always known.
        Given the tools themselves, a mapping of name to module, a resolved node's params are laid
        over its tool's DEFAULTS, so a param the file lacks, one the tool gained since it was
        saved, has its value."""
        for n in self.nodes:
            n.unresolved = n.tool != VIDEO_TOOL and n.tool not in known
            tool = known.get(n.tool) if hasattr(known, "get") else None
            if tool is not None:
                n.params = {**getattr(tool, "DEFAULTS", {}), **n.params}

    def folder(self):
        """Where relative paths resolve: the document's folder, else the working directory."""
        return os.path.dirname(os.path.abspath(self.path)) if self.path else os.getcwd()

    def video_path(self):
        """The path to open: relative paths resolve against the document's folder."""
        if self.video is None or os.path.isabs(self.video) or self.path is None:
            return self.video
        return os.path.normpath(os.path.join(self.folder(), self.video))

    def selector(self, nid=None, input=INPUT):
        """The node wired into `nid`'s `input`, by default the video node's, or None."""
        if nid is None:
            v = self.video_node()
            if v is None:
                return None
            nid = v.id
        w = self.source(nid, input)
        return None if w is None else self.node(w.src)

    def to_dict(self):
        return {
            "version": VERSION,
            "video": self.video,
            "display": self.display,
            "overlay": self.overlay,
            **({"pinned": self.pinned} if self.pinned is not None else {}),
            "nodes": [{"id": n.id, "tool": n.tool, "params": n.params, "pos": list(n.pos),
                       **({"band": list(n.band)} if n.band is not None else {}),
                       **({"mode": n.mode} if n.mode is not None else {}),
                       **({"baked": n.baked.to_dict()} if n.baked is not None else {}), **n.extra} for n in self.nodes],
            "wires": [{"from": w.src, "to": w.dst, "input": w.input} for w in self.wires],
            **self.extra,
        }

    @classmethod
    def from_dict(cls, d, known=None):
        v = d.get("version")
        if not isinstance(v, int) or v > VERSION:
            raise FormatError(f"document is format version {v!r}; this module reads up to {VERSION}")
        top = {"version", "video", "display", "overlay", "pinned", "nodes", "wires"}
        node_keys = {"id", "tool", "params", "pos", "band", "mode", "baked"}
        doc = cls(video=d.get("video"), display=d.get("display"), overlay=d.get("overlay"), pinned=d.get("pinned"),
                  extra={k: v for k, v in d.items() if k not in top})
        for nd in d.get("nodes", []):
            if any(n.id == nd["id"] for n in doc.nodes):
                raise FormatError(f"node id {nd['id']!r} appears twice")
            doc.nodes.append(Node(nd["id"], nd["tool"], dict(nd.get("params", {})),
                                  tuple(float(x) for x in nd.get("pos", (0, 0))),
                                  None if nd.get("band") is None else tuple(float(x) for x in nd["band"]),
                                  BAKED if nd.get("mode") == "stale" else nd.get("mode"),    # stale was once saved; it serves
                                  None if nd.get("baked") is None else Bake.from_dict(nd["baked"]),
                                  {k: v for k, v in nd.items() if k not in node_keys}))
        ids = {n.id for n in doc.nodes}
        for wd in d.get("wires", []):
            if wd["from"] not in ids or wd["to"] not in ids:
                raise FormatError(f"wire {wd['from']!r} -> {wd['to']!r} names a node the document lacks")
            doc.wires.append(Wire(wd["from"], wd["to"], wd.get("input", INPUT)))
        doc._lift_scale()
        if known is not None:
            doc.resolve(known)
        return doc

    def _lift_scale(self):
        """A video node carrying a scale, format 1's, loses it, and one under 1 becomes a rescale
        node of that factor between the video node and every node that read it, so what reaches
        each reader is the plane it read before."""
        v = self.video_node()
        if v is None or RESCALE_PARAM not in v.params:
            return
        try:
            s = float(v.params.pop(RESCALE_PARAM))
        except (TypeError, ValueError):
            return
        if not 0.0 < s < 1.0:
            return
        readers = [w for w in self.wires if w.src == v.id]
        node = self.add_node(RESCALE_TOOL, (v.pos[0], v.pos[1] + LAYOUT_STEP / 2), {RESCALE_PARAM: s})
        for w in readers:
            w.src = node.id
        self.wires.append(Wire(v.id, node.id))


def save(doc, path):
    """Writes the document, whole or not at all, and records `path` as where it lives."""
    part = f"{os.fspath(path)}.part"
    try:
        with open(part, "w", encoding="utf-8") as f:
            json.dump(doc.to_dict(), f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(part, path)
    except OSError:
        if os.path.exists(part):
            os.remove(part)
        raise
    doc.path = os.fspath(path)


def load(path, known=None):
    """Reads a document. `known`, if given, is the tool names the registry resolves (see resolve)."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    doc = Document.from_dict(d, known)
    doc.path = os.fspath(path)
    return doc


def _by_name(tools):
    """`tools` as a mapping of name to module, whether given as one or as the modules."""
    return tools if hasattr(tools, "get") else {t.NAME: t for t in tools}


def expects(tool):
    e = getattr(tool, "EXPECTS", None)
    if e is None:
        return None
    return tuple(e) if isinstance(e, (tuple, list, set)) else (e,)


def paths(tool):
    """A tool's path inputs: name to the loader that turns the file into params; empty if none."""
    return dict(getattr(tool, "PATHS", None) or {})


def static(tool):
    """Whether the tool's output is the same at every row, as STATIC declares: the runtime then
    computes it once per key and holds it once, and the monitor counts its run per change, not per row."""
    return bool(getattr(tool, "STATIC", False))


def inputs(tool):
    """A tool's frame inputs after the first, in order: name to the types each expects, as INPUTS
    declares them; empty if none."""
    return {name: tuple(t) if isinstance(t, (tuple, list, set)) else (t,)
            for name, t in (getattr(tool, "INPUTS", None) or {}).items()}


def frame_inputs(tool):
    """Every input `run` reads through `frames`: INPUT first, then each of INPUTS."""
    return [INPUT, *inputs(tool)]


def optional(tool):
    """The frame inputs after the first that may be unwired, as OPTIONAL names them."""
    return tuple(getattr(tool, "OPTIONAL", None) or ())


def inputs_of(doc, tools, nid):
    """[(input name, types it expects or None)]: PATH on the video node, none on a selector, else
    the frame inputs and then each path input."""
    node = doc.node(nid)
    if node.tool == VIDEO_TOOL:
        return [(INPUT, (PATH,))]
    tool = _by_name(tools).get(node.tool)
    if tool is None:
        return [(INPUT, None)]
    if is_selector(tool):
        return []
    return [(INPUT, expects(tool)), *inputs(tool).items()] + [(name, (PATH,)) for name in paths(tool)]


def wants(doc, tools, nid, input=INPUT):
    """What `nid`'s `input` expects; None for an input nothing declares."""
    return dict(inputs_of(doc, tools, nid)).get(input)


def is_selector(tool):
    return getattr(tool, "PRODUCES", None) == PATH and expects(tool) is None


def as_written(path, folder):
    """`path` relative to `folder` when it is under it, so a moved folder still finds it; else absolute."""
    try:
        rel = os.path.relpath(path, folder)
    except ValueError:      # another drive on Windows
        return os.path.abspath(path)
    return rel if not rel.startswith(os.pardir) else os.path.abspath(path)


def pick_path(doc, tools, nid, input=INPUT):
    """Asks the selector wired into `nid`'s `input` which file it means. Returns (path, reason):
    the path, or None and why there is none; (None, "") when nothing is wired there."""
    sel = doc.selector(nid, input)
    if sel is None:
        return None, ""
    tool = _by_name(tools).get(sel.tool)
    if tool is None or not is_selector(tool):
        return None, f"{sel.id} is not a selector"
    try:
        path = tool.select(doc.folder(), dict(sel.params))
    except Exception as e:  # a tool's rule is user code; its failure is a report, not a crash
        return None, f"{sel.id} raised {type(e).__name__}: {e}"
    if path is None:
        return None, f"{sel.id} matched nothing"
    return os.path.normpath(os.path.join(doc.folder(), path)), ""


def pick_video(doc, tools):
    """`pick_path` on the video node, recording the answer in `video` as written. Without a
    selector the answer is `video_path()` and the reason is empty."""
    v = doc.video_node()
    if v is None or doc.selector() is None:
        return doc.video_path(), ""
    path, why = pick_path(doc, tools, v.id)
    if path is not None:
        doc.video = as_written(path, doc.folder())
    return path, why


def produces(doc, tools, nid, _seen=()):
    """The type `nid` hands out, or None: unresolved, a pass-through nothing feeds, or in a cycle."""
    node = doc.node(nid)
    if node.tool == VIDEO_TOOL:
        out = video_output(doc)
        return "gray" if out == "luma" else out
    if served(node):
        return served(node).kind
    p = getattr(_by_name(tools).get(node.tool), "PRODUCES", None)
    if p != "same":
        return p
    w = doc.source(nid)
    if w is None or nid in _seen:
        return None
    return produces(doc, tools, w.src, (*_seen, nid))


LIVE, BAKED = "live", "baked"   # a node's two modes: serving the chain, or the bake it holds; whether the bake is stale is the plan's to say


def served(node):
    """The Bake `node` serves while its mode is BAKED; None for a live node."""
    return node.baked if node.mode == BAKED and node.baked else None


def land(node, bake):
    """Records `bake` as written for `node`, which serves it from here on."""
    node.mode, node.baked = BAKED, bake


def kind_of(doc, tools, nid, _seen=()):
    """The kind the plan gives `nid`: "video", "selector", else the tool's KIND; a KIND of "same"
    is the kind of the node wired into the first input, "frame" under the video node, while nothing
    is wired or in a cycle; a served node's is its bake's. An unresolved tool reads as "frame", as
    a tool that did not say does."""
    node = doc.node(nid)
    if node.tool == VIDEO_TOOL:
        return "video"
    if served(node):
        return "series" if served(node).series else "frame"
    tool = _by_name(tools).get(node.tool)
    if is_selector(tool):
        return "selector"
    kind = getattr(tool, "KIND", "frame")
    if kind != "same":
        return kind
    w = doc.source(nid)
    if w is None or nid in _seen:
        return "frame"
    up = kind_of(doc, tools, w.src, (*_seen, nid))
    return "frame" if up in ("video", "selector") else up


def mode_of(doc, tools, nid):
    """LIVE or BAKED for a node whose tool bakes; None for any other node."""
    if getattr(_by_name(tools).get(doc.node(nid).tool), "bake", None) is None:
        return None
    return BAKED if served(doc.node(nid)) else LIVE


def video_output(doc):
    """What the video node hands out, one of VIDEO_OUTPUTS; "bgr" unless its param says otherwise or with no video node."""
    v = doc.video_node()
    out = VIDEO_PRODUCES if v is None else v.params.get(VIDEO_OUTPUT, VIDEO_PRODUCES)
    return out if out in VIDEO_OUTPUTS else VIDEO_PRODUCES


def from_tools(tools, video=None):
    """The document `play([gray, threshold])` means: the video node first, each tool wired to the
    nearest earlier node producing what it EXPECTS (unwired if none does), laid out top to bottom,
    the flag on the last frame tool the video reaches, else on the video."""
    doc = Document(video=video)
    doc.add_node(VIDEO_TOOL)
    for i, t in enumerate(tools, 1):
        n = doc.add_node(t.NAME, (0.0, i * LAYOUT_STEP), getattr(t, "DEFAULTS", {}))
        if is_selector(t):
            doc.connect(n.id, VIDEO_TOOL)      # a selector reads nothing and feeds the video
            continue
        want = expects(t) or ()
        for earlier in reversed(doc.nodes[:-1]):
            if produces(doc, tools, earlier.id) in want:
                doc.connect(earlier.id, n.id)
                break
    doc.display = doc.nodes[0].id
    for n in doc.nodes[1:]:
        t = _by_name(tools)[n.tool]
        if kind_of(doc, tools, n.id) == "frame" and fed(doc, n.id):
            doc.display = n.id
    return doc


def fed(doc, nid, tools=None):
    """Whether the video, or a served bake, reaches `nid` through every frame input's wires. With `tools`, a node whose
    tool the names do not resolve, or a wire whose types do not fit, breaks the chain: what the
    runtime computes. Without them only the first input is known, and it alone is followed."""
    tools = None if tools is None else _by_name(tools)

    def reaches(nid, stack):
        node = doc.node(nid)
        if node.tool == VIDEO_TOOL or served(node):
            return True
        if nid in stack:
            return False
        names, skip = [INPUT], ()
        if tools is not None:
            tool = tools.get(node.tool)
            if tool is None:
                return False
            names, skip = frame_inputs(tool), optional(tool)
        for name in names:
            w = doc.source(nid, name)
            if w is None and name in skip:
                continue
            if w is None or (tools is not None and not fits(doc, tools, w)) or not reaches(w.src, (*stack, nid)):
                return False
        return True

    return reaches(nid, ())


def fits(doc, tools, wire):
    """Whether the wire's source hands out something its destination expects; a source that hands
    out nothing (unresolved, an unfed pass-through) does not fit."""
    tools = _by_name(tools)
    got, want = produces(doc, tools, wire.src), wants(doc, tools, wire.dst, wire.input)
    return got is not None and (want is None or got in want)


def validate(doc, tools):
    """Every wire whose destination does not expect what its source produces, every cycle, and every
    node with an input nothing feeds; the video node's input and a selector, which has none, are
    never unfed. Reports; never refuses. Needs the tools for the types and the unfed
    check; the cycle check reads the document alone."""
    tools = _by_name(tools)
    out = []
    for w in doc.wires:
        got, want = produces(doc, tools, w.src), wants(doc, tools, w.dst, w.input)
        if got is not None and want is not None and got not in want:
            out.append(Problem("type", f"{w.src} -> {w.dst}", f"{w.dst} expects {want!r} but {w.src} produces {got!r}"))
    state = {}      # id -> 1 on the stack, 2 finished

    def walk(nid, stack):
        state[nid] = 1
        for w in doc.wires:
            if w.src == nid:
                if state.get(w.dst) == 1:
                    cycle = stack[stack.index(w.dst):] + [w.dst]
                    out.append(Problem("cycle", w.dst, " -> ".join(cycle)))
                elif w.dst not in state:
                    walk(w.dst, stack + [w.dst])
        state[nid] = 2

    for n in doc.nodes:
        if n.id not in state:
            walk(n.id, [n.id])
    for n in doc.nodes:
        tool = tools.get(n.tool)
        if n.tool == VIDEO_TOOL or is_selector(tool):
            continue
        for name in [INPUT] if tool is None else frame_inputs(tool):
            if doc.source(n.id, name) is None and name not in optional(tool):
                out.append(Problem("unfed", n.id, f"{n.id} has no input" if name == INPUT else f"{n.id}'s {name} is unfed"))
    return out
