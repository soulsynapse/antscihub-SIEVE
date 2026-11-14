r"""The catalogue: the detectors, each a function from a ledger's view to the problems it shows, and the
log, one entry per class and subject, which a ledger tells of each bucket as it settles. A class
of CLASSES judges a walk and a problem of its is costed in ms a row of that walk, so problems rank
against each other and against the walk; a class of SPANS judges the buckets, a walk over them or
none; a class of CLOCK judges what a view says of now. A class is entered with a simulation in dev/simulations.py, which proves it fires alone. No
graph is held and no Qt reached. A
problem and a resource carry their own words; laying entries out as a report is report.py's.
What a reader shows of a walk is a value here, `rows`, `naming`, `needs`, `asked_of`, `gui`, `machine`, `tight`,
`alike`, so the monitor and whatever else draws a node read one figure.
"""
import math
from dataclasses import dataclass, field, replace
from typing import NamedTuple

from .ledger import PARTS, View, WalkId, quantile, stores_after
from .stream import ASKED, CACHE, DECODE, FOLD, GIVEN, MONITOR, PAINT, READ, RUN, SEEK, SHAPE, SLOT, STEP, THE_USERS

COSTS = (RUN, STEP, FOLD, DECODE, SEEK, READ)      # the kinds a walk is compared with its baseline by
SLOWER = 1.5        # what the nodes of a walk cost, against the same runs at its baseline's ms a run

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
    "signals": "worker._Walk.report, a progress signal at every row, and the window's slots on it; "
               "docs/findings/2026-11-13-a-signal-a-row.md",
    "late": "window.Lateness, the GUI thread's timer firing late: a slot or a paint of window.PlayerWindow's, a tool's one call "
            "holding the interpreter, or what the GUI thread does under no span; the subject says which",
    "restarts": "worker._Walk.turn, a range begun again where what it was given went stale or the nodes or the shape changed "
                "under it, and Worker.set_window or walk_clip asked by no hand and no edit; the evidence says which",
    "stalls": "no one place: a tool's call, a read or the worker's own code between two rows that does not return; "
              "the stream says which lane and not yet what the thread is in",
}


NODE, STORE, TURN, BETWEEN = "node", "store", "turn", "between"     # what a problem's subject is: a node's id is no store's name and no turn's
LANE, UNRECORDED = "lane", "unrecorded"                             # and of a class of SPANS or CLOCK a lane, or of SPANS what no span of the stream covers


@dataclass(frozen=True)
class Problem:
    kind: str               # the class, a key of CLASSES
    subject: str            # the node it is about, a cache being its node's; "memo" for the memo
    subject_is: str         # NODE; STORE for the memo; TURN for a span of the GUI thread's; BETWEEN for the time between rows; LANE; UNRECORDED
    line: str
    ms_row: float | None    # what it cost a row of the walk; of a class of SPANS a row finished over its span, None where none was; of CLOCK None
    share: float | None     # of what the walk's nodes cost
    evidence: tuple         # the lines the figures were drawn from
    source: str             # where in the code the class has come from before
    walk: WalkId | None     # the walk it was found in; None of a class of SPANS
    t: float                # that walk's last progress, on the probe's clock; of a class of SPANS the start of the bucket it was found in; of CLOCK since when it has been so
    says: str = ""          # the class in one sentence, for a user of the player and not a reader of the code
    target: str = ""        # what to act on: a node's fold, a store and what the walk needs of it, a slot
    nodes: tuple = ()       # the nodes it names
    turns: tuple = ()       # the GUI thread's spans it names, as a bucket's `turns` keys them

    @property
    def key(self):
        """What a Log holds one Entry of: the class and the subject as the kind of thing it is, so
        a node whose id is a store's name or a turn's is another subject."""
        return self.kind, self.subject_is, self.subject


def cost(walk):
    """The ms the walk's nodes took, every span of every kind."""
    return sum(r.ms for n in walk.nodes.values() for r in n.runs.values())


def walk_row_ms(walk):
    """What a row of `walk` cost, its nodes' ms and its unprobed over the rows done, of which it has one."""
    return (cost(walk) + walk.unprobed) / walk.done


def unprobed_row_ms(walk):
    """The part of `walk_row_ms` no node ran."""
    return walk.unprobed / walk.done


def realtime_multiple(walk, fps):
    """The rows `walk` did in a second of what they cost, over a clip's `fps`; None for a walk that cost nothing."""
    ms = walk_row_ms(walk)
    return 1000 / ms / fps if ms else None


def bucket_row_ms(bucket, thread):
    """(what a row cost in `bucket` as `walk_row_ms` costs a walk's, `thread`'s ms in nodes and the
    unprobed over the rows the lanes finished, those rows), or None when they finished none. A
    reader's own work on the thread is no node's and is not in it."""
    n = sum(bucket.rows.values())
    ms = sum(bucket.ms.get(thread, {}).values())
    return ((ms + bucket.unprobed) / n, n) if n else None


def resource_shares(name, sample):
    """(SIEVE's share of the whole, everything else's) of memory, cores or disk in one machine
    `sample` of it; the disk's whole is how busy it was, split by the bytes each moved."""
    if name == "disk":
        ours, others, busy = sample
        part = ours / (ours + others) if ours + others else 0.0
        return (busy or 0.0) * part, (busy or 0.0) * (1 - part)
    ours, others, whole = sample
    return ours / whole, others / whole


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


def stores_at(view, t=None):
    """{store: (bytes held, limit)} of the stores there are at the bucket `t` is in or else the
    view's last, by `ledger.stores_after` over the buckets up to it: no one bucket's `stores` is
    every store, and a store a later telling left out is not one."""
    end = len(view.buckets) if t is None else int(t // view.width) - view.first + 1
    out = {}
    for b in view.buckets[:max(end, 0)]:
        if b.stores:
            out = stores_after(out, b.stores)
    return out


_HELD_AS = {RUN: "result", FOLD: "plane", CACHE: "row", DECODE: "row", SEEK: "row"}


def needs(view, walk):
    """What `walk`'s range asks each store to hold, {store: bytes}: for each node the mean bytes of
    a result, of a fold and of a row its cache read, by the latest walk in `view` that made one under
    the node's key, times the range, a static node's result once. What a fold asked for counts by
    the walks of `walk`'s own lane alone, the window's walk folding and the clip's not. It reads
    what was made and no discard, so it stands from a walk's first rows; a store nothing was made
    for is not in it."""
    nodes, out = (walk.plan or {}).get("nodes") or {}, {}
    for nid, key in (walk.keys or {}).items():
        mean = {}
        for w in view.walks:
            if (w.keys or {}).get(nid) != key or nid not in w.nodes:
                continue
            made = {}
            for u, r in w.nodes[nid].runs.items():
                if u.kind in _HELD_AS and (u.demand != "fold" or w.lane == walk.lane):
                    m = made.setdefault(_HELD_AS[u.kind], [0, 0])
                    m[0], m[1] = m[0] + r.count, m[1] + r.bytes
            mean.update({what: b / n for what, (n, b) in made.items() if n and b})
        rows = 1 if (nodes.get(nid) or {}).get("static") else walk.length
        for what, b in mean.items():
            store = key if what == "row" else "memo"
            out[store] = out.get(store, 0) + b * rows
    return out


class Need(NamedTuple):
    """What the range of a lane's last walk asks one store to hold."""
    lane: str | None
    bytes: float
    over: bool          # past the store's limit
    says: str


def asked_of(view):
    """{store: [Need]}, a Need for each lane's last walk in `view` whose range asks the store for
    anything, by `needs`, the lanes in the order each first walked. One past the store's limit
    says what a single pass over the range never shows: the next walk of it makes it all again."""
    stores, out = stores_at(view), {}
    for w in {w.lane: w for w in view.walks}.values():
        for store, n in needs(view, w).items():
            limit = stores.get(store, (0, None))[1]
            over = bool(limit and n > limit)
            again = "computes" if store == "memo" else "decodes"
            out.setdefault(store, []).append(Need(w.lane, n, over, f"the {w.lane or 'walk'} needs {size(n)}"
                                                  + (f", past the limit: its next walk {again} it again" if over else "")))
    return out


def shut(view, walk):
    """Whether `walk` takes no more rows: it has done its range, closed short of it or not, or its lane has begun another."""
    return walk.done >= walk.length or any(w.lane == walk.lane and w.t0 > walk.t0 for w in view.walks)


_UNPROBED = ("unprobed", "row")


def _per(walk):
    """{(node, kind): (the runs, ms a run)} of `walk`, which has a row done, over the kinds in
    COSTS, and under _UNPROBED the ms a row no span covers, a row its run."""
    out = {}
    for nid, node in walk.nodes.items():
        for u, r in node.runs.items():
            if u.kind in COSTS and r.count:
                at = out.setdefault((nid, u.kind), [0, 0.0])
                at[0] += r.count
                at[1] += r.ms
    return {key: (n, ms / n) for key, (n, ms) in out.items()} | {_UNPROBED: (walk.done, walk.unprobed / walk.done)}


def _rows_ran(walk):
    """How cold `walk` was, as a key: the rows each of its nodes ran on."""
    return frozenset((n, x.ran) for n, x in walk.nodes.items() if x.ran)


def _against(base, walk):
    """(what `walk`'s runs cost at `base`'s ms a run, what they cost, [(ms over the walk, ms a run
    in `base`, in `walk`, the runs, node, kind)]) over what `base`, a `_Baseline.of`, and `walk` both
    hold; None when no node ran in both."""
    now = _per(walk)
    moved = [((now[key][1] - base[key]) * now[key][0], base[key], now[key][1], now[key][0], *key) for key in base.keys() & now.keys()]
    if all((n, k) == _UNPROBED for *_, n, k in moved):
        return None
    expected, actual = sum(a * n for _, a, _, n, _, _ in moved), sum(b * n for _, _, b, n, _, _ in moved)
    return (expected, actual, moved) if expected else None


class _Baseline(NamedTuple):
    """What a lane's walks under `keys` and of `length` cost, through the walk begun at `t0`. It is
    of every walk of the lane up to that one and of no other, so it stands when the history drops them."""
    keys: dict | None
    length: int
    t0: float
    ms: dict            # (node, kind) -> ms a run in the latest whole walk in which it ran and which was not slower than this
    between: dict       # `_rows_ran` -> the ms a row no span covered in the latest such walk that cold
    last: tuple | None = None   # ((keys, length), whether replanned) of the walk begun at `t0`

    def of(self, walk):
        """{(node, kind): ms a run} as `_per` keys them, to hold `walk` against: the unprobed among
        them only by a walk as cold as it, a row a store held leaving another time between rows.
        None for a walk under other keys or of another length, or with nothing to hold it against."""
        if (self.keys, self.length) != (walk.keys, walk.length):
            return None
        cold = _rows_ran(walk)
        return (self.ms | ({_UNPROBED: self.between[cold]} if cold in self.between else {})) or None

    def after(self, w):
        """This with `w`, the lane's next walk, taken."""
        last = (w.keys, w.length), w.replanned
        if w.replanned:
            return self._replace(t0=w.t0, last=last)
        b = self if (w.keys, w.length) == (self.keys, self.length) else _Baseline(w.keys, w.length, w.t0, {}, {})
        if 0 < w.length <= w.done and ((c := _against(b.of(w) or {}, w)) is None or c[1] < SLOWER * c[0]):
            per = {key: ms for key, (_, ms) in _per(w).items()}
            return b._replace(t0=w.t0, between=b.between | {_rows_ran(w): per.pop(_UNPROBED)}, ms=b.ms | per, last=last)
        return b._replace(t0=w.t0, last=last)


_NO_BASELINE = _Baseline(None, 0, float("-inf"), {}, {})


@dataclass
class Sofar:
    """What a Log holds of a walk it has not judged for the last time: what the settled buckets
    the walk ran over have shown, and what its classes have found of it."""
    at: int | None = None                           # the first bucket not yet taken; None before any
    both: float = 0.0                               # ms the tools' wait and the GUI thread's turns coincide, the lesser of the two bucket by bucket
    by: dict = field(default_factory=dict)          # a turn -> its ms in the buckets they coincided in
    calls: dict = field(default_factory=dict)       # a slot -> its spans begun over the walk, and under `ms` what they took
    ms: dict = field(default_factory=dict)
    found: dict = field(default_factory=dict)       # class -> the keys of the problems it has shown of the walk, for each class that could judge it
    base: dict | None = None                        # what the walk is held against, a `_Baseline.of`, and `prev`, its lane's walk before it as `_Baseline.last`
    prev: tuple | None = None

    def take(self, view, walk, end):
        """Takes the settled buckets `walk` has run over, through bucket `end` on the probe's clock, each once."""
        lo = max(int(walk.t0 // view.width) if self.at is None else self.at, view.first)
        hi = min(end, int(walk.t1 // view.width), view.first + len(view.buckets) - 1)
        for b in view.buckets[lo - view.first:max(hi + 1 - view.first, 0)]:
            if b.wait > 0 and b.turns:
                self.both += min(b.wait, sum(b.turns.values()))
                for name, ms in b.turns.items():
                    self.by[name] = self.by.get(name, 0.0) + ms
            for name, n in b.calls.items():
                if name.startswith(SLOT + " "):
                    self.calls[name], self.ms[name] = self.calls.get(name, 0) + n, self.ms.get(name, 0.0) + b.turns.get(name, 0.0)
        if hi >= lo:
            self.at = hi + 1


def _comparable(walk, sofar):
    if walk.keys is None or walk.replanned:
        return False
    if sofar.prev is not None and sofar.prev[0] != (walk.keys, walk.length):
        return not sofar.prev[1]
    return 0 < walk.length <= walk.done and sofar.base is not None and _against(sofar.base, walk) is not None


def _signalled(walk, sofar):
    walked = walk.nodes.get((walk.plan or {}).get("walk"))
    return walked is not None and 2 * (walked.ran + walked.served) >= walk.done


# A class -> whether it can say anything of a walk; a class not here can of every one. A walk it
# cannot is no evidence either way: it shows no problem of the class and shows none gone.
JUDGES = {"unread": lambda walk, sofar: walk.plan is not None and not walk.replanned, "grows": lambda walk, sofar: not walk.replanned,
          "slower": _comparable, "signals": _signalled}
WHOLE = ("slower",)     # the classes of a whole walk, judged once and when it takes no more rows


def _problem(kind, walk, subject, line, ms, evidence, says, target, nodes=(), subject_is=NODE, turns=()):
    total = cost(walk)
    return Problem(kind, subject, subject_is, line, ms / walk.done, ms / total if total else None, tuple(evidence), SOURCES[kind],
                   walk.id, walk.t1, says, target, tuple(dict.fromkeys(nodes)), tuple(dict.fromkeys(turns)))


UNREAD = 0.25       # the share of a walk's cost under folds no watched node asked for, at which each is a problem


def unread(view, w, sofar=None):
    """Work no watched node and no walked node asked for: everything under a density's fold of a
    node neither pinned nor selected while the walk ran, the runs and decodes the fold opened with it.
    A span is charged to the fold that opened it, the first to read its node in the document's
    order, so the evidence names the other such folds that would open it were that one gone. A node
    with no fold span under its own fold had no plane to fold, and its line and target say so."""
    out, watched, by = [], {*w.plan["pinned"], *w.selected}, {}
    for nid, node in w.nodes.items():
        for u, r in node.runs.items():
            if u.demand == "fold" and u.asked not in watched:
                by.setdefault(u.asked, []).append((r.ms, r.count, nid, u.kind))
    if sum(r[0] for rs in by.values() for r in rs) < UNREAD * cost(w) or not cost(w):
        return out
    opens = {asked: _through(w.plan.get("nodes") or {}, [asked]) for asked in by}
    for asked, rs in by.items():
        rs.sort(reverse=True)
        what = ", ".join(f"{n} {nid} {kind}" for _, n, nid, kind in rs)
        too = {(nid, kind): "" if kind == FOLD else ", ".join(a for a in by if a != asked and nid in opens[a]) for _, _, nid, kind in rs}
        plane = any(kind == FOLD for *_, kind in rs)
        out.append(_problem("unread", w, asked, (f"{asked}'s density is folded and it is neither pinned nor selected: {what}" if plane else
                                                 f"{asked} is computed for a density and its output is no plane, so none is folded: {what}"),
                            sum(r[0] for r in rs),
                            [f"{nid} {kind} x{n}: {ms:.1f} ms" + (f"; a fold of {too[nid, kind]} opens it too" if too[nid, kind] else "")
                             for ms, n, nid, kind in rs],
                            "Computed on every row and read by nothing",
                            f"the fold of {asked}" if plane else f"{asked}, which has no plane to fold", [r[2] for r in rs]))
    return out


THRASH = 0.25       # recomputations a row of the walk at which a store is a problem


def thrash(view, w, sofar=None):
    """A store computing or decoding again what it had discarded: the memo, or a decoder's cache,
    the plate's under the video node and a served reader's under the served one."""
    out, stores, need = [], stores_at(view, w.t1), None
    for store, n in w.recomputed.items():
        if n < THRASH * w.done:
            continue
        need = needs(view, w) if need is None else need
        node = next((nid for nid, k in (w.keys or {}).items() if k == store), store)
        held = f"; it held {stores[store][0] / 2**20:.1f} of {(stores[store][1] or 0) / 2**20:.1f} MB at the walk's last row" if store in stores else ""
        line = (f"the memo ran again {n} results it had discarded" if store == "memo" else
                f"{node}'s cache decoded again {n} rows it had discarded") + f", over {w.done} rows{held}"
        name = "memo" if store == "memo" else f"{node} cache"
        fits = store in need and store in stores and stores[store][1]
        out.append(_problem("thrash", w, "memo" if store == "memo" else node, line, w.recomputed_ms.get(store, 0.0),
                            [f"{n} recomputations, {w.recomputed_ms.get(store, 0.0):.1f} ms", f"store {store}"],
                            f"The {name} is {'recomputing' if store == 'memo' else 'decoding again'} what it threw out",
                            f"the {w.lane or 'walk'} needs {size(need[store])}, the {name} holds {size(stores[store][1])}"
                            if fits else f"the {name}'s limit", () if store == "memo" else [node],
                            STORE if store == "memo" else NODE))
    return out


GROWS = 3.0         # a node's ms a run over the last quarter of the range it has run in against the first
GROWS_BEFORE = GROWS ** 0.5     # and over the quarter before the last, so one long call at the rows last walked is no growth
GROWS_SHARE = 0.1   # and the share of the walk's cost the growth is, below which it is not a problem


def grows(view, w, sofar=None):
    """A node whose cost a run grows along the range, a chain node run whole over the rows so far
    being the known case; read off the parts of the range its spans fell in, so rows a store held
    are not taken for cheap ones. A walk that went on after a sync is not judged: a node the new
    plan steps again from the range's first row does it all where the walk then stood."""
    out, total = [], cost(w)
    for nid, node in w.nodes.items():
        per = [ms / n for ms, n in zip(node.parts, node.counts) if n]
        k = len(per) // 4
        if not k:
            continue
        first, before, last = sum(per[:k]) / k, sum(per[-2 * k:-k]) / k, sum(per[-k:]) / k
        over = sum(node.parts) - first * sum(node.counts)
        if last < GROWS * first or before < GROWS_BEFORE * first or over < GROWS_SHARE * total or not over:
            continue
        p = ((w.plan or {}).get("nodes") or {}).get(nid) or {}
        whole = "; the plan runs it whole at every emit" if p.get("kind") == "series" and not p.get("steps") else ""
        out.append(_problem("grows", w, nid, f"{nid} costs {last:.2f} ms a run at the last rows walked against {first:.2f} "
                            f"at the range's start{whole}", over, ["ms a run along the range: " + " ".join(f"{x:.2f}" for x in per)],
                            "Costs more a row the further the walk goes",
                            nid + (", run whole at every emit" if whole else ""), [nid]))
    return out


SEEKS = 1           # the seeks a walk may make on one node: the one a walk beginning mid-clip opens with


def seeks(view, w, sofar=None):
    """The walk's cursor seeking, on the plate's decoder or a served reader's."""
    out = []
    for nid, node in w.nodes.items():
        rs = [(u.demand, u.asked, r.count, r.ms) for u, r in node.runs.items() if u.kind == SEEK]
        n = sum(r[2] for r in rs)
        if n > SEEKS:
            out.append(_problem("seeks", w, nid, f"the walk's cursor on {nid} sought {n} times over {w.done} rows",
                                sum(r[3] for r in rs), [f"under the {d} of {a}: {c} seeks, {ms:.1f} ms" for d, a, c, ms in rs],
                                "The walk's reads jump around the file instead of running forward",
                                f"the reads of {nid}", [nid]))
    return out


def slower(view, w, sofar):
    """A whole walk that costs more than its lane's baseline, `sofar.base`, whatever the cause:
    each node's ms a run in what the baseline holds of it, so a walk colder than those before is
    not a slower one, and the ms a row no span covers, under the subject "unprobed"."""
    against = None if sofar.base is None else _against(sofar.base, w)      # with no baseline, another plan or range: there is nothing it is slower than
    if against is None or against[1] < SLOWER * against[0]:
        return []
    expected, actual, moved = against
    moved.sort(reverse=True)
    _, a, b, _, nid, kind = moved[0]
    between = (nid, kind) == _UNPROBED
    return [_problem("slower", w, nid, f"a row costs {actual / w.done:.2f} ms in what ran before under this plan against "
                     f"{expected / w.done:.2f} at what each cost in the lane's last walk that ran it and was not itself slower; {nid} went from {a:.2f} to "
                     f"{b:.2f} ms a {kind}", actual - expected,
                     [f"{n} {k}: {x:.3f} to {y:.3f} ms, {d:+.1f} ms over the walk" for d, x, y, _, n, k in moved],
                     "Slower than it was under the same settings",
                     "the time between rows, in no node" if between else nid,
                     [n for d, _, _, _, n, k in moved if d > 0 and (n, k) != _UNPROBED], BETWEEN if between else NODE)]


WAITS = 0.1         # the tools' waits that coincide with the GUI thread's spans, as a share of the walk's cost
TICK = 16.0         # ms; the CPU clock's step on Windows, see Event.cpu_ms: a walk's wait under one is not a figure


def waits(view, w, sofar):
    """The worker waiting on the GUI thread: over the settled buckets a walk has run over, what its
    tools spent off their own CPU while the GUI thread was in a slot or a paint, the lesser of the
    two in each bucket and no more than the walk's own wait, which is the steadier figure. A read's
    wait is the decoder's threads and is not counted; a tool that sleeps coincides with nothing."""
    both = min(sofar.both, w.wait)
    if not sofar.by or both < max(TICK, WAITS * cost(w)):
        return []
    top = sorted(sofar.by.items(), key=lambda x: -x[1])
    return [_problem("waits", w, top[0][0], f"the walk's tools waited {both:.0f} ms off their CPU while the GUI thread "
                     f"was in its own spans, {top[0][0]} the longest at {top[0][1]:.0f} ms", both,
                     [*(f"{name}: {ms:.1f} ms" for name, ms in top),
                      f"the walk's tools {w.wait:.1f} ms off their CPU, its reads {w.read_wait:.1f}"],
                     "The walk waits while the interface thread is busy",
                     "the " + " ".join(reversed(top[0][0].split(" ", 1))), subject_is=TURN, turns=[top[0][0]])]


SIGNALS = 0.04      # a slot's own spans as a share of the walk's cost, at which one run at most rows is a problem
BRIEF = 1.0         # ms a call; a slot longer than this holds the interpreter and is waits' to find


def signals(view, w, sofar):
    """A slot of the GUI thread's run at one row in two of a walk or oftener, brief each time: a
    worker signal a row, which a walk of short rows pays for at each. The cost is the slot's own
    spans and so the floor: the interpreter changing hands at every call lands in the tools' spans
    and has no figure of its own. Those spans are the GUI thread's and no part of what the walk's
    nodes cost, so the problem has no share. A walk whose walked node the stores held on more than
    half its rows is not judged, being over either way."""
    out = []
    for name, n in sofar.calls.items():
        ms = sofar.ms[name]
        if 2 * n < w.done or ms > BRIEF * n or ms < SIGNALS * cost(w):
            continue
        slot = name.split(" ", 1)[1]
        p = _problem("signals", w, name, f"the {slot} slot ran {n} times over the walk's {w.done} rows, "
                     f"{ms / n * 1000:.0f} us each", ms,
                     [f"{name}: {n} calls, {ms:.1f} ms", f"the walk: {(w.t1 - w.t0) * 1000 / w.done:.3f} ms a row of wall"],
                     "The interface is told of every row, and a row is short enough to feel it",
                     f"how often {slot} is signalled", subject_is=TURN, turns=[name])
        out.append(replace(p, share=None))
    return out


# Each takes a view, one walk of it with PARTS rows done or more that its JUDGES entry passes, and the Log's Sofar of that walk.
CLASSES = {"unread": unread, "thrash": thrash, "grows": grows, "seeks": seeks, "slower": slower, "waits": waits, "signals": signals}


BACK = 8.0          # s behind the bucket it judges that a class of SPANS reads; a ledger's history is never shorter


def _spanned(kind, view, i, subject, subject_is, line, ms, rows, evidence, says, target, nodes=(), turns=()):
    return Problem(kind, subject, subject_is, line, ms / rows if rows else None, None, tuple(evidence), SOURCES[kind], None,
                   i * view.width, says, target, tuple(nodes), tuple(turns))


def _range(view, first, last):
    """(index on the probe's clock, bucket) of the buckets of `view` from index `first` through `last`."""
    lo, hi = max(first - view.first, 0), min(last - view.first, len(view.buckets) - 1)
    return [(view.first + i, view.buckets[i]) for i in range(lo, hi + 1)]


LATE = 100.0        # ms the GUI thread's timer fires late at which a user feels it; what a heavy walk ordinarily leaves is under it
COVERS = 0.5        # the share of a lateness a turn's ms or a node's one call is, at which it is what the GUI thread was late under


def late(view, first, last):
    """The GUI thread late past LATE, with a walk or without one, a problem for each bucket from
    `first` through `last` that sampled it so. Its subject is what the buckets hold over the
    lateness, no further back than BACK: the turn whose ms cover it; else the node one call of
    which, begun before the bucket's end, ran as long on its own CPU, so holding the interpreter;
    else that no span of the stream covers it. Its cost is the lateness over the rows the lanes
    finished across it."""
    out = []
    for i, b in _range(view, first, last):
        if b.late < LATE:
            continue
        at = i - view.first
        back = max(at - math.ceil(min(b.late / 1000, BACK) / view.width), 0)
        over = view.buckets[back:at + 1]
        turns, calls = {}, {}
        for x in over:
            for name, ms in x.turns.items():
                turns[name] = turns.get(name, 0.0) + ms
        for x in view.buckets[back:]:       # a call that held the interpreter is told of as it ends, the sample it made late behind it
            for nid, (ms, cpu, t) in x.longest.items():
                if t < (i + 1) * view.width and cpu >= COVERS * ms and ms > calls.get(nid, 0.0):
                    calls[nid] = ms
        turn, call = max(turns.items(), key=lambda x: x[1], default=("", 0.0)), max(calls.items(), key=lambda x: x[1], default=("", 0.0))
        evidence = [f"late {b.late:.0f} ms", *(f"{name}: {ms:.1f} ms" for name, ms in sorted(turns.items(), key=lambda x: -x[1])),
                    *(f"{nid}: one call of {ms:.0f} ms on its own CPU" for nid, ms in sorted(calls.items(), key=lambda x: -x[1]))]
        says, rows = "The interface thread ran late enough to feel", sum(n for x in over for n in x.rows.values())
        if turn[1] >= COVERS * b.late:
            out.append(_spanned("late", view, i, turn[0], TURN, f"the GUI thread ran {b.late:.0f} ms late with {turn[0]} taking {turn[1]:.0f} ms over it",
                                b.late, rows, evidence, says, "the " + " ".join(reversed(turn[0].split(" ", 1))), turns=[turn[0]]))
        elif call[1] >= COVERS * b.late:
            out.append(_spanned("late", view, i, call[0], NODE, f"the GUI thread ran {b.late:.0f} ms late while one call of {call[0]} ran "
                                f"{call[1]:.0f} ms on its own CPU, holding the interpreter", b.late, rows, evidence, says,
                                f"{call[0]}, one call of which holds the interpreter", nodes=[call[0]]))
        else:
            out.append(_spanned("late", view, i, "nothing recorded", UNRECORDED, f"the GUI thread ran {b.late:.0f} ms late and no span of the "
                                f"stream covers it: its longest turn over it {turn[1]:.0f} ms, the longest call of a node {call[1]:.0f}",
                                b.late, rows, evidence, says, "what the interface thread does under no span"))
    return out


RESTARTS = 3            # the walks of a lane begun by neither a hand nor an edit, inside RESTARTS_OVER seconds, at which they are a problem
RESTARTS_OVER = 2.0
_BEGAN = {ASKED: "an ask that named neither a hand nor an edit", GIVEN: "what the walk was given went stale",
          SHAPE: "the nodes or the shape changed under the walk"}


def restarts(view, first, last):
    """A lane begun again and again by no hand of the user's with few rows finished: for each
    bucket from `first` through `last` in which such a walk began, RESTARTS of them or more over
    the RESTARTS_OVER seconds to it, the lane finishing fewer than PARTS rows a beginning. A begin
    by a hand or an edit is not counted, however many, nor one that says not what began it. Its
    cost is what every node ran over those seconds, over the rows the lane finished."""
    out, k = [], max(round(RESTARTS_OVER / view.width), 1)
    for i, b in _range(view, first, last):
        at = i - view.first
        over = view.buckets[max(at - k + 1, 0):at + 1]
        for lane, began in b.begins.items():
            if all(by in THE_USERS for by in began):
                continue
            by = {}
            for x in over:
                for what, n in x.begins.get(lane, {}).items():
                    if what not in THE_USERS:
                        by[what] = by.get(what, 0) + n
            n, rows = sum(by.values()), sum(x.rows.get(lane, 0) for x in over)
            if n < RESTARTS or rows >= PARTS * n:
                continue
            why = "; ".join(_BEGAN.get(what, what) for what in sorted(by, key=lambda x: -by[x]))
            out.append(_spanned("restarts", view, i, str(lane), LANE, f"the {lane} walk began again {n} times in {len(over) * view.width:.2f} s "
                                f"and finished {rows} rows: {why}", sum(ms for x in over for d in x.ms.values() for ms in d.values()), rows,
                                [f"{_BEGAN.get(what, what)}: {c} beginnings" for what, c in by.items()],
                                "The walk keeps starting over, and nothing the user did began it", f"what begins the {lane} walk again: {why}"))
    return out


# Each takes a view and the indices of the first and the last bucket to judge, and judges no walk.
SPANS = {"late": late, "restarts": restarts}
STILL = 5.0         # s to the last settled bucket's end inside which a problem of a class of SPANS, seen, still holds


STALLS = 5.0        # s a lane being walked may finish no row; docs/findings/2026-11-14-how-long-a-lane-finishes-no-row-with-nothing-wrong.md has the longest seen with nothing wrong


def stalls(view):
    """A lane being walked that has finished no row for STALLS seconds or longer, by
    `View.no_row_since` against `View.now`: a problem for each, its subject the lane, found in the
    lane's walk and with no cost, no row having finished over it. It reads no bucket, so it is
    found with the call that holds the lane still out."""
    out = []
    for lane, since in view.no_row_since.items():
        w, still = next(w for w in reversed(view.walks) if w.lane == lane), view.now - since
        if still < STALLS:
            continue
        at = "its first row" if w.start is None and not w.done else f"row {(w.start or 0) + w.done}"
        out.append(Problem("stalls", str(lane), LANE, f"the {lane} walk has finished no row for {still:.0f} s, {w.done} of its {w.length} done, "
                           "with its thread awake and no other lane's turn taken", None, None,
                           (f"{w.done} of {w.length} rows done", f"no row finished and no other lane's turn taken for {still:.1f} s"),
                           SOURCES["stalls"], w.id, since, "The walk has stopped finishing rows", f"what the {lane} walk is in at {at}"))
    return out


# Each takes a view and judges what it says of now: neither a walk's rows nor a settled bucket.
CLOCK = {"stalls": stalls}


@dataclass
class Entry:
    problem: Problem        # its latest sighting
    first: float            # the first sighting's t
    count: int = 0          # the walks it was seen in; of a class of SPANS the buckets
    holds: bool = True      # whether a walk still walking has shown it or, in any lane, the last walk its class could judge did; of a class of SPANS whether it was seen inside STILL; of CLOCK whether it is found now

    def seen(self):
        """How often it was seen, as written."""
        return f"{self.count} {'time' if self.problem.walk is None else 'walk'}{'s' * (self.count != 1)}"


class Log:
    """The problems the catalogue has surfaced, one Entry per class and subject, by `Problem.key`:
    a fold of the stream, made by the ledger it is the `watch` of, which calls `settled` in the
    stream's order, so the entries are the same whatever history the ledger keeps and whenever it
    is read. A reader takes `copy()`, a view's `found`, and judges nothing.

    A class of `classes` has one reading, of a walk with PARTS rows done as each bucket it has run
    over settles and once more when it takes no more rows and its last bucket has: what it shows at
    any of those is found, and stands; a walk counts once toward an entry. A class of WHOLE is
    judged at the last alone. An entry holds while a walk not yet judged for the last time has
    shown it, or the last walk of any lane that its class could judge did. A class of `spans`
    judges each bucket once, as it settles. A class of `clock` judges what the view says of now,
    each time the ledger says the stream's clock has moved on, `clock`: its entry holds while it
    is found and a walk counts once toward it. `classes` given, `spans` and `clock` are none but
    those given."""

    def __init__(self, classes=None, spans=None, clock=None):
        self.classes = CLASSES if classes is None else classes
        self.spans = (SPANS if classes is None else {}) if spans is None else spans
        self.clocks = (CLOCK if classes is None else {}) if clock is None else clock
        self._clocked = set()   # (a Problem's key, its walk) of each a class of `clocks` has found
        self.entries = {}       # a Problem's key -> Entry
        self.checked = set()    # the classes that have judged a walk or a bucket
        self._spanned = None    # the index of the first bucket no class of `spans` has judged
        self._sofar = {}        # a walk's id -> Sofar, of the walks not judged for the last time
        self._final = set()     # the ids of those that were, while the ledger holds them
        self._held = {}         # (lane, class) -> the keys the lane's last walk the class could judge showed
        self._baselines = {}    # lane -> _Baseline through its last walk judged for the last time

    def back(self, width):
        """The buckets of `width` seconds behind the one it judges that a class may read."""
        return math.ceil(BACK / width) + 1

    def final(self, wid):
        """Whether the walk of id `wid` has been judged for the last time."""
        return wid in self._final

    def settled(self, view, upto=None):
        """Takes into the entries what `view` shows through bucket `upto` on the probe's clock, the
        last settled, or through everything it holds when the stream has ended and `upto` is None."""
        n = len(view.buckets)
        end = view.first + n - 1 if upto is None else min(upto, view.first + n - 1)
        if n and end >= view.first:
            start = view.first if self._spanned is None else self._spanned
            for kind, detect in self.spans.items():
                if start <= end:
                    self.checked.add(kind)
                for p in detect(view, start, end):
                    e = self._sight(p)
                    e.count += 1
            self._spanned = max(end + 1, start)
        for w in view.walks:
            if w.id in self._final or not w.done:
                continue
            s = self._sofar.setdefault(w.id, Sofar())
            s.take(view, w, end)
            final = shut(view, w) and (upto is None or w.t1 // view.width <= upto)
            b = self._baselines.get(w.lane, _NO_BASELINE)
            s.base, s.prev = b.of(w), b.last
            if w.done >= PARTS:
                for kind, detect in self.classes.items():
                    if kind in WHOLE and not final or kind in JUDGES and not JUDGES[kind](w, s):
                        continue
                    self.checked.add(kind)
                    keys = s.found.setdefault(kind, set())
                    for p in detect(view, w, s):
                        e = self._sight(p)
                        if p.key not in keys:
                            keys.add(p.key)
                            e.count += 1
            if final:
                for kind, keys in s.found.items():
                    self._held[w.lane, kind] = keys
                self._baselines[w.lane] = b.after(w)
                self._final.add(w.id)
                del self._sofar[w.id]
        held = {w.id for w in view.walks}
        self._final &= held
        self._sofar = {wid: s for wid, s in self._sofar.items() if wid in held}
        shown = {key for s in self._sofar.values() for keys in s.found.values() for key in keys}
        shown |= {key for keys in self._held.values() for key in keys}
        for key, e in self.entries.items():
            if key[0] in self.spans:
                if n:
                    e.holds = (end + 1) * view.width - e.problem.t <= STILL
            elif key[0] not in self.clocks:
                e.holds = key in shown

    def clock(self, view):
        """Takes into the entries what `view` says of now."""
        for kind, detect in self.clocks.items():
            self.checked.add(kind)
            found = set()
            for p in detect(view):
                e = self._sight(p)
                found.add(p.key)
                if (p.key, p.walk) not in self._clocked:
                    self._clocked.add((p.key, p.walk))
                    e.count += 1
            for key, e in self.entries.items():
                if key[0] == kind:
                    e.holds = key in found
        held = {w.id for w in view.walks}
        self._clocked = {x for x in self._clocked if x[1] in held}

    def _sight(self, p):
        """The entry of `p`, made if it is the first sighting, its problem `p` unless it has a later one."""
        e = self.entries.get(p.key)
        if e is None:
            e = self.entries[p.key] = Entry(p, p.t)
        elif p.t >= e.problem.t:
            e.problem = p
        return e

    def copy(self):
        """A Log of the entries as they now stand, a reader's to hold while this one is told on; it is not one to tell."""
        out = Log(self.classes, self.spans, self.clocks)
        out.entries, out.checked = {key: replace(e) for key, e in self.entries.items()}, set(self.checked)
        return out

    def ordered(self):
        """The entries, the costliest first, and before them those with no cost a row, which rank against none."""
        return sorted(self.entries.values(), key=lambda e: (e.problem.ms_row is not None, -(e.problem.ms_row or 0.0)))


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

    def rate_if_free(self, rate):
        """The walk's multiple of realtime were the node free, `rate` being its multiple now; None when either is not known."""
        return None if self.free is None or rate is None else rate * self.free


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
        ms, n = sum(r.ms for r in node.runs.values()), sum(r.count for r in node.runs.values())
        most = max(node.runs, key=lambda u: node.runs[u].ms)
        kind = most.kind
        bins = node.bins.get(kind) or []
        median, px = quantile(bins, 0.5), None
        if kind == RUN:
            read = [_pixels(view, walk, src) for src in (plan.get(nid) or {}).get("reads", {}).values() if src]
            px = sum(read) if read and None not in read else None
        elif kind in (DECODE, SEEK, CACHE, READ, FOLD):
            px = _pixels(view, walk, nid)
        out[nid] = Row(nid, ms / walk.done, n, kind, most.demand, most.asked, total / (total - ms) if total > ms else None,
                       median, quantile(bins, 0.99), median / (px / 1e6) if median is not None and px else None)
    return out


def reach(plan):
    """The nodes a walk under `plan`, a sync's facts, computes for a row when it folds no density:
    the walked node and what it reads, through to the video or a served node, and the chain."""
    return _through(plan.get("nodes") or {}, [plan.get("walk"), *(plan.get("chain") or ())])


def _through(nodes, starts):
    """`starts` and what they read, by `nodes`, a sync's facts of each node, through to the video or a served node."""
    seen, todo = set(), list(starts)
    while todo:
        nid = todo.pop()
        if nid in nodes and nid not in seen:
            seen.add(nid)
            todo += [s for s in nodes[nid]["reads"].values() if s]
    return seen


_COLD = (RUN, STEP, DECODE, READ)     # what a row nothing holds pays a node; a seek is a walk's opening, a fold the window's and a cache's row one a store held


@dataclass(frozen=True)
class Cold:
    """What a row nothing holds pays one node, from the latest walk in which the node ran."""
    node: str
    ms_row: float           # its ms a run or a read of its file under the walk's own demand, a row being one; a node run whole's over the walk's rows; 0 for a static node, which runs once
    walk: WalkId | None     # the walk the figure is from; None for a static node
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
            ms = sum(r.ms for u, r in node.runs.items() if u.demand == "walk" and u.kind in _COLD) if node else 0.0
            n = sum(r.count for u, r in node.runs.items() if u.demand == "walk" and u.kind in _COLD) if node else 0
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
        nodes[nid] = Cold(nid, ms / (max(w.done, 1) if whole else n), w.id, stale, _growth(w, node) if whole else None)
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
    for what, mine in ((SLOT, False), (PAINT, False), (MONITOR, True)):
        rs = {n: ms for n, ms in by.items() if n.endswith(f" {MONITOR}") == mine and (mine or n.startswith(what))}
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
        stores = stores_at(view, walk.t1)
        held = [f"{store_name(s, view)} {size(n)}" for s, (n, _) in sorted(stores.items(), key=lambda x: -x[1][0]) if n]
        faults = max((b.machine["faults"] for b in seen if b.machine.get("faults") is not None), default=None)
        out.append(Resource("memory", *resource_shares("memory", m), f"{size(ours + others)} of {size(whole)}",
                            f"SIEVE {size(ours)}" + (": " + ", ".join(held) if held else "")
                            + ("" if faults is None else f" · {faults:.0f} hard faults a second"), (ours + others) / whole >= MEMORY))
    if (m := most("cores", lambda m: m[0] + m[1])) is not None:
        ours, others, whole = m
        out.append(Resource("cores", *resource_shares("cores", m), f"{ours + others:.1f} of {whole}", f"SIEVE {ours:.1f}",
                            (ours + others) / whole >= CORES))
    if (m := most("disk", lambda m: (m[2] or 0.0, m[0] + m[1]))) is not None:
        ours, others, busy = m
        out.append(Resource("disk", *resource_shares("disk", m),
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
    mine = _rows_ran(walk)
    return [walk_row_ms(w) for w in view.walks
            if w.lane == walk.lane and w.keys == walk.keys and w.length == walk.length and w.done >= w.length
            and not w.replanned and _rows_ran(w) == mine]
