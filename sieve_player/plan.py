"""The plan: what the runtime will compute, read off the document and the tools alone.

`plan()` is pure: the same document, tools and video key give the same plan, with no decoder, thread
or memo in sight, so a test or `python -m sieve_player doc.json --plan` reads it as a table. The Graph calls
it at every sync and holds the result under its lock; nothing here is touched after it is built.
"""
import hashlib
import json
from dataclasses import dataclass, field

from .document import (INPUT, OVERLAYABLE, VIDEO_TOOL, aligned, fed, fits, frame_inputs, is_selector, kind_of, optional,
                       produces, served, static, wants)


def _key(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def base_key(path, output, scale):
    """The video node's key: the file and what the decoder hands out of it."""
    return _key("video", path, output, scale)


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
    static: bool        # the same output at every row: memoized under the raw key alone, row None
    standing: str = ""  # why the node does not run, as the plan sees it; "" when it runs
    types: dict = field(default_factory=dict)   # frame input name -> what the node wired into it produces, or None
    axis: str | None = None                     # the served, unaligned bake at or upstream of the node, whose rows it is in; None in the plate's
    bake: dict | None = None                    # the bake the node serves (document.served), or None
    off: bool = False                           # in another row space than the display: not fed, the standing says so


@dataclass
class Plan:
    entries: dict = field(default_factory=dict)   # node id -> Entry
    heads: list = field(default_factory=list)     # the series nodes that run on the stack: those fed by the walked node
    chain: list = field(default_factory=list)     # the heads and each fed series node on from a chain node, in run order
    unrun: list = field(default_factory=list)     # every series node not in the chain; its standing says why
    shown: str | None = None                      # the display flag, when it names a node
    over: str | None = None                       # the overlay flag, when it names a one-plane node
    axis: str | None = None                       # the served, unaligned bake the display is behind: the document's row space is its file's
    rows: tuple | None = None                     # (count, fps) of that file; None in the plate's space, where the decoder's are
    stale: set = field(default_factory=set)       # served nodes whose live key is not the key they were baked under


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


def plan(doc, tools, base):
    """The plan for `doc` under `tools`, name to module, with `base` the video node's key. A raw
    key names what a tool computes from, so the memo holds under it; the key adds the band, which
    is applied on read, so what downstream sees is keyed by it and the node's own run is not. A
    served node (document.served) is a source: fed with nothing wired in, keyed by its bake, and
    its live key, what the chain would give it, is kept beside to say whether it is stale. The row
    axis is the bake the display flag is behind when that bake is not aligned with the plate, else
    the plate's; a node in the other space is not fed, its standing saying so."""
    keys, raw_keys, live_keys = {}, {}, {}

    def bake_of(nid):
        return served(doc.node(nid))

    def sources(nid, live=False):
        tool = tools.get(doc.node(nid).tool)
        names = [INPUT] if tool is None or is_selector(tool) else frame_inputs(tool)
        if bake_of(nid) and not live:
            return {name: None for name in names}
        return {name: (w.src if (w := doc.source(nid, name)) else None) for name in names}

    def up_key(nid, stack=(), live=False):
        ups = [key_of(src, stack, live) if src is not None and src not in stack else "none" for src in sources(nid, live).values()]
        return ups[0] if len(ups) == 1 else _key(*ups)

    def key_of(nid, stack=(), live=False):
        held = live_keys if live else keys
        if nid not in held:
            node = doc.node(nid)
            if node.tool == VIDEO_TOOL:
                held[nid] = base
                if not live:
                    raw_keys[nid] = base
            elif bake_of(node.id) and not live:
                # hashed, not the bake's key itself: the file is not the chain, in its rows or its bytes,
                # so nothing memoized under the live key is served for it
                keys[nid] = raw_keys[nid] = _key("served", bake_of(nid)["key"])
            else:
                raw = _key(up_key(nid, (*stack, nid), live), node.tool, json.dumps(node.params, sort_keys=True))
                if not live:
                    raw_keys[nid] = raw
                held[nid] = raw if node.band is None else _key(raw, node.band)
        return held[nid]

    def axis_of(nid, stack=()):
        """The nearest served, unaligned bake at or upstream of `nid`, or None."""
        b = bake_of(nid)
        if b and not aligned(b):
            return nid
        if nid in stack:
            return None
        for src in sources(nid).values():
            if src is not None and (a := axis_of(src, (*stack, nid))) is not None:
                return a
        return None

    axis = axis_of(doc.display) if doc.display in {n.id for n in doc.nodes} else None
    rows = None
    if axis is not None:
        b = bake_of(axis)
        lo, hi, inc = int(b["rows"][0]), int(b["rows"][1]), int(b["increment"])
        rows = (len(range(lo, hi + 1, inc)), float(b["written_fps"]))
    entries, series, stale = {}, [], set()
    for n in doc.nodes:
        tool = tools.get(n.tool)
        kind = kind_of(doc, tools, n.id)      # a selector answers a path, once, before the decoder; never a row
        srcs = sources(n.id)
        src = srcs[INPUT]
        off = kind not in ("video", "selector") and axis_of(n.id) != axis
        entries[n.id] = Entry(tool, kind, dict(n.params), n.band, src, key_of(n.id), raw_keys[n.id],
                              up_key(n.id) if src else None, fed(doc, n.id, tools) and not off, srcs, static(tool),
                              types={name: produces(doc, tools, s) if s else None for name, s in srcs.items()},
                              axis=axis_of(n.id), off=off, bake=bake_of(n.id))
        if bake_of(n.id) and key_of(n.id, live=True) != bake_of(n.id)["key"]:
            stale.add(n.id)
        if kind == "series":
            series.append(n.id)
    roots = [s for s in series if entries[s].src is None or entries[entries[s].src].kind != "series"]
    roots.sort(key=lambda s: entries[s].bake is None)      # a served series node heads the chain from its file, before any walked head
    heads = [s for s in roots if entries[s].src == entries[roots[0]].src and (entries[s].fed or s == roots[0])] if roots else []
    chain = list(heads)
    for nid in chain:
        chain += [s for s in series if entries[s].src == nid and entries[s].fed and s not in chain]
    for nid, e in entries.items():
        e.standing = _standing(doc, tools, entries, heads, chain, nid, axis)
    over = doc.overlay if doc.overlay in entries and produces(doc, tools, doc.overlay) in OVERLAYABLE else None
    return Plan(entries, heads, chain, [s for s in series if s not in chain],
                doc.display if doc.display in entries else None, over, axis, rows, stale)


def _standing(doc, tools, entries, heads, chain, nid, axis=None):
    e = entries[nid]
    if e.kind in ("video", "selector") or e.tool is None:
        return ""
    if e.off:
        where = "in the plate's" if axis is None else f"behind {axis}"
        return f"in {'the plate' if e.axis is None else e.axis}'s row space; the display is {where}"
    if served(doc.node(nid)):
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
        if entries[heads[0]].src is None:
            return f"unrun: reads {e.src}; {heads[0]} heads the chain from its bake"
        return f"unrun: reads {e.src}; the walk is {entries[heads[0]].src}, which {heads[0]} reads"
    return "" if e.fed else "in a cycle"
