"""The saved form of a pipeline. `spec/document.md` is the spec.

Nodes, wires, the display flag and the video path; nothing of the canvas's view or the runtime's
memo. This module imports neither Qt nor cv2 nor any other part of the player. Where a function
needs a tool's facets (EXPECTS, PRODUCES) it is handed the tools, as a mapping of name to module
or as the modules themselves; the document stores only names.

The video is a node like any other, with the reserved tool name VIDEO_TOOL, so that wires can name
it. Its path is kept on the document, not in the node's params, so it can be stored as written and
resolved against the document's folder on load.
"""
import json
import os
from dataclasses import dataclass, field

VERSION = 1
VIDEO_TOOL = "video"        # the reserved tool name of the node the decoder is
VIDEO_PRODUCES = "bgr"
INPUT = "in"                # every tool today has one input; wires name it so fan-in costs nothing later
LAYOUT_STEP = 100.0         # vertical spacing of a list-built document


class FormatError(ValueError):
    """The file is not a document this module can read."""


@dataclass
class Node:
    id: str
    tool: str
    params: dict = field(default_factory=dict)
    pos: tuple = (0.0, 0.0)
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
    video: str | None = None                                        # as written
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
        """Removes the node, every wire into or out of it, and the flag if it carried it."""
        self.nodes = [n for n in self.nodes if n.id != nid]
        self.wires = [w for w in self.wires if nid not in (w.src, w.dst)]
        if self.display == nid:
            self.display = None

    def connect(self, src, dst, input=INPUT):
        """Wires `src` into `dst`'s input, replacing whatever fed it."""
        self.disconnect(dst, input)
        self.wires.append(Wire(src, dst, input))

    def disconnect(self, dst, input=INPUT):
        self.wires = [w for w in self.wires if not (w.dst == dst and w.input == input)]

    def resolve(self, known):
        """Marks each node whose tool name `known` does not contain; the video node is always known."""
        for n in self.nodes:
            n.unresolved = n.tool != VIDEO_TOOL and n.tool not in known

    def video_path(self):
        """The path to open: relative paths resolve against the document's folder."""
        if self.video is None or os.path.isabs(self.video) or self.path is None:
            return self.video
        return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(self.path)), self.video))

    def to_dict(self):
        return {
            "version": VERSION,
            "video": self.video,
            "display": self.display,
            "nodes": [{"id": n.id, "tool": n.tool, "params": n.params, "pos": list(n.pos), **n.extra} for n in self.nodes],
            "wires": [{"from": w.src, "to": w.dst, "input": w.input} for w in self.wires],
            **self.extra,
        }

    @classmethod
    def from_dict(cls, d, known=None):
        v = d.get("version")
        if not isinstance(v, int) or v > VERSION:
            raise FormatError(f"document is format version {v!r}; this module reads up to {VERSION}")
        top = {"version", "video", "display", "nodes", "wires"}
        node_keys = {"id", "tool", "params", "pos"}
        doc = cls(video=d.get("video"), display=d.get("display"), extra={k: v for k, v in d.items() if k not in top})
        for nd in d.get("nodes", []):
            if any(n.id == nd["id"] for n in doc.nodes):
                raise FormatError(f"node id {nd['id']!r} appears twice")
            doc.nodes.append(Node(nd["id"], nd["tool"], dict(nd.get("params", {})),
                                  tuple(float(x) for x in nd.get("pos", (0, 0))),
                                  {k: v for k, v in nd.items() if k not in node_keys}))
        ids = {n.id for n in doc.nodes}
        for wd in d.get("wires", []):
            if wd["from"] not in ids or wd["to"] not in ids:
                raise FormatError(f"wire {wd['from']!r} -> {wd['to']!r} names a node the document lacks")
            doc.wires.append(Wire(wd["from"], wd["to"], wd.get("input", INPUT)))
        if known is not None:
            doc.resolve(known)
        return doc


def save(doc, path):
    """Writes the document and records `path` as where it lives."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc.to_dict(), f, indent=2, ensure_ascii=False)
        f.write("\n")
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


def produces(doc, tools, nid, _seen=()):
    """The type `nid` hands out, or None: unresolved, a pass-through nothing feeds, or in a cycle."""
    node = doc.node(nid)
    if node.tool == VIDEO_TOOL:
        return VIDEO_PRODUCES
    p = getattr(_by_name(tools).get(node.tool), "PRODUCES", None)
    if p != "same":
        return p
    w = doc.source(nid)
    if w is None or nid in _seen:
        return None
    return produces(doc, tools, w.src, (*_seen, nid))


def from_tools(tools, video=None):
    """The document `play([gray, threshold])` means: the video node first, each tool wired to the
    nearest earlier node producing what it EXPECTS (unwired if none does), laid out top to bottom,
    the flag on the last frame tool the video reaches, else on the video."""
    doc = Document(video=video)
    doc.add_node(VIDEO_TOOL)
    for i, t in enumerate(tools, 1):
        n = doc.add_node(t.NAME, (0.0, i * LAYOUT_STEP), getattr(t, "DEFAULTS", {}))
        want = expects(t) or ()
        for earlier in reversed(doc.nodes[:-1]):
            if produces(doc, tools, earlier.id) in want:
                doc.connect(earlier.id, n.id)
                break
    doc.display = doc.nodes[0].id
    for n in doc.nodes[1:]:
        if getattr(_by_name(tools)[n.tool], "KIND", "frame") == "frame" and fed(doc, n.id):
            doc.display = n.id
    return doc


def fed(doc, nid, tools=None):
    """Whether the video reaches `nid` through its wires. With `tools`, a node whose tool the names
    do not resolve, or a wire whose types do not fit, breaks the chain: what the runtime computes."""
    tools = None if tools is None else _by_name(tools)
    seen = set()
    while nid not in seen:
        node = doc.node(nid)
        if node.tool == VIDEO_TOOL:
            return True
        seen.add(nid)
        w = doc.source(nid)
        if w is None:
            return False
        if tools is not None:
            tool = tools.get(node.tool)
            if tool is None or not fits(doc, tools, w):
                return False
        nid = w.src
    return False


def fits(doc, tools, wire):
    """Whether the wire's source hands out something its destination expects; a source that hands
    out nothing (unresolved, an unfed pass-through) does not fit."""
    tools = _by_name(tools)
    got, want = produces(doc, tools, wire.src), expects(tools.get(doc.node(wire.dst).tool))
    return got is not None and (want is None or got in want)


def validate(doc, tools):
    """Every wire whose destination does not expect what its source produces, every cycle, and every
    node with an input nothing feeds. Reports; never refuses. Needs the tools for the types; the
    other two checks read the document alone."""
    tools = _by_name(tools)
    out = []
    for w in doc.wires:
        got, want = produces(doc, tools, w.src), expects(tools.get(doc.node(w.dst).tool))
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
        if n.tool != VIDEO_TOOL and doc.source(n.id) is None:
            out.append(Problem("unfed", n.id, f"{n.id} has no input"))
    return out
