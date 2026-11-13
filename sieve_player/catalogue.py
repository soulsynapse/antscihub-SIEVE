r"""The catalogue: the detectors, each a function from a ledger's view to the problems it shows, and the
log, one entry per class and subject. A problem's cost is ms a row of the walk it was found in, so
problems rank against each other and against the walk. A class is entered with a simulation of its
name in dev/simulations.py, which proves it fires alone. No graph is held and no Qt reached; an
entry's text takes what the stream does not carry, the document and the decoder's facts, as a dict.
What a reader shows of a walk is a value here, `rows`, `naming`, `needs`, `gui`, `machine`, `tight`,
`alike`, so the monitor and whatever else draws a node read one figure.

    .venv\Scripts\python -m sieve_player.catalogue dump.jsonl
"""
import json
import sys
from dataclasses import dataclass

from .ledger import View, quantile, replay

COSTS = ("run", "step", "fold", "decode", "seek", "read")      # the kinds a walk is compared with the last by

SOURCES = {
    "unread": "worker._Walk.turn folds Graph.frame_nodes(), every fed frame node, whatever the plot shows; "
              "docs/findings/2026-11-12-served-bake-upstream-walk.md",
    "thrash": "graph.Memo.put and Decoder._put, an LRU under a scanning walk; "
              "docs/findings/2026-10-31-window-fit-and-lru-thrash.md, docs/findings/2026-11-08-bake-window-fit.md",
    "grows": "worker.run_chain, a chain node the plan does not step run whole at every emit; "
             "docs/findings/2026-11-08-bake-window-fit.md, its second half",
    "seeks": "decoder.Decoder.read, a row behind the cursor or past what it reads through; a tool reading far from its row",
    "slower": "no one place; the evidence names the nodes whose cost moved",
    "waits": "window.PlayerWindow's slots and paints, Python on the GUI thread holding the interpreter a tool on the "
             "worker's then waits for; the subject names the slot or the part",
}


@dataclass(frozen=True)
class Problem:
    kind: str               # the class, a key of CLASSES
    subject: str            # the node it is about, a cache being its node's; "memo" for the memo
    line: str
    ms_row: float           # what it cost a row of the walk
    share: float | None     # of what the walk's nodes cost
    evidence: tuple         # the lines the figures were drawn from
    source: str             # where in the code the class has come from before
    walk: tuple             # (lane, t0) of the walk it was found in
    t: float                # that walk's last progress, on the probe's clock
    says: str = ""          # the class in one sentence, for a user of the player and not a reader of the code
    target: str = ""        # what to act on: a node's fold, a store and what the walk needs of it, a slot
    nodes: tuple = ()       # the nodes it names, and for a wait the GUI thread's span


def cost(walk):
    """The ms the walk's nodes took, every span of every kind."""
    return sum(r[1] for n in walk.nodes.values() for r in n.runs.values())


def size(b):
    """Bytes as they are written, in GB from one up and in MB under it."""
    return f"{b / 2**30:.1f} GB" if b >= 2**30 else f"{b / 2**20:.1f} MB"


def store_name(store, view):
    """A store as it is written: the memo, a lane's stack, or a cache by the node whose key it reports under."""
    names = {k: n for w in view.walks for n, k in (w.keys or {}).items()}
    return store if store == "memo" or store.endswith(" stack") else names.get(store, store[:6]) + " cache"


def span(view, walk):
    """The buckets of `view` that `walk` ran over."""
    i0, i1 = (int(t // view.width) - view.first for t in (walk.t0, walk.t1))
    return view.buckets[max(i0, 0):max(i1 + 1, 0)]


_HELD_AS = {"run": "result", "fold": "fold", "cache": "row", "decode": "row", "seek": "row"}


def needs(view, walk):
    """What `walk`'s range asks each store to hold, {store: bytes}: for each node the mean bytes of
    a result, of a fold and of a row its cache read, by the latest walk in `view` that made one under
    the node's key, times the range, a static node's result once. It reads what was made and no
    discard, so it stands from a walk's first rows; a store nothing was made for is not in it."""
    nodes, out = (walk.plan or {}).get("nodes") or {}, {}
    for nid, key in (walk.keys or {}).items():
        mean = {}
        for w in view.walks:
            if (w.keys or {}).get(nid) != key or nid not in w.nodes:
                continue
            made = {}
            for (kind, _, _), (n, _, b) in w.nodes[nid].runs.items():
                if kind in _HELD_AS:
                    m = made.setdefault(_HELD_AS[kind], [0, 0])
                    m[0], m[1] = m[0] + n, m[1] + b
            mean.update({what: b / n for what, (n, b) in made.items() if n and b})
        rows = 1 if (nodes.get(nid) or {}).get("static") else walk.length
        for what, b in mean.items():
            store = key if what == "row" else "memo"
            out[store] = out.get(store, 0) + b * rows
    return out


def finished(view):
    """The walks a detector judges: every walk its lane has begun another after, and a lane's last
    once it has done its range."""
    last = {w.lane: w for w in view.walks}
    return [w for w in view.walks if w.done and (w is not last[w.lane] or w.done >= w.length)]


def _problem(kind, walk, subject, line, ms, evidence, says, target, nodes=()):
    total = cost(walk)
    return Problem(kind, subject, line, ms / walk.done, ms / total if total else None, tuple(evidence), SOURCES[kind],
                   (walk.lane, walk.t0), walk.t1, says, target, tuple(dict.fromkeys(nodes)))


UNREAD = 0.25       # the share of a walk's cost under folds no watched node asked for, at which each is a problem


def unread(view):
    """Work no watched node and no walked node asked for: everything under a density's fold of a
    node neither pinned nor selected while the walk ran, the runs and decodes the fold opened with it."""
    out = []
    for w in finished(view):
        if w.plan is None or w.replanned:
            continue
        watched, by = {*w.plan["pinned"], *w.selected}, {}
        for nid, node in w.nodes.items():
            for (kind, demand, asked), (n, ms, _) in node.runs.items():
                if demand == "fold" and asked not in watched:
                    by.setdefault(asked, []).append((ms, n, nid, kind))
        if sum(r[0] for rs in by.values() for r in rs) < UNREAD * cost(w) or not cost(w):
            continue
        for asked, rs in by.items():
            rs.sort(reverse=True)
            what = ", ".join(f"{n} {nid} {kind}" for _, n, nid, kind in rs)
            out.append(_problem("unread", w, asked, f"{asked}'s density is folded and it is neither pinned nor selected: {what}",
                                sum(r[0] for r in rs), [f"{nid} {kind} x{n}: {ms:.1f} ms" for ms, n, nid, kind in rs],
                                "Computed on every row and read by nothing", f"the fold of {asked}", [r[2] for r in rs]))
    return out


THRASH = 0.25       # recomputations a row of the walk at which a store is a problem


def thrash(view):
    """A store computing or decoding again what it had discarded: the memo, or a decoder's cache,
    the plate's under the video node and a served reader's under the served one."""
    out = []
    for w in finished(view):
        at = int(w.t1 // view.width) - view.first
        stores = view.buckets[at].stores if 0 <= at < len(view.buckets) else {}
        need = needs(view, w)
        for store, n in w.recomputed.items():
            if n < THRASH * w.done:
                continue
            node = next((nid for nid, k in (w.keys or {}).items() if k == store), store)
            held = f"; it held {stores[store][0] / 2**20:.1f} of {(stores[store][1] or 0) / 2**20:.1f} MB at the walk's end" if store in stores else ""
            line = (f"the memo ran again {n} results it had discarded" if store == "memo" else
                    f"{node}'s cache decoded again {n} rows it had discarded") + f", over {w.done} rows{held}"
            name = "memo" if store == "memo" else f"{node} cache"
            fits = store in need and store in stores and stores[store][1]
            out.append(_problem("thrash", w, "memo" if store == "memo" else node, line, w.recomputed_ms.get(store, 0.0),
                                [f"{n} recomputations, {w.recomputed_ms.get(store, 0.0):.1f} ms", f"store {store}"],
                                f"The {name} is {'recomputing' if store == 'memo' else 'decoding again'} what it threw out",
                                f"the {w.lane or 'walk'} needs {size(need[store])}, the {name} holds {size(stores[store][1])}"
                                if fits else f"the {name}'s limit", () if store == "memo" else [node]))
    return out


GROWS = 3.0         # a node's ms a run over the last quarter of the range against the first
GROWS_SHARE = 0.1   # and the share of the walk's cost the growth is, below which it is not a problem


def grows(view):
    """A node whose cost a run grows along the range, a chain node run whole over the rows so far
    being the known case; read off the parts of the range its spans fell in, so rows a store held
    are not taken for cheap ones."""
    out = []
    for w in finished(view):
        total = cost(w)
        for nid, node in w.nodes.items():
            per = [ms / n for ms, n in zip(node.parts, node.counts) if n]
            k = len(per) // 4
            if not k:
                continue
            first, last = sum(per[:k]) / k, sum(per[-k:]) / k
            over = sum(node.parts) - first * sum(node.counts)
            if last < GROWS * first or over < GROWS_SHARE * total or not over:
                continue
            p = ((w.plan or {}).get("nodes") or {}).get(nid) or {}
            whole = "; the plan runs it whole at every emit" if p.get("kind") == "series" and not p.get("steps") else ""
            out.append(_problem("grows", w, nid, f"{nid} costs {last:.2f} ms a run at the range's end against {first:.2f} "
                                f"at its start{whole}", over, ["ms a run along the range: " + " ".join(f"{x:.2f}" for x in per)],
                                "Costs more a row the further the walk goes",
                                nid + (", run whole at every emit" if whole else ""), [nid]))
    return out


SEEKS = 1           # the seeks a walk may make on one node: the one a walk beginning mid-clip opens with


def seeks(view):
    """The walk's cursor seeking, on the plate's decoder or a served reader's."""
    out = []
    for w in finished(view):
        for nid, node in w.nodes.items():
            rs = [(demand, asked, n, ms) for (kind, demand, asked), (n, ms, _) in node.runs.items() if kind == "seek"]
            n = sum(r[2] for r in rs)
            if n > SEEKS:
                out.append(_problem("seeks", w, nid, f"the walk's cursor on {nid} sought {n} times over {w.done} rows",
                                    sum(r[3] for r in rs), [f"under the {d} of {a}: {c} seeks, {ms:.1f} ms" for d, a, c, ms in rs],
                                    "The walk's reads jump around the file instead of running forward",
                                    f"the reads of {nid}", [nid]))
    return out


SLOWER = 1.5        # what the nodes of a walk cost, against the same runs at the last walk's ms a run


def _per(walk):
    out = {}
    for nid, node in walk.nodes.items():
        for (kind, _, _), (n, ms, _) in node.runs.items():
            if kind in COSTS and n:
                r = out.setdefault((nid, kind), [0, 0.0])
                r[0] += n
                r[1] += ms
    return out


def slower(view):
    """A walk that costs more than the lane's last walk, both whole, of one length and under one
    plan, whatever the cause: each node's ms a run in what ran in both, so a walk colder than the
    last is not a slower one, and the ms a row no span covers, under the subject "unprobed"."""
    out, before, judged = [], {}, {id(w) for w in finished(view)}
    for w in view.walks:
        prev, before[w.lane] = before.get(w.lane), w
        if (id(w) not in judged or prev is None or w.keys is None or prev.keys != w.keys or w.replanned or prev.replanned
                or prev.length != w.length or w.done < w.length or prev.done < prev.length):
            continue
        was, now, moved = _per(prev), _per(w), []
        for key in was.keys() & now.keys():
            a, b = was[key][1] / was[key][0], now[key][1] / now[key][0]
            moved.append(((b - a) * now[key][0], a, b, now[key][0], *key))
        if not moved:
            continue
        a, b = prev.unprobed / prev.done, w.unprobed / w.done
        moved.append(((b - a) * w.done, a, b, w.done, "unprobed", "row"))
        expected, actual = sum(a * n for _, a, _, n, _, _ in moved), sum(b * n for _, _, b, n, _, _ in moved)
        if not expected or actual < SLOWER * expected:
            continue
        moved.sort(reverse=True)
        _, a, b, _, nid, kind = moved[0]
        out.append(_problem("slower", w, nid, f"a row costs {actual / w.done:.2f} ms in what ran in both walks against "
                            f"{expected / w.done:.2f} in the walk before, under one plan; {nid} went from {a:.2f} to "
                            f"{b:.2f} ms a {kind}", actual - expected,
                            [f"{n} {k}: {x:.3f} to {y:.3f} ms, {d:+.1f} ms over the walk" for d, x, y, _, n, k in moved],
                            "Slower than the last walk under the same settings",
                            "the time between rows, in no node" if nid == "unprobed" else nid,
                            [n for d, _, _, _, n, _ in moved if d > 0 and n != "unprobed"]))
    return out


WAITS = 0.1         # the tools' waits that coincide with the GUI thread's spans, as a share of the walk's cost
TICK = 16.0         # ms; the CPU clock's step on Windows, see Event.cpu_ms: a walk's wait under one is not a figure


def waits(view):
    """The worker waiting on the GUI thread: over the buckets a walk spans, what its tools spent
    off their own CPU while the GUI thread was in a slot or a paint, the lesser of the two in each
    bucket and no more than the walk's own wait, which is the steadier figure. A read's wait is the
    decoder's threads and is not counted; a tool that sleeps coincides with nothing."""
    out = []
    for w in finished(view):
        both, by = 0.0, {}
        for b in span(view, w):
            if b.wait > 0 and b.turns:
                both += min(b.wait, sum(b.turns.values()))
                for name, ms in b.turns.items():
                    by[name] = by.get(name, 0.0) + ms
        both = min(both, w.wait)
        if both < max(TICK, WAITS * cost(w)):
            continue
        top = sorted(by.items(), key=lambda x: -x[1])
        out.append(_problem("waits", w, top[0][0], f"the walk's tools waited {both:.0f} ms off their CPU while the GUI thread "
                            f"was in its own spans, {top[0][0]} the longest at {top[0][1]:.0f} ms", both,
                            [*(f"{name}: {ms:.1f} ms" for name, ms in top),
                             f"the walk's tools {w.wait:.1f} ms off their CPU, its reads {w.read_wait:.1f}"],
                            "The walk waits while the interface thread is busy",
                            "the " + " ".join(reversed(top[0][0].split(" ", 1))), [top[0][0]]))
    return out


CLASSES = {"unread": unread, "thrash": thrash, "grows": grows, "seeks": seeks, "slower": slower, "waits": waits}


@dataclass
class Entry:
    problem: Problem        # its latest sighting
    first: float            # the first sighting's t
    count: int = 0          # the walks it was seen in
    holds: bool = True      # whether its lane's last finished walk shows it


class Log:
    """The problems the catalogue has surfaced, one Entry per class and subject. `read(view)` runs
    every detector and may be called on any view any number of times: a walk counts once toward an
    entry however often it is read."""

    def __init__(self, classes=None):
        self.classes = CLASSES if classes is None else classes
        self.entries = {}       # (class, subject) -> Entry
        self._seen = {}         # a walk's (lane, t0) -> the entries it has counted toward

    def read(self, view):
        """Takes what `view` shows into the entries and returns those it made, the first sightings."""
        made = []
        latest = {w.lane: (w.lane, w.t0) for w in finished(view)}
        for detect in self.classes.values():
            for p in detect(view):
                key = (p.kind, p.subject)
                e = self.entries.get(key)
                if e is None:
                    e = self.entries[key] = Entry(p, p.t)
                    made.append(e)
                seen = self._seen.setdefault(p.walk, set())
                if key not in seen:
                    seen.add(key)
                    e.count += 1
                if p.walk[1] >= e.problem.walk[1]:
                    e.problem = p
        for e in self.entries.values():
            lane = e.problem.walk[0]
            e.holds = latest.get(lane, e.problem.walk) == e.problem.walk
        self._seen = {wid: s for wid, s in self._seen.items() if wid in {(w.lane, w.t0) for w in view.walks}}
        return made

    def ordered(self):
        """The entries, the costliest first."""
        return sorted(self.entries.values(), key=lambda e: -e.problem.ms_row)


@dataclass(frozen=True)
class Row:
    """One node over a walk as any reader shows it, the monitor's table or a node on the canvas."""
    node: str
    ms_row: float           # its ms over the walk's rows
    spans: int
    kind: str               # the kind, demand and node asked that most of its ms were under
    demand: str | None
    asked: str | None
    free: float | None      # the walk's rate were the node free, over its rate now; None for a node that took all of it
    median: float | None    # of the ms a span of `kind` took, and the 99th percentile, by ledger.quantile
    p99: float | None
    per_mp: float | None    # that median over the megapixels a span read: its own plane for a read or a fold, its inputs' for a run

    def asked_by(self):
        return {"walk": "the walk", "fold": f"fold of {self.asked}", "display": "the display", "bake": "a bake"}.get(self.demand, "-")


def _pixels(view, walk, nid):
    """The pixels of `nid`'s output, by `walk` or else the latest walk of `view` before it that saw
    its shape under the same key; None unseen, or for an output that is no plane."""
    key, at = (walk.keys or {}).get(nid), next((i for i, x in enumerate(view.walks) if x is walk), len(view.walks))
    for w in (walk, *reversed(view.walks[:at])):
        shape = w.nodes[nid].shape if nid in w.nodes and (w is walk or (w.keys or {}).get(nid) == key) else None
        if shape is not None:
            return shape[0] * shape[1] if len(shape) >= 2 else None
    return None


def rows(walk, view=None):
    """{node: Row} of `walk`, in the record's order; what a row cost is its nodes' ms and its
    unprobed. `view` is where an input's shape is looked for when `walk` did not run it; without
    one a run whose input was held has no ms per megapixel."""
    total, out, plan = cost(walk) + walk.unprobed, {}, (walk.plan or {}).get("nodes") or {}
    view = View(0.0, 0, [], [walk]) if view is None else view
    for nid, node in walk.nodes.items():
        if not node.runs or not walk.done:
            continue
        ms, n = sum(r[1] for r in node.runs.values()), sum(r[0] for r in node.runs.values())
        kind, demand, asked = max(node.runs, key=lambda k: node.runs[k][1])
        bins = node.bins.get(kind) or []
        median, px = quantile(bins, 0.5), None
        if kind == "run":
            read = [_pixels(view, walk, src) for src in (plan.get(nid) or {}).get("reads", {}).values() if src]
            px = sum(read) if read and None not in read else None
        elif kind in ("decode", "seek", "cache", "read", "fold"):
            px = _pixels(view, walk, nid)
        out[nid] = Row(nid, ms / walk.done, n, kind, demand, asked, total / (total - ms) if total > ms else None,
                       median, quantile(bins, 0.99), median / (px / 1e6) if median is not None and px else None)
    return out


def reach(plan):
    """The nodes a walk under `plan`, a sync's facts, computes for a row when it folds no density:
    the walked node and what it reads, through to the video or a served node, and the chain."""
    nodes, seen, todo = plan.get("nodes") or {}, set(), [plan.get("walk"), *(plan.get("chain") or ())]
    while todo:
        nid = todo.pop()
        if nid in nodes and nid not in seen:
            seen.add(nid)
            todo += [s for s in nodes[nid]["reads"].values() if s]
    return seen


_COLD = ("run", "step", "decode", "read", "cache")     # what a row pays a node; a seek is a walk's opening and a fold the window's


@dataclass(frozen=True)
class Cold:
    """What a row nothing holds pays one node, from the latest walk in which the node ran."""
    node: str
    ms_row: float           # its ms under the walk's own demand over the rows it ran or read its file on; 0 for a static node, which runs once
    walk: tuple | None      # (lane, t0) of the walk the figure is from; None for a static node
    stale: bool             # that walk ran it under another key: the figure is from before a change at or upstream of it
    grows: tuple | None     # (ms an emit at no rows, ms an emit a row, rows an emit) for a chain node run whole, fitted along that walk's range


@dataclass(frozen=True)
class Projection:
    """A cold walk under the newest walk's plan, by `cold`."""
    nodes: dict             # node -> Cold, the nodes `reach` gives that have a figure
    unprobed: float         # ms a row no span covers, by the newest walk a figure is from
    missing: tuple          # reached, not static, and never seen running

    def ms_row(self, rows=None):
        """The ms a cold row costs; over a range of `rows`, a node run whole costing by its growth
        and no longer by its mean over the walk it was seen in."""
        out = self.unprobed
        for c in self.nodes.values():
            if rows and c.grows:
                at0, slope, every = c.grows
                emits = rows / every
                out += (at0 * emits + slope * every * emits * (emits + 1) / 2) / rows
            else:
                out += c.ms_row
        return out


def cold(view):
    """The Projection for the plan of the newest walk in `view`, or None with no walk or no plan.
    Each node's figure is from the latest walk in which it ran under its key now, else under any."""
    w0 = next((w for w in reversed(view.walks) if w.plan), None)
    if w0 is None:
        return None
    plan, nodes, missing, newest = w0.plan["nodes"], {}, [], None
    for nid in (n for n in plan if n in reach(w0.plan)):
        if plan[nid]["static"]:
            nodes[nid] = Cold(nid, 0.0, None, False, None)
            continue
        found = None
        for w in reversed(view.walks):
            node = w.nodes.get(nid)
            ms = sum(r[1] for (kind, demand, _), r in node.runs.items() if demand == "walk" and kind in _COLD) if node else 0.0
            n = sum(r[0] for (kind, demand, _), r in node.runs.items() if demand == "walk" and kind in _COLD) if node else 0
            if not n:
                continue
            same = (w.keys or {}).get(nid) == (w0.keys or {}).get(nid)
            if found is None or same:
                found = (w, node, ms, n, not same)
            if same:
                break
        if found is None:
            missing.append(nid)
            continue
        w, node, ms, n, stale = found
        whole = plan[nid]["kind"] == "series" and not plan[nid]["steps"]
        rows = w.done if whole else node.ran + node.served
        nodes[nid] = Cold(nid, ms / max(rows, 1), (w.lane, w.t0), stale, _growth(w, node) if whole else None)
        if newest is None or w.t0 > newest.t0:
            newest = w
    return Projection(nodes, newest.unprobed / max(newest.done, 1) if newest else 0.0, tuple(missing))


def _growth(walk, node):
    """(ms an emit at no rows, ms an emit a row, rows an emit) by least squares over the parts of
    `walk`'s range `node` ran in; None with fewer than two."""
    n = len(node.parts)
    pts = [((i + 0.5) * walk.length / n, ms / c) for i, (ms, c) in enumerate(zip(node.parts, node.counts)) if c]
    spans = sum(node.counts)
    if len(pts) < 2 or not walk.done:
        return None
    mx, my = sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)
    slope = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)
    return my - slope * mx, slope, walk.done / spans


def naming(entries):
    """{node: the entries whose problems name it}, in the order given."""
    out = {}
    for e in entries:
        for n in e.problem.nodes:
            out.setdefault(n, []).append(e)
    return out


def gui(view, walk):
    """The GUI thread over `walk`: (its worst lateness in ms, [(what, its share of the wall, the
    longest of them)]) for its slots, its paints and the monitor's own of both."""
    bs, by = span(view, walk), {}
    for b in bs:
        for name, ms in b.turns.items():
            by[name] = by.get(name, 0.0) + ms
    wall, out = len(bs) * view.width * 1000, []
    for what, mine in (("slot", False), ("paint", False), ("monitor", True)):
        rs = {n: ms for n, ms in by.items() if n.endswith(" monitor") == mine and (mine or n.startswith(what))}
        out.append((what, sum(rs.values()) / wall if wall else 0.0, max(rs, key=rs.get).split(" ", 1)[1] if rs else None))
    return max((b.late for b in bs), default=0.0), out


MEMORY = CORES = DISK = 0.9   # the share of a resource in use at which it is tight


@dataclass(frozen=True)
class Resource:
    """One of the machine's resources over a walk, at the sample in which the most of it was in use.
    The GPU is a line and no resource to run short of, SIEVE's decode and tools running on none
    (docs/findings/2026-11-12-the-gpu-over-a-walk.md): it has no shares and is never tight."""
    name: str               # "memory" | "cores" | "disk" | "GPU"
    ours: float | None      # SIEVE's share of the whole, and everything else's
    others: float | None
    value: str              # the two together against the whole, as written
    note: str               # SIEVE's part, and for memory what holds it as far as the stream says
    tight: bool


def machine(view, walk):
    """[Resource] for `walk`, memory, cores, disk and GPU, from the "machine" samples in the buckets
    it ran over, or the last before it when it was shorter than their period; [] with none, and a
    resource the sample could not read is left out. Memory's hard faults are a figure beside it and
    no part of whether it is tight: a mapped file's first read is one as a page file's is."""
    at = max(int(walk.t1 // view.width) - view.first + 1, 0)
    seen = [b for b in span(view, walk) if b.machine] or [b for b in reversed(view.buckets[:at]) if b.machine][:1]

    def most(name, share):
        return max((b.machine[name] for b in seen if b.machine.get(name)), key=share, default=None)
    out = []
    if (m := most("memory", lambda m: m[0] + m[1])) is not None:
        ours, others, whole = m
        stores = next((b.stores for b in reversed(view.buckets[:at]) if b.stores), {})
        held = [f"{store_name(s, view)} {size(n)}" for s, (n, _) in sorted(stores.items(), key=lambda x: -x[1][0]) if n]
        faults = max((b.machine["faults"] for b in seen if b.machine.get("faults") is not None), default=None)
        out.append(Resource("memory", ours / whole, others / whole, f"{size(ours + others)} of {size(whole)}",
                            f"SIEVE {size(ours)}" + (": " + ", ".join(held) if held else "")
                            + ("" if faults is None else f" · {faults:.0f} hard faults a second"), (ours + others) / whole >= MEMORY))
    if (m := most("cores", lambda m: m[0] + m[1])) is not None:
        ours, others, whole = m
        out.append(Resource("cores", ours / whole, others / whole, f"{ours + others:.1f} of {whole}", f"SIEVE {ours:.1f}",
                            (ours + others) / whole >= CORES))
    if (m := most("disk", lambda m: (m[2] or 0.0, m[0] + m[1]))) is not None:
        ours, others, busy = m
        part = ours / (ours + others) if ours + others else 0.0
        out.append(Resource("disk", (busy or 0.0) * part, (busy or 0.0) * (1 - part),
                            f"{size(ours + others)}/s" + ("" if busy is None else f" · busy {busy:.0%}"),
                            f"SIEVE {size(ours)}/s" + (" · how busy the disks were was not read" if busy is None else ""),
                            (busy or 0.0) >= DISK))
    if (m := most("gpu", sum)) is not None:
        mine = max(b.machine["gpu"][0] for b in seen if b.machine.get("gpu"))
        out.append(Resource("GPU", None, None, f"{m[0] + m[1]:.0%}",
                            f"SIEVE {mine:.0%} at most" if mine else "SIEVE ran nothing on it", False))
    return out


def tight(resources):
    """The machine in one sentence: which of `resources` is tight, or that none is."""
    if not resources:
        return "The machine was not sampled over this walk."
    names = [r.name for r in resources if r.tight]
    if not names:
        return "No resource of the machine's is tight."
    return (f"{' and '.join(names).capitalize()} {'are' if len(names) > 1 else 'is'} what is tight: "
            + "; ".join(f"{r.name} {r.value}" for r in resources if r.tight) + ".")


def alike(view, walk):
    """The ms a row, its nodes' and its unprobed, of each walk in `view` to set beside `walk`: its
    lane's, whole, of its length, under its plan and as cold, each node having run on as many rows;
    `walk`'s own among them when it is whole. Oldest first."""
    def ran(w):
        return {n: x.ran for n, x in w.nodes.items() if x.ran}
    return [(cost(w) + w.unprobed) / w.done for w in view.walks
            if w.lane == walk.lane and w.keys == walk.keys and w.length == walk.length and w.done >= w.length
            and not w.replanned and ran(w) == ran(walk)]


def report(entries, view, context=None):
    """One block for `entries`, in the order given: the problems numbered, each with its sentence
    and target, its evidence, where the class has come from and its simulation; then once, of the
    first entry's walk, the walk and the one before it in its lane, the plan's watched set, the
    table with the numbers of the problems naming each node, the machine, the GUI thread, the
    stores, the video and the decoder, and the history's file. `context` is as `text` takes it, with
    "history", the path of a saved history holding the document, "when", the wall time as written,
    and "now", the probe's clock; a part with nothing to say reads "-"."""
    c, named = context or {}, {}
    out = [f"SIEVE monitor report · {c.get('when', '-')} · commit {c.get('commit') or '-'}",
           f"{len(entries)} problem{'s' * (len(entries) != 1)}, costliest first; their shares may count the same ms twice"]
    for i, e in enumerate(entries, 1):
        p = e.problem
        since = "" if c.get("now") is None else f" · first seen {c['now'] - e.first:.0f} s before this"
        out += ["", f"{i}  {p.kind} · {p.subject} · {p.ms_row:.2f} ms a row" + ("" if p.share is None else f" · {p.share:.0%}")
                + f" · {e.count} walk{'s' * (e.count != 1)}{since}{'' if e.holds else ' · cleared'}",
                f"   {p.says}: {p.target}", f"   {p.line}", *("   " + x for x in p.evidence),
                f"   from  {p.source}", f"   repro python -m sieve_player.dev.simulations {p.kind}"]
        for n in p.nodes:
            named.setdefault(n, []).append(str(i))

    def said(w):
        return (f"{w.lane} · rows {w.start}..{(w.start or 0) + w.length - 1} · {w.done} done · "
                f"{(cost(w) + w.unprobed) / max(w.done, 1):.2f} ms a row" + (" · under more than one plan" if w.replanned else ""))
    at = next((i for i, w in enumerate(view.walks) if entries and (w.lane, w.t0) == entries[0].problem.walk), len(view.walks) - 1)
    out.append("")
    if at < 0:
        out.append("WALK     no longer in the history")
    else:
        w = view.walks[at]
        prev = next((x for x in reversed(view.walks[:at]) if x.lane == w.lane), None)
        plan = w.plan or {}
        out += ["WALK     " + said(w),
                "BEFORE   " + ("-" if prev is None else said(prev) + (" · the same plan" if prev.keys == w.keys else " · another plan")),
                "PLAN     " + ("-" if not plan else f"walks {plan.get('walk')} · chain {', '.join(plan.get('chain') or []) or 'none'} · "
                               f"shown {plan.get('shown')} · pinned {', '.join(plan.get('pinned') or []) or 'none'} · "
                               f"selected {', '.join(w.selected) or 'none'}"),
                "", f"ROW      {'node':<16}{'ms/row':>7}{'spans':>7}  {'kind':<7}{'asked by':<20}{'p50':>7}{'p99':>7}{'ms/MP':>7}  in"]

        def ms(x):
            return f"{'-' if x is None else format(x, '.2f'):>7}"
        for r in rows(w, view).values():
            out.append(f"         {r.node:<16}{r.ms_row:>7.2f}{r.spans:>7}  {r.kind:<7}{r.asked_by():<20}{ms(r.median)}{ms(r.p99)}{ms(r.per_mp)}"
                       f"  {','.join(named.get(r.node, []))}".rstrip())
        res, like = machine(view, w), alike(view, w)
        late, turns = gui(view, w)
        stores, need = next((b.stores for b in reversed(span(view, w)) if b.stores), {}), needs(view, w)
        out += [f"         {'unprobed':<16}{w.unprobed / max(w.done, 1):>7.2f}", "",
                "MACHINE  " + "\n         ".join([tight(res), *(f"{r.name} {r.value} · {r.note}" for r in res),
                                                 *([f"{len(like)} walks under this plan and as cold, {min(like):.2f} to {max(like):.2f} ms a row"]
                                                   if len(like) > 1 else [])]),
                f"GUI      worst {late:.0f} ms late · " + " · ".join(("the monitor" if what == "monitor" else f"{what}s") + f" {share:.1%}"
                                                                   + (f", {top} the longest" if top and what != "monitor" else "")
                                                                   for what, share, top in turns),
                "STORES   " + ("\n         ".join(
                    f"{store_name(s, view)} {size(held)} of {size(limit or 0)} · {w.recomputed.get(s, 0)} run again"
                    + (f" · the {w.lane or 'walk'} needs {size(need[s])}" if s in need else "") for s, (held, limit) in stores.items()) or "-")]
    d = c.get("decoder")
    out += [f"VIDEO    {c.get('video', '-')} · " + ("-" if not d else ", ".join(f"{k} {v}" for k, v in d.items())) + f" · memo limit {c.get('memo_limit', '-')}",
            f"HISTORY  {c.get('history') or '-'}"]
    return "\n".join(out)


def line(entry):
    p = entry.problem
    share = "" if p.share is None else f" {p.share:.0%}"
    return (f"{p.kind:<7} {p.subject:<14} {p.ms_row:7.2f} ms/row{share:>5}  x{entry.count}"
            f"{'' if entry.holds else '  cleared'}  {p.line}")


def text(entry, view, context=None):
    """One block sufficient to begin on the entry's fault without the session it was seen in, each
    part under its label, the document last and whole after its label's line. `context` is what
    no view holds: "document", the document as saved, "video", "decoder", "memo_limit", "commit",
    "dump"; a part it lacks reads "-"."""
    p, c = entry.problem, context or {}
    w = next((w for w in view.walks if (w.lane, w.t0) == p.walk), None)
    out = [f"class      {p.kind}", f"subject    {p.subject}", f"line       {p.line}",
           f"cost       {p.ms_row:.3f} ms a row" + ("" if p.share is None else f", {p.share:.0%} of what the walk's nodes cost")
           + f"; seen in {entry.count} walk{'s' * (entry.count != 1)}, {'still holds' if entry.holds else "not in the lane's last walk"}",
           "evidence", *("  " + e for e in p.evidence)]
    if w is None:
        out.append("walk       no longer in the history")
    else:
        out.append(f"walk       {w.lane}, rows {w.start}..{(w.start or 0) + w.length - 1}, {w.done} of {w.length} done in "
                   f"{w.t1 - w.t0:.2f} s, {cost(w):.0f} ms in its nodes" + (", under more than one plan" if w.replanned else ""))
        out.append(f"  {'node':<14}{'ran':>6}{'held':>6}{'served':>7}  {'kind':<7}{'demand':<8}{'asked':<14}{'n':>6}{'ms':>9}{'ms/row':>8}")
        for nid, node in w.nodes.items():
            head = f"  {nid:<14}{node.ran:>6}{node.held:>6}{node.served:>7}  "
            for (kind, demand, asked), (n, ms, _) in node.runs.items() or {("-", "-", "-"): (0, 0.0, 0)}.items():
                out.append(f"{head}{kind:<7}{str(demand):<8}{str(asked):<14}{n:>6}{ms:>9.1f}{ms / w.done:>8.3f}")
                head = " " * len(head)
        nodes = (w.plan or {}).get("nodes") or {}
        out.append("plan       " + ("-" if not nodes else f"walk {w.plan['walk']}, chain {w.plan['chain']}, shown {w.plan['shown']}, "
                                    f"overlaid {w.plan['over']}, pinned {w.plan['pinned']}, selected {w.selected}"))
        if p.subject in nodes:
            readers = [n for n, f in nodes.items() if p.subject in f["reads"].values()]
            for nid in dict.fromkeys([p.subject, *(s for s in nodes[p.subject]["reads"].values() if s), *readers]):
                f = nodes[nid]
                flags = [f["kind"], "fed" if f["fed"] else "unfed", *(k for k in ("static", "served", "steps") if f[k]),
                         *([f"whole by {f['whole_by']}"] if f["whole_by"] else [])]
                out.append(f"  {nid}: {', '.join(flags)}; reads {', '.join(str(s) for s in f['reads'].values())}; "
                           f"read by {', '.join(n for n, x in nodes.items() if nid in x['reads'].values()) or 'nothing'}")
        names = {k: n for n, k in (w.keys or {}).items()}
        stores = next((b.stores for b in reversed(view.buckets) if b.stores), {})
        out.append("stores     " + (", ".join(f"{'memo' if s == 'memo' else names.get(s, s) + ' cache'} {b / 2**20:.1f} of "
                                              f"{(limit or 0) / 2**20:.1f} MB" for s, (b, limit) in stores.items()) or "-"))
    d = c.get("decoder")
    out += [f"video      {c.get('video', '-')}",
            "decoder    " + ("-" if not d else ", ".join(f"{k} {v}" for k, v in d.items())) + f"; memo limit {c.get('memo_limit', '-')}",
            f"commit     {c.get('commit') or '-'}", f"dump       {c.get('dump') or '-'}",
            f"simulation python -m sieve_player.dev.simulations {p.kind}", f"source     {p.source}",
            "document", json.dumps(c.get("document"), indent=2, ensure_ascii=False)]
    return "\n".join(out)


if __name__ == "__main__":
    log = Log()
    log.read(replay(sys.argv[1]).view())
    print("\n".join(line(e) for e in log.ordered()) or "nothing found")
