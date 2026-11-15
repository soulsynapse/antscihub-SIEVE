"""The plan: what the runtime will compute, read off the document and the tools alone.

`plan()` is pure: the same document, tools, video key and cut files give the same plan, with no decoder,
thread, memo or disk in sight, so a test or `python -m sieve_player doc.json --plan` reads it as a table. The
Graph calls it at every sync and holds the result under its lock; nothing here is touched after it is built.
"""
import hashlib
import json
from dataclasses import dataclass, field

from .document import (INPUT, OVERLAYABLE, VIDEO_TOOL, fed, fits, frame_inputs, is_selector, kind_of, optional, produces,
                       static, video_output, wants)


def _key(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def base_key(footage, output):
    """The video node's key: the footage, as decoder.footage_print says which it is, and what the
    decoder hands out of it. No path is in it, so the keys are a file's wherever it lies."""
    return _key("video", footage, output)


@dataclass
class Entry:
    """One node as the plan sees it."""
    tool: object
    kind: str           # "video" | "frame" | "series" | "selector"
    params: dict
    band: tuple | None  # (lo, hi): what the node's plane, or signal, keeps; see document
    src: str | None     # the node its first input's wire names
    key: str
    raw_key: str         # the key without the band: what the memo holds
    src_key: str | None  # what its run() sees as frames.key: every frame input's key, hashed together when there are several
    fed: bool
    srcs: dict          # frame input name -> the node wired into it, or None
    static: bool        # the same output at every row, declared or inherited from every input: memoized under the raw key alone, row None
    standing: str = ""  # why the node does not run, as the plan sees it; "" when it runs
    types: dict = field(default_factory=dict)   # frame input name -> what the node wired into it produces, or None
    file: tuple | None = None                   # (path, footage print) of the file the node serves in place of its run, or None
    piece: str | None = None                    # the nearest node upstream whose tool cuts, by its cut_file: the node's inputs are of that node's piece of the plate; None for the plate
    steps: bool = False                         # a chain node the walk steps a row at a time; a chain node without it runs whole
    whole_by: str | None = None                 # a stepping tool run whole: the chain node that ended the prefix; None on every other node


@dataclass
class Plan:
    entries: dict = field(default_factory=dict)   # node id -> Entry
    heads: list = field(default_factory=list)     # the series nodes that run on the stack: those fed by the walked node
    chain: list = field(default_factory=list)     # the heads and each fed series node on from a chain node, in run order
    unrun: list = field(default_factory=list)     # every series node not in the chain; its standing says why
    shown: str | None = None                      # the display flag, when it names a node
    over: str | None = None                       # the overlay flag, when it names a one-plane node

    @property
    def walk(self):
        return walked(self.entries, self.chain, self.shown)

    @property
    def fold(self):
        return shared_fold(self.entries, self.heads)


def walked(entries, chain, shown):
    """The node the worker computes over the window: what the chain's head reads, else what is
    shown; None when the head is not fed, so its tool never sees a type it does not expect."""
    if not chain:
        return shown
    e = entries[chain[0]]
    return e.src if e.fed else None


def shared_fold(entries, heads):
    """The heads' fold() when every one of them has the same, else None: the stack then holds the
    rows as they are and each head folds them at run."""
    folds = {id(f): f for f in (getattr(entries[s].tool, "fold", None) for s in heads)}
    return next(iter(folds.values())) if len(folds) == 1 else None


def facts(p, pinned):
    """The Plan `p` as a sync event carries it, in plain values a dump can write: per node its kind,
    whether it is fed, static and served, whether the walk steps it and the chain node that made a
    stepping tool run whole, and the node each input reads; beside them the chain in run order, the
    walked, shown and overlaid nodes, and `pinned`, the document's. The player's selection is the
    stream's to add, see stream.Emitter.sync()."""
    return {"nodes": {nid: {"kind": e.kind, "fed": e.fed, "static": e.static, "served": e.file is not None,
                            "steps": e.steps, "whole_by": e.whole_by, "reads": dict(e.srcs)} for nid, e in p.entries.items()},
            "chain": list(p.chain), "walk": p.walk, "shown": p.shown, "over": p.over,
            "pinned": list(pinned)}


def plan(doc, tools, base, cut_files=None):
    """The plan for `doc` under `tools`, name to module, with `base` the video node's key and
    `cut_files`, node to (path, footage print), the file each cutting node's tool says holds what
    the node hands out. A raw key names what a tool computes from, so the memo holds under it; the
    key adds the band, which is applied on read, so what downstream sees is keyed by it and the
    node's own run is not. A node of `cut_files` that reads the video node itself, or a node that
    serves a file, serves its file: it reads nothing, and its key is the one a document opened on that file gives its video node, so
    everything below it is keyed as that document's is. A node reads one piece of the plate: one
    whose inputs are of two, the plate among them, is not fed, nor is anything that reads it, and
    its standing says which. A chain node is stepped when its tool steps and everything it reads on
    the chain is stepped; the first node that runs whole ends the prefix for every node after it,
    and a stepping tool so ended names that node in `whole_by`."""
    cut_files = cut_files or {}
    keys, raw_keys, pieces = {}, {}, {}

    def file_of(nid, stack=()):
        w = doc.source(nid)
        if w is None or nid not in cut_files or nid in stack:
            return None
        whole = doc.node(w.src).tool == VIDEO_TOOL or file_of(w.src, (*stack, nid)) is not None
        return cut_files[nid] if whole else None

    def wired(nid):
        tool = tools.get(doc.node(nid).tool)
        names = [INPUT] if tool is None or is_selector(tool) else frame_inputs(tool)
        return {name: (w.src if (w := doc.source(nid, name)) else None) for name in names}

    def sources(nid):
        return {name: None for name in wired(nid)} if file_of(nid) else wired(nid)

    def static_of(nid, stack=()):
        """Declared by the tool, or inherited: a frame node fed on every input by static nodes is
        static in fact, since no frame tool reads the row itself. A served node reads its file per row."""
        tool = tools.get(doc.node(nid).tool)
        if static(tool) or tool is None or kind_of(doc, tools, nid) != "frame" or file_of(nid) or nid in stack:
            return static(tool)
        srcs = sources(nid).values()
        return bool(srcs) and all(s is not None and static_of(s, (*stack, nid)) for s in srcs)

    def up_key(nid, stack=()):
        ups = [key_of(src, stack) if src is not None and src not in stack else "none" for src in sources(nid).values()]
        return ups[0] if len(ups) == 1 else _key(*ups)

    def key_of(nid, stack=()):
        if nid not in keys:
            node = doc.node(nid)
            if node.tool == VIDEO_TOOL:
                keys[nid] = raw_keys[nid] = base
                return base
            raw = (base_key(file_of(nid)[1], video_output(doc)) if file_of(nid)
                   else _key(up_key(nid, (*stack, nid)), node.tool, json.dumps(node.params, sort_keys=True)))
            raw_keys[nid] = raw
            keys[nid] = raw if node.band is None else _key(raw, node.band)
        return keys[nid]

    def pieces_of(nid, stack=()):
        """Input name -> the cutting node that input is of, None for the plate, over the inputs wired."""
        if nid not in pieces:
            out = {}
            for name, src in wired(nid).items():
                if src is None or src in stack:
                    continue
                if getattr(tools.get(doc.node(src).tool), "cut_file", None) is not None:
                    out[name] = src
                else:
                    out[name] = next(iter(pieces_of(src, (*stack, nid)).values()), None)
            pieces[nid] = out
        return pieces[nid]

    def said(piece):
        return "the plate" if piece is None else piece

    crossings = {}
    for n in doc.nodes:
        of = pieces_of(n.id)
        if len(set(of.values())) > 1:
            (a, pa), (b, pb) = next(((a, pa), (b, pb)) for a, pa in of.items() for b, pb in of.items() if pa != pb)
            crossings[n.id] = f"reads across a cut: {a} is of {said(pa)}, {b} of {said(pb)}"
    blocked, more = set(), set(crossings)
    while more:
        blocked |= more
        more = {n.id for n in doc.nodes if n.id not in blocked and any(s in blocked for s in wired(n.id).values())}
    entries, series = {}, []
    for n in doc.nodes:
        tool = tools.get(n.tool)
        kind = kind_of(doc, tools, n.id)      # a selector answers a path, once, before the decoder; never a row
        srcs = sources(n.id)
        src = srcs[INPUT]
        entries[n.id] = Entry(tool, kind, dict(n.params), n.band, src, key_of(n.id), raw_keys[n.id],
                              up_key(n.id) if src else None, fed(doc, n.id, tools) and n.id not in blocked, srcs, static_of(n.id),
                              types={name: produces(doc, tools, s) if s else None for name, s in srcs.items()},
                              file=file_of(n.id), piece=next(iter(pieces_of(n.id).values()), None))
        if kind == "series":
            series.append(n.id)
    roots = [s for s in series if entries[s].src is None or entries[entries[s].src].kind != "series"]
    heads = [s for s in roots if entries[s].src == entries[roots[0]].src and (entries[s].fed or s == roots[0])] if roots else []
    chain = list(heads)
    for nid in chain:
        chain += [s for s in series if entries[s].src == nid and entries[s].fed and s not in chain]
    enders = {}
    for nid in chain:
        e = entries[nid]
        own = getattr(e.tool, "step", None) is None
        enders[nid] = nid if own else enders.get(e.src)
        e.steps, e.whole_by = enders[nid] is None, None if own else enders[nid]
    for nid, e in entries.items():
        e.standing = crossings.get(nid) or _standing(doc, tools, entries, heads, chain, nid)
    over = doc.overlay if doc.overlay in entries and produces(doc, tools, doc.overlay) in OVERLAYABLE else None
    return Plan(entries, heads, chain, [s for s in series if s not in chain], doc.display if doc.display in entries else None, over)


def _standing(doc, tools, entries, heads, chain, nid):
    e = entries[nid]
    if e.kind in ("video", "selector") or e.tool is None or e.file is not None:
        return ""
    for name, src in e.srcs.items():
        if src is None:
            return "" if name in optional(e.tool) else f"{name} is unwired"
        if not fits(doc, tools, doc.source(nid, name)):
            got, want = produces(doc, tools, src), wants(doc, tools, nid, name)
            if got is None:
                return f"{name} waits on {src}"
            return f"{name} expects {' | '.join(want)}, {src} produces {got}"
        if not entries[src].fed and entries[src].kind != "series":
            return f"{name} waits on {src}"
    if e.kind == "series" and nid not in chain:
        if entries[e.src].kind == "series":
            return f"in waits on {e.src}"
        return f"unrun: reads {e.src}; the walk is {entries[heads[0]].src}, which {heads[0]} reads"
    return "" if e.fed else "in a cycle"
