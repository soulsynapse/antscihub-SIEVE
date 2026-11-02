"""The plan: what the runtime will compute, read off the document and the tools alone.

`plan()` is pure: the same document, tools and video key give the same plan, with no decoder, thread
or memo in sight, so a test or `python -m sieve_player doc.json --plan` reads it as a table. The Graph calls
it at every sync and holds the result under its lock; nothing here is touched after it is built.
"""
import hashlib
import json
from dataclasses import dataclass, field

from .document import (INPUT, OVERLAYABLE, VIDEO_TOOL, fed, fits, frame_inputs, is_selector, optional, produces, static,
                       wants)


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


@dataclass
class Plan:
    entries: dict = field(default_factory=dict)   # node id -> Entry
    heads: list = field(default_factory=list)     # the series nodes that run on the stack: those fed by the walked node
    chain: list = field(default_factory=list)     # the heads and each fed series node on from a chain node, in run order
    unrun: list = field(default_factory=list)     # every series node not in the chain; its standing says why
    shown: str | None = None                      # the display flag, when it names a node
    over: str | None = None                       # the overlay flag, when it names a one-plane node


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
    is applied on read, so what downstream sees is keyed by it and the node's own run is not."""
    keys, raw_keys = {}, {}

    def sources(nid):
        tool = tools.get(doc.node(nid).tool)
        names = [INPUT] if tool is None or is_selector(tool) else frame_inputs(tool)
        return {name: (w.src if (w := doc.source(nid, name)) else None) for name in names}

    def up_key(nid, stack=()):
        ups = [key_of(src, stack) if src is not None and src not in stack else "none" for src in sources(nid).values()]
        return ups[0] if len(ups) == 1 else _key(*ups)

    def key_of(nid, stack=()):
        if nid not in keys:
            node = doc.node(nid)
            if node.tool == VIDEO_TOOL:
                keys[nid] = raw_keys[nid] = base
            else:
                raw_keys[nid] = _key(up_key(nid, (*stack, nid)), node.tool, json.dumps(node.params, sort_keys=True))
                keys[nid] = raw_keys[nid] if node.band is None else _key(raw_keys[nid], node.band)
        return keys[nid]

    entries, series = {}, []
    for n in doc.nodes:
        tool = tools.get(n.tool)
        if n.tool == VIDEO_TOOL:
            kind = "video"
        elif is_selector(tool):
            kind = "selector"       # answers a path, once, before the decoder; never a row
        else:
            kind = getattr(tool, "KIND", "frame")
        srcs = sources(n.id)
        src = srcs[INPUT]
        entries[n.id] = Entry(tool, kind, dict(n.params), n.band, src, key_of(n.id), raw_keys[n.id],
                              up_key(n.id) if src else None, fed(doc, n.id, tools), srcs, static(tool),
                              types={name: produces(doc, tools, s) if s else None for name, s in srcs.items()})
        if kind == "series":
            series.append(n.id)
    roots = [s for s in series if entries[s].src is None or entries[entries[s].src].kind != "series"]
    heads = [s for s in roots if entries[s].src == entries[roots[0]].src and (entries[s].fed or s == roots[0])] if roots else []
    chain = list(heads)
    for nid in chain:
        chain += [s for s in series if entries[s].src == nid and entries[s].fed and s not in chain]
    for nid, e in entries.items():
        e.standing = _standing(doc, tools, entries, heads, chain, nid)
    over = doc.overlay if doc.overlay in entries and produces(doc, tools, doc.overlay) in OVERLAYABLE else None
    return Plan(entries, heads, chain, [s for s in series if s not in chain],
                doc.display if doc.display in entries else None, over)


def _standing(doc, tools, entries, heads, chain, nid):
    e = entries[nid]
    if e.kind in ("video", "selector") or e.tool is None:
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
