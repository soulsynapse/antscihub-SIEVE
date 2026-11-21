"""The plan: what the runtime will compute, read off the document and the tools alone.

`plan()` is pure in the document, the tools, the video key and what `cut_file` and `cut_result` answer, with no decoder,
thread, memo or disk of its own in sight, so a test or `python -m sieve_player doc.json --plan` reads it as a table. The
Graph calls it at every sync and holds the result under its lock; nothing here is touched after it is built.
"""
import hashlib
import json
from dataclasses import dataclass, field

from .cut import Record
from .document import INPUT, VIDEO_TOOL, fed, fits, frame_inputs, kind_of, produces, video_output, wants
from .registry import cuts as tool_cuts
from .registry import computed, cut_by, cut_extents_of, fold_of, is_selector, key_params_of, optional, paths, reach_of, serves_cut_file, static, steps
from .wire import overlaid


FED_ABSENT = "a gated-out row is absent"     # in the key of a series node another feeds: what it is handed at a row that one's band shuts out


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
    static: bool        # the same output at every row, declared or inherited from every input: memoized with row None, one value a cut
    standing: str = ""  # why the node does not run, as the plan sees it; "" when it runs
    types: dict = field(default_factory=dict)   # frame input name -> what the node wired into it produces, or None
    file: tuple | None = None                   # (path, footage print) of the file the node serves in place of its run, or None
    cuts: tuple = ()                            # the cuts the node's output is of, a cut.Record each: the footage's own where no cutting node is above it
    reads: tuple = ()                           # the cuts its inputs are of: its own, but for a cutting node, whose cuts are made from them
    reach: tuple = (None, None)                 # (rows before, rows after) a row that the node's result there reads, through everything above it; None a side without bound
    steps: bool = False                         # a chain node the walk steps a row at a time; a chain node without it runs whole
    whole_by: str | None = None                 # a stepping tool run whole: the chain node that ended the prefix; None on every other node
    produces: str | None = None                 # the type the node hands out, of wire.TYPES; None for one unresolved or that nothing feeds
    computed: dict = field(default_factory=dict)   # of params, those the tool's computing is handed and the key holds


@dataclass
class Plan:
    entries: dict = field(default_factory=dict)   # node id -> Entry
    heads: list = field(default_factory=list)     # the series nodes that run on a stack: those fed by a walked node
    chain: list = field(default_factory=list)     # the heads and each fed series node on from a chain node, in run order
    unrun: list = field(default_factory=list)     # every series node not in the chain nor a timed Walk's; its standing says why
    shown: str | None = None                      # the display flag, when it names a node
    over: str | None = None                       # the overlay flag, when it names a one-plane node
    timed: list = field(default_factory=list)     # a Walk for each extent cut in time that heads read: none of it on `chain`, and the window walks none of it

    @property
    def walk(self):
        """The first of `walks`; with no chain, what is shown."""
        return walked(self.entries, self.chain, self.shown)

    @property
    def walks(self):
        """Each node a fed head reads, in the heads' order: every node a walk of this plan stacks."""
        out = []
        for h in self.heads:
            if self.entries[h].fed and self.entries[h].src not in out:
                out.append(self.entries[h].src)
        return out

    @property
    def fold(self):
        """The fold the heads reading `walk` share, or None."""
        return self.fold_for(self.walk)

    def fold_for(self, nid):
        """The fold the heads reading `nid` share, or None."""
        return shared_fold(self.entries, [h for h in self.heads if self.entries[h].src == nid])

    def of(self, walk):
        """This plan with `walk`, one of `timed`, for its heads and chain: what a walk of one of its cuts runs under."""
        return Plan(self.entries, walk.heads, walk.chain, [], self.shown, self.over)

    def parts(self):
        """This plan as a Plan a walked node, in the order of `walks`: the heads reading it and what
        is fed on from them, so each part has one walk and one fold; this plan alone where it has
        one walked node or none."""
        walks = self.walks
        if len(walks) < 2:
            return [self]
        root = {}
        for nid in self.chain:
            root[nid] = self.entries[nid].src if nid in self.heads else root.get(self.entries[nid].src)
        return [Plan(self.entries, [h for h in self.heads if root[h] == w], [n for n in self.chain if root[n] == w], [], self.shown, self.over)
                for w in walks]


@dataclass
class Walk:
    """The series nodes reading the walked nodes of one extent whose cuts are cuts in time, walked
    over each of `cuts` alone: `heads` read those nodes, and `chain` is they and what is fed on from
    them, in run order, as Plan's are."""
    cuts: tuple
    heads: list
    chain: list


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
    folds = {id(f): f for f in (fold_of(entries[s].tool) for s in heads)}
    return next(iter(folds.values())) if len(folds) == 1 else None


def walked_keys(p):
    """What a walk of the Plan `p` computes under: each chain node's key."""
    return {nid: p.entries[nid].key for nid in p.chain}


def stands(began, p):
    """Whether a job begun under `began`, node to key as walked_keys gave them, stands under the
    Plan `p`: every node of it is on `p`'s chain under the key it began under, whatever else of the
    document has changed."""
    now = walked_keys(p)
    return all(now.get(nid) == key for nid, key in began.items())


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


def plan(doc, tools, base, cut_file=None, cut_result=None, footage=None):
    """The plan for `doc` under `tools`, name to module, with `base` the video node's key,
    `footage` what the cuts' records say they are of, `base` with none, `cut_result(nid, key, within)`
    answering the result a cutting node reads on its CUT_BY wire over `within`, one of the cuts it
    reads, its rows counted from that cut's first, `key` that of the node wired there and None with
    none, the answer None where no such result is held, and
    `cut_file(nid, up)` answering (path, footage print) of the file that holds a cutting node's cut
    of the footage it reads, or None: `up` is that footage as the node above answered, None for the
    video. It is asked only of a node whose tool cuts, has the cut_file facet and that reads the video
    node or a node that serves a file, and only such a node serves one; with no `cut_file` none
    does. A str for an answer is why a node that is to serve a file has none: the node is not fed,
    nor is anything that reads it, and the str is its standing, so what a document computes is
    never one thing with a file in the store and another without. A raw key names what a tool computes from, so the memo holds under it; the key adds the
    band, which is applied on read, so what downstream sees is keyed by it and the node's own run
    is not. Of a node's params the raw key holds those its tool's computing is handed, the
    registry's `computed`, or what its tool's `key_params` answers of them where it has one that
    does not raise. A node that serves its file reads nothing, and its key is the one a document opened on
    that file gives its video node, so everything below it is keyed as that document's is. A node that cuts
    in its rows alone enters no key below it: what reads it is keyed by what it reads. A node's cuts are its inputs', and a cutting node's are made from them, one for
    each extent its tool's `cut_extents` answers of its params and of `cut_result` over each cut it
    reads, the rows it answers of a result over a cut in time lifted by that cut's first row. A cutting node
    is refused, saying why, where its CUT_BY input is wired beside a
    path input, and where the node wired into it reads it; one whose CUT_BY wire's result is not held
    cuts no cut and waits on that node's walk, and one with neither wired is refused. A tool that
    raises in `cut_extents` otherwise cuts nothing. A node's reach is its tool's, the registry's `reach_of`, added a side
    to the furthest of the nodes it reads, and without bound where either is; the video node and
    a node that serves its file read their own row. A node reads one piece of the plate: one
    whose inputs are of two, the plate among them, is not fed, nor is anything that reads it, and
    its standing says which. A chain node is stepped when its tool steps and everything it reads on
    the chain is stepped; the first node that runs whole ends the prefix for every node after it,
    and a stepping tool so ended names that node in `whole_by`. The chain is of every fed head
    whose walked node's cuts are not cuts in time, whatever node each reads; the heads reading a
    node whose cuts are, or a node below a cutting node that has cut nothing yet, are each extent's
    `timed` Walk, every head of one extent's cuts in it, and their standing says the window does not
    walk them."""
    keys, raw_keys, pieces, files, refused = {}, {}, {}, {}, {}

    def cuts(nid):
        return tool_cuts(tools.get(doc.node(nid).tool))

    def file_of(nid, stack=()):
        if nid in stack:
            return None
        if nid not in files:
            w, said = doc.source(nid), None
            if cut_file is not None and w is not None and cuts(nid) and serves_cut_file(tools.get(doc.node(nid).tool)):
                if doc.node(w.src).tool == VIDEO_TOOL:
                    said = cut_file(nid, None)
                elif (up := file_of(w.src, (*stack, nid))) is not None:
                    said = cut_file(nid, up)
            if isinstance(said, str):
                refused[nid], said = said, None
            files[nid] = None if said is None else tuple(said)
        return files[nid]

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

    def keyed(node):
        tool = tools.get(node.tool)
        given, facet = computed(tool, node.params), key_params_of(tool)
        if facet is not None:
            try:
                return facet(given)
            except Exception:       # a tool's rule is user code: one that fails keys the node as a tool without one
                pass
        return given

    def in_time_alone(nid, stack):
        """Whether `nid` cuts what it reads in its rows and nothing else, so that what it hands
        down is what it reads, row for row."""
        if not cuts(nid) or file_of(nid):
            return False
        made_here = cuts_of(nid, stack)
        return made_here != reads_of(nid, stack) and all(
            len(c.made_from) == 1 and c.extent.rect == c.made_from[0].extent.rect and c.extent.rects == c.made_from[0].extent.rects
            for c in made_here)

    def read_key(src, stack):
        while in_time_alone(src, stack) and (above := doc.source(src)) is not None and above.src not in stack:
            src = above.src
        return key_of(src, stack)

    def up_key(nid, stack=()):
        ups = [read_key(src, stack) if src is not None and src not in stack else "none" for src in sources(nid).values()]
        return ups[0] if len(ups) == 1 else _key(*ups)

    def key_of(nid, stack=()):
        if nid not in keys:
            node = doc.node(nid)
            if node.tool == VIDEO_TOOL:
                keys[nid] = raw_keys[nid] = base
                return base
            fed_by_series = any(s is not None and kind_of(doc, tools, s) == "series" for s in sources(nid).values())
            raw = (base_key(file_of(nid)[1], video_output(doc)) if file_of(nid)
                   else _key(up_key(nid, (*stack, nid)), node.tool, json.dumps(keyed(node), sort_keys=True), *[FED_ABSENT][:fed_by_series]))
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
                if cuts(src):
                    out[name] = src
                else:
                    out[name] = next(iter(pieces_of(src, (*stack, nid)).values()), None)
            pieces[nid] = out
        return pieces[nid]

    root = Record(base if footage is None else footage)
    reads, made = {}, {}

    def reads_of(nid, stack=()):
        if nid not in reads:
            src = next((s for s in wired(nid).values() if s is not None and s not in stack), None)
            reads[nid] = (root,) if src is None else cuts_of(src, (*stack, nid))
        return reads[nid]

    waiting = {}

    def reads_node(nid, other, stack=()):
        return any(s == other or (s not in stack and reads_node(s, other, (*stack, nid))) for s in wired(nid).values() if s is not None)

    def cuts_of(nid, stack=()):
        if nid not in made:
            made[nid] = above = reads_of(nid, stack)
            if cuts(nid):
                node = doc.node(nid)
                tool = tools[node.tool]
                by = cut_by(tool)
                gate = w.src if by and (w := doc.source(nid, by[0])) else None
                filed = [name for name in paths(tool) if doc.source(nid, name)]
                if by and gate is None and not filed and paths(tool):
                    refused[nid] = f"neither {' nor '.join(paths(tool))} nor {by[0]} is wired"
                elif gate is not None and filed:
                    refused[nid] = f"fed both: {', '.join(filed)} by a file and {by[0]} by {gate}; one cuts it"
                elif gate is not None and reads_node(gate, nid):
                    refused[nid] = f"in a cycle: {by[0]} is fed by {gate}, which reads {nid}"
                elif gate is not None and None in (results := [cut_result and cut_result(nid, key_of(gate, (*stack, nid)), r) for r in above]):
                    waiting[nid], made[nid] = f"{by[0]} waits on {gate}'s walk", ()
                else:
                    try:
                        given = results if gate is not None else [cut_result(nid, None, r) if cut_result else None for r in above]
                        extents = [(r, list(cut_extents_of(tool)(computed(tool, node.params), g))) for r, g in zip(above, given)]
                        file = file_of(nid) if sum(len(xs) for _, xs in extents) == 1 else None
                        made[nid] = tuple(r.cut(**_lifted(x, r, g), file=file) for (r, xs), g in zip(extents, given) for x in xs)
                    except Exception:       # a tool's rule is user code: one that fails cuts nothing
                        pass
        return made[nid]

    reaches = {}

    def reach_of_node(nid, stack=()):
        if nid in stack:
            return None, None
        if nid not in reaches:
            node = doc.node(nid)
            tool = tools.get(node.tool)
            if node.tool == VIDEO_TOOL or file_of(nid) or (tool is not None and is_selector(tool)):
                reaches[nid] = (0, 0)
            else:
                sides = [(0, 0) if tool is None else reach_of(tool, computed(tool, node.params)),
                         *(reach_of_node(s, (*stack, nid)) for s in wired(nid).values() if s is not None)]
                own, above = sides[0], list(zip(*sides[1:])) or [(0,), (0,)]
                reaches[nid] = tuple(None if o is None or None in up else o + max(up) for o, up in zip(own, above))
        return reaches[nid]

    def said(piece):
        return "the plate" if piece is None else piece

    crossings = {}
    for n in doc.nodes:
        of = pieces_of(n.id)
        if len(set(of.values())) > 1:
            (a, pa), (b, pb) = next(((a, pa), (b, pb)) for a, pa in of.items() for b, pb in of.items() if pa != pb)
            crossings[n.id] = f"reads across a cut: {a} is of {said(pa)}, {b} of {said(pb)}"
    for n in doc.nodes:
        file_of(n.id)
        cuts_of(n.id)
    blocked, more = set(), {*crossings, *refused, *waiting}
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
                              file=file_of(n.id), cuts=cuts_of(n.id), reads=reads_of(n.id), reach=reach_of_node(n.id), produces=produces(doc, tools, n.id),
                              computed=computed(tool, n.params))
        if kind == "series":
            series.append(n.id)
    def chain_from(heads):
        chain = list(heads)
        for nid in chain:
            chain += [s for s in series if entries[s].src == nid and entries[s].fed and s not in chain]
        return chain

    def in_time(s):
        """Whether the node `s` reads is of cuts in time, or of none, a cutting node above it having cut nothing yet."""
        cuts = entries[entries[s].src].cuts
        return not cuts or any(c.extent.rows is not None for c in cuts)

    roots = [s for s in series if entries[s].src is None or entries[entries[s].src].kind != "series"]
    untimed = [s for s in roots if entries[s].src is None or not in_time(s)]
    anchor = untimed[0] if untimed else None
    heads = [s for s in untimed if entries[s].fed] or ([anchor] if anchor else [])
    chain, timed = chain_from(heads), []
    for s in roots:
        cuts = entries[entries[s].src].cuts if s not in untimed else None
        if cuts and entries[s].fed and all(w.cuts != cuts for w in timed):
            within = [r for r in roots if r not in untimed and entries[r].fed and entries[entries[r].src].cuts == cuts]
            timed.append(Walk(cuts, within, chain_from(within)))
    walked_chains = {nid for c in [chain, *(w.chain for w in timed)] for nid in c}
    enders = {}
    for nid in [*chain, *(n for w in timed for n in w.chain)]:
        e = entries[nid]
        own = not steps(e.tool)
        enders[nid] = nid if own else enders.get(e.src)
        e.steps, e.whole_by = enders[nid] is None, None if own else enders[nid]
    by_period = {nid: w for w in timed for nid in w.chain}
    for nid, e in entries.items():
        e.standing = (crossings.get(nid) or refused.get(nid) or waiting.get(nid)
                      or (f"walked by the clip walk over each of {len(by_period[nid].cuts)} periods alone, not by the window" if nid in by_period else "")
                      or (f"reads {e.src}, which cuts no rows" if e.kind == "series" and e.fed and e.src and not entries[e.src].cuts else "")
                      or _standing(doc, tools, entries, heads, walked_chains, nid))
    over = doc.overlay if doc.overlay in entries and overlaid(produces(doc, tools, doc.overlay)) else None
    return Plan(entries, heads, chain, [s for s in series if s not in walked_chains], doc.display if doc.display in entries else None, over, timed)


def _lifted(extent, within, result):
    """`extent`, as a tool's cut_extents answered it of `result`, with rows on the footage: a
    result handed over a cut in time counts its rows from that cut's first row."""
    rows = extent.get("rows")
    if result is None or rows is None or within.extent.rows is None:
        return extent
    first = within.extent.rows[0]
    return {**extent, "rows": (rows[0] + first, rows[1] + first)}


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
        return f"unrun: reads {e.src}, which no walk walks"
    return "" if e.fed else "in a cycle"
