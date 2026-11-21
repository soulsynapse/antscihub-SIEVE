"""What the held runs are to a plan's walks, apart from the window: a chain as held.Runs is told it,
held results as the worker is given them, what the runs hold of each cut in time, a walked
period's results as the run they are held as, what the window shows of each period it overlaps and
of the one holding a row, and the result a cutting node is cut by. No Qt; the window composes it with the worker."""
from typing import NamedTuple

from . import held, wire
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


def held_periods(p, runs):
    """What the held.Runs `runs` hold of each cut in time of the Plan `p`, as Worker.give_periods takes it."""
    out = {}
    for w in p.timed:
        sub, chain = p.of(w), held_chain(p, w.chain)
        src, stacks = p.entries[w.heads[0]].src, [(q.walk, stacked_key(q)) for q in sub.parts()]
        for c in w.cuts:
            s, e = c.extent.rows
            if e <= s:
                continue
            spared = runs.over(s, e - s, chain, (s, e), (s, e)) is not None
            given = {} if spared else as_given(p, runs.part(s, e - s, chain, (s, e), (s, e)))
            handed = {} if spared else {
                walked: rows for walked, key in stacks if key is not None
                and (rows := runs.walked_rows(walked, key, sub.entries[walked].reach, s, e - s, (s, e), (s, e)))[0].any()}
            out[(src, (s, e))] = HeldCut(period_keys(sub), spared, given, handed or None)
    return out


def period_run(p, results, start, of):
    """The PeriodRun `periodReady`'s `results` from `start` over the cut `of`, (the node its walk
    reads, the cut.Record), are held as under the Plan `p`; None where `p` has no such cut, or the
    results are not every chain node's over the cut whole."""
    walked_node, cut = of
    has = {nid: r for nid, r in results.items() if isinstance(r, dict) and "signal" in r}
    rows = max((len(r["signal"]) for r in has.values()), default=0)
    w = next((w for w in p.timed if p.entries[w.heads[0]].src == walked_node and cut in w.cuts), None)
    if w is None or not rows or set(has) != set(w.chain) or cut.extent.rows != (start, start + rows):
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
    run = next((run for run in runs if run.cut == rows and (run.start, run.start + run.rows) == rows
                and held.good(run.results.get(src), key)), None)
    return None if run is None else run.results[src]


def window_periods(p, runs, s, n):
    """What the window of `n` rows from `s` shows of each cut in time of the Plan `p` it overlaps:
    (the node its walk reads, the cut.Record) to its Shown. A cut whose every chain node the
    held.Runs `runs` serve over the whole cut, as the worker's give_periods is told it, is that walk
    over the window's rows; another is the window's own walk of it, as walk.window_legs has it, its
    results {} until the worker's windowPeriodReady hands them."""
    out = {}
    for leg in window_legs(p, s, n):
        c = leg.cut
        w = next(w for w in p.timed if c in w.cuts and p.entries[w.heads[0]].src == leg.walked)
        first, end = c.extent.rows
        lo, hi = max(first, s), min(end, s + n)
        chain = held_chain(p, w.chain)
        if runs.over(first, end - first, chain, (first, end), (first, end)) is not None:
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
