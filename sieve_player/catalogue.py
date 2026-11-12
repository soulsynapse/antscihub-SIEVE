r"""The catalogue: the detectors, each a function from a ledger's view to the problems it shows, and the
log, one entry per class and subject. A problem's cost is ms a row of the walk it was found in, so
problems rank against each other and against the walk. A class is entered with a simulation of its
name in dev/simulations.py, which proves it fires alone. No graph is held and no Qt reached; an
entry's text takes what the stream does not carry, the document and the decoder's facts, as a dict.

    .venv\Scripts\python -m sieve_player.catalogue dump.jsonl
"""
import json
import sys
from dataclasses import dataclass

from .ledger import replay

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


def cost(walk):
    """The ms the walk's nodes took, every span of every kind."""
    return sum(r[1] for n in walk.nodes.values() for r in n.runs.values())


def finished(view):
    """The walks a detector judges: every walk its lane has begun another after, and a lane's last
    once it has done its range."""
    last = {w.lane: w for w in view.walks}
    return [w for w in view.walks if w.done and (w is not last[w.lane] or w.done >= w.length)]


def _problem(kind, walk, subject, line, ms, evidence):
    total = cost(walk)
    return Problem(kind, subject, line, ms / walk.done, ms / total if total else None, tuple(evidence), SOURCES[kind],
                   (walk.lane, walk.t0), walk.t1)


UNREAD = 0.25       # the share of a walk's cost under folds no pinned node asked for, at which each is a problem


def unread(view):
    """Work no watched node and no walked node asked for: everything under a density's fold of a
    node that is not pinned, the runs and decodes the fold opened with it. The selection is not in
    the stream, so a selected node's fold reads as unwatched."""
    out = []
    for w in finished(view):
        if w.plan is None or w.replanned:
            continue
        watched, by = set(w.plan["pinned"]), {}
        for nid, node in w.nodes.items():
            for (kind, demand, asked), (n, ms, _) in node.runs.items():
                if demand == "fold" and asked not in watched:
                    by.setdefault(asked, []).append((ms, n, nid, kind))
        if sum(r[0] for rs in by.values() for r in rs) < UNREAD * cost(w) or not cost(w):
            continue
        for asked, rs in by.items():
            rs.sort(reverse=True)
            what = ", ".join(f"{n} {nid} {kind}" for _, n, nid, kind in rs)
            out.append(_problem("unread", w, asked, f"{asked}'s density is folded and no pinned node shows it: {what}",
                                sum(r[0] for r in rs), [f"{nid} {kind} x{n}: {ms:.1f} ms" for ms, n, nid, kind in rs]))
    return out


THRASH = 0.25       # recomputations a row of the walk at which a store is a problem


def thrash(view):
    """A store computing or decoding again what it had discarded: the memo, or a decoder's cache,
    the plate's under the video node and a served reader's under the served one."""
    out = []
    for w in finished(view):
        at = int(w.t1 // view.width) - view.first
        stores = view.buckets[at].stores if 0 <= at < len(view.buckets) else {}
        for store, n in w.recomputed.items():
            if n < THRASH * w.done:
                continue
            node = next((nid for nid, k in (w.keys or {}).items() if k == store), store)
            held = f"; it held {stores[store][0] / 2**20:.1f} of {(stores[store][1] or 0) / 2**20:.1f} MB at the walk's end" if store in stores else ""
            line = (f"the memo ran again {n} results it had discarded" if store == "memo" else
                    f"{node}'s cache decoded again {n} rows it had discarded") + f", over {w.done} rows{held}"
            out.append(_problem("thrash", w, "memo" if store == "memo" else node, line, w.recomputed_ms.get(store, 0.0),
                                [f"{n} recomputations, {w.recomputed_ms.get(store, 0.0):.1f} ms", f"store {store}"]))
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
                                f"at its start{whole}", over, ["ms a run along the range: " + " ".join(f"{x:.2f}" for x in per)]))
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
                                    sum(r[3] for r in rs), [f"under the {d} of {a}: {c} seeks, {ms:.1f} ms" for d, a, c, ms in rs]))
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
                            [f"{n} {k}: {x:.3f} to {y:.3f} ms, {d:+.1f} ms over the walk" for d, x, y, _, n, k in moved]))
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
        i0, i1 = (int(t // view.width) - view.first for t in (w.t0, w.t1))
        both, by = 0.0, {}
        for b in view.buckets[max(i0, 0):max(i1 + 1, 0)]:
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
                             f"the walk's tools {w.wait:.1f} ms off their CPU, its reads {w.read_wait:.1f}"]))
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
                                    f"overlaid {w.plan['over']}, pinned {w.plan['pinned']}"))
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
