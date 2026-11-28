"""What the held runs are to a plan's walks, apart from the window: a chain as held.Runs is told it,
held results as the worker is given them, what the runs hold of each cut in time and list of a node's, a walked
period's results as the run they are held as, what the window shows of each period it overlaps and
of the one holding a row, and the result a cutting node is cut by, held or as the window walked it.
No Qt; the window composes it with the worker."""
from typing import NamedTuple

import numpy as np

from . import held, wire
from .cut import among, touching
from .walk import WALKED, HeldCut, period_keys, stacked_key, window_legs


class PeriodRun(NamedTuple):
    """A walked period's results as held.Runs.hold takes them: `walked` each walked node's rows, or None."""
    start: int
    rows: int
    results: dict
    chain: held.Chain
    cut: tuple
    walked: tuple | None


class Shown(NamedTuple):
    """What the window shows of one period: the row its results begin at, the results, the chain
    nodes best effort there, and whether they are the period's walk held."""
    start: int
    results: dict
    best: frozenset
    held: bool


def held_chain(p, nodes):
    """`nodes` of the Plan `p` as held.Runs is told a chain, a node `p` lacks left out."""
    entries = {nid: p.entries[nid] for nid in nodes if nid in p.entries}
    return held.Chain({nid: e.key for nid, e in entries.items()}, frozenset(nid for nid, e in entries.items() if e.steps),
                      {nid: e.reach for nid, e in entries.items()})


def as_given(p, part):
    """`part`, node to held result, as the worker takes it under the Plan `p`: node to (raw key,
    the result's fields as the tool made them, without what the player put beside them, what it
    says it was made under)."""
    return {nid: (p.entries[nid].raw_key, {f: v for f, v in r.items() if f not in ("gate", "key", "code")}, r.get("code"))
            for nid, r in part.items()}


def held_periods(p, runs, was=None, moved=None):
    """What the held.Runs `runs` hold of each cut in time of the Plan `p`, as Worker.give_periods
    takes it. `was` is what it answered of this same Plan, the same object, and of runs since
    changed by `moved` alone, the rows Runs.hold returned: a cut holding no row of those is as
    `was` has it, and the answer costs the cuts that hold one. A provisional cut has nothing held."""
    again = was is not None and moved is not None
    out = dict(was) if again else {}
    for w in p.timed:
        sub, chain = p.of(w), held_chain(p, w.chain)
        src, stacks = p.entries[w.heads[0]].src, [(q.walk, stacked_key(q)) for q in sub.parts()]
        keys = period_keys(sub)
        for c in [w.cuts[i] for i in touching(w.cuts, moved)] if again else w.cuts:
            s, e = c.extent.rows
            if e <= s or c.provisional:
                continue
            spared = runs.over(s, e - s, chain, (s, e), (s, e)) is not None
            given = {} if spared else as_given(p, runs.part(s, e - s, chain, (s, e), (s, e)))
            handed = {} if spared else {
                walked: rows for walked, key in stacks if key is not None
                and (rows := runs.walked_rows(walked, key, sub.entries[walked].reach, s, e - s, (s, e), (s, e)))[0].any()}
            out[(src, (s, e))] = HeldCut(keys, spared, given, handed or None)
    return out


def touched_periods(p, moved):
    """The cuts in time of the Plan `p` holding a row of `moved`, the rows Runs.hold returned, each
    as held_periods keys it."""
    return [(p.entries[w.heads[0]].src, w.cuts[i].extent.rows) for w in p.timed for i in touching(w.cuts, moved)]


def listed_cuts(runs, nid, chain, cuts, count, was=None, moved=None):
    """`nid`'s values in each cut.Record of `cuts`, a held.Listed each as Runs.listed answers under
    `chain` and the footage's `count` rows. `was` is what it answered of these same `cuts`, the
    same tuple, and of runs since changed by `moved` alone, as held_periods takes them: a cut
    holding no row of those is as `was` has it."""
    if was is None or moved is None or len(was) != len(cuts):
        return [runs.listed(nid, chain, c, count) for c in cuts]
    out = list(was)
    for i in touching(cuts, moved):
        out[i] = runs.listed(nid, chain, cuts[i], count)
    return out


def period_run(p, results, start, of):
    """The PeriodRun `periodReady`'s `results` from `start` over the cut `of`, (the node its walk
    reads, the cut.Record), are held as under the Plan `p`; None where `p` has no such cut, it is
    provisional, or the results are not every chain node's over the cut whole."""
    walked_node, cut = of
    has = {nid: r for nid, r in results.items() if isinstance(r, dict) and "signal" in r}
    rows = max((len(r["signal"]) for r in has.values()), default=0)
    w = next((w for w in p.timed if p.entries[w.heads[0]].src == walked_node and among(cut, w.cuts)), None)
    if w is None or cut.provisional or not rows or set(has) != set(w.chain) or cut.extent.rows != (start, start + rows):
        return None
    folds = {q.walk: q.fold for q in p.of(w).parts()}
    walked = tuple((*stack, sum(wire.nbytes(None if folds[stack[0]] is not None else p.entries[stack[0]].produces, r) for r in stack[2]))
                   for stack in results.get(WALKED, ()) if len(stack[2]) == rows and stack[0] in folds)
    return PeriodRun(start, rows, has, held_chain(p, w.chain), (start, start + rows), walked or None)


def gate_result(runs, src, key, within, count):
    """The result of `src`, the node wired into a cutting node's CUT_BY input, under `key` over the
    cut.Record `within`, as plan.plan's cut_result answers it of the held.Runs `runs`: a run's from
    row 0 reaching the footage's `count` rows, or for a cut in time a run of that cut walked whole;
    None with none."""
    rows = within.extent.rows
    if rows is None:
        run = runs.from_first_row(src, key)
        return run.results[src] if run is not None and run.rows >= count else None
    run = next((run for run in runs.of_cut(rows) if held.good(run.results.get(src), key)), None)
    return None if run is None else run.results[src]


def window_gate_result(results, start, shown, src, key, within):
    """(the result of `src` under `key` over the cut.Record `within`, the footage rows it is over)
    as the window walked it: for a `within` of every row its own walk's `results` from `start`,
    and for a cut in time what `shown`, as window_periods answers, has of that cut. None where the
    window has no such result."""
    if within.extent.rows is not None:
        rows = within.extent.rows       # compared first: a record's equality reads every cut it was made from
        of = next((v for (_, c), v in shown.items() if c.extent.rows == rows and c == within and held.good(v.results.get(src), key)), None)
        start, results = (of.start, of.results) if of is not None else (start, {})
    r = results.get(src)
    return (r, (start, start + len(r["signal"]))) if held.good(r, key) else None


def cuts_alike(a, b):
    """Whether the results `a` and `b` of one node, either None, cut a node they are wired into
    alike: one key, and the signal and the gate of one equal to the other's."""
    if a is None or b is None or a.get("key") != b.get("key"):
        return False

    def equal(f):
        x, y = a.get(f), b.get(f)
        if x is None or y is None:
            return x is y
        x, y = np.asarray(x), np.asarray(y)
        return x.shape == y.shape and bool(np.array_equal(x, y, equal_nan=x.dtype.kind == "f" and y.dtype.kind == "f"))
    return equal("signal") and equal("gate")


def walked_before(shown, was, key_of):
    """`shown`, as window_periods answers, with what `was`, an earlier answer, has of the window's
    own walk of a cut both show from one row, under the keys `key_of` answers of its nodes now: a
    plan moved under other cuts leaves what the window walked of this one."""
    out = dict(shown)
    for of, v in shown.items():
        had = was.get(of)
        if had is not None and not v.held and not had.held and had.start == v.start and not v.results:
            out[of] = v._replace(results={nid: r for nid, r in had.results.items() if held.good(r, key_of(nid))})
    return out


def window_periods(p, runs, s, n):
    """What the window of `n` rows from `s` shows of each cut in time of the Plan `p` it overlaps:
    (the node its walk reads, the cut.Record) to its Shown. A cut whose every chain node the
    held.Runs `runs` serve over the whole cut, as the worker's give_periods is told it, is that walk
    over the window's rows; another, and every provisional one, is the window's own walk of it, as
    walk.window_legs has it, its results {} until the worker's windowPeriodReady hands them."""
    out = {}
    for leg in window_legs(p, s, n):
        c = leg.cut
        w = next(w for w in p.timed if among(c, w.cuts) and p.entries[w.heads[0]].src == leg.walked)
        first, end = c.extent.rows
        lo, hi = max(first, s), min(end, s + n)
        chain = held_chain(p, w.chain)
        if not c.provisional and runs.over(first, end - first, chain, (first, end), (first, end)) is not None:
            out[(leg.walked, c)] = Shown(lo, runs.over(lo, hi - lo, chain, (first, end), (first, end)), frozenset(), True)
        else:
            out[(leg.walked, c)] = Shown(leg.first, {}, leg.best, False)
    return out


def shown_at(shown, row):
    """Node to (its result, the row it begins at) over the period holding `row` among `shown`, as
    window_periods answers; the first such period's where two hold it."""
    out = {}
    for v in shown.values():
        for nid, r in v.results.items():
            if nid not in out and isinstance(r, dict) and "signal" in r and v.start <= row < v.start + len(r["signal"]):
                out[nid] = (r, v.start)
    return out
