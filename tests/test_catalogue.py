"""The catalogue: each class read off a view, each simulation surfacing its class alone, the log and an entry's text."""
import json
import time
from dataclasses import replace

import pytest

from sieve_player import document as D
from sieve_player.catalogue import CLASSES, CLOCK, SOURCES, SPANS, STALLS, Log, cold, reach, stores_at, thrash, unread
from sieve_player.dev.simulations import HEALTHY, SIMULATIONS, run
from sieve_player.graph import Graph
from sieve_player.ledger import Bucket, Ledger, Node, Total, Under, View, Walk
from sieve_player.report import report, text
from tests.test_graph import TOOLS, Dec, gray, tool
from tests.test_ledger import event, walk

PLAN = {"nodes": {}, "chain": [], "walk": "b", "shown": "b", "over": None, "pinned": []}


def runs(by):
    return {Under(*u): Total(*r) for u, r in by.items()}


def rec(t0=0.0, keys=None, **nodes):
    """A finished window walk of eight rows whose nodes are `nodes`, each a Node or its runs."""
    nodes = {n: v if isinstance(v, Node) else Node(runs=runs(v)) for n, v in nodes.items()}
    return Walk("window", 0, 8, PLAN, keys, t0, t0 + 0.5, done=8, nodes=nodes)


def seen(view):
    """What a Log told of the whole of `view`, as of a stream that has ended, holds: {(class, subject): Entry}, the costliest first."""
    log = Log()
    log.settled(view)
    return {(e.problem.kind, e.problem.subject): e for e in log.ordered()}


def found(*walks, pinned=()):
    for w in walks:
        w.plan = PLAN | {"pinned": list(pinned)}
    return seen(View(0.25, 0, [], list(walks)))


FOLDED = {"a": {("run", "fold", "a"): [8, 8.0, 0], ("fold", "fold", "a"): [8, 1.0, 0]}, "b": {("run", "walk", "b"): [8, 8.0, 0]}}
SOUGHT = {"video": {("seek", "walk", "b"): [3, 6.0, 0], ("decode", "walk", "b"): [5, 5.0, 0]}}
GROWN = {"c": Node(runs=runs({("run", "walk", "c"): [8, 20.0, 0]}), parts=[1.0] * 4 + [4.0] * 4, counts=[1] * 8)}


def test_each_class_reads_off_a_view_built_by_hand():
    (key, e), = found(rec(**FOLDED)).items()
    p = e.problem
    assert key == ("unread", "a") and (p.ms_row, p.share, p.walk, p.source) == (9 / 8, 9 / 17, ("window", 0.0), SOURCES["unread"])
    assert "a run" in p.line and len(p.evidence) == 2 and not found(rec(**FOLDED), pinned=["a"])
    selected = rec(**FOLDED)
    selected.selected = ["a"]
    assert not found(selected)                                                                  # watched by the selection as by a pin
    assert not found(rec(a=FOLDED["a"], b={("run", "walk", "b"): [8, 80.0, 0]}))                # under the threshold
    both = rec(v={("decode", "fold", "a"): [8, 4.0, 0]}, a=FOLDED["a"], t={("run", "fold", "t"): [8, 8.0, 0]})
    both.plan = PLAN | {"nodes": {"v": {"reads": {}}, "a": {"reads": {"in": "v"}}, "t": {"reads": {"in": "a"}}}}
    a, t = unread(View(0.25, 0, [], [both]), both)
    assert [" t " in x for x in a.evidence] == [True, True, False]                             # the run and the decode t's fold would open, not a's own fold
    assert "no plane" in t.line and "no plane" in t.target and "no plane" not in a.line        # t ran under its fold and folded nothing
    thrashed = rec(keys={"video": "kv"}, b={("run", "walk", "b"): [8, 8.0, 0]})
    thrashed.recomputed, thrashed.recomputed_ms = {"memo": 8, "kv": 4, "other": 1}, {"memo": 4.0, "kv": 2.0, "other": 1.0}
    assert {k: e.problem.ms_row for k, e in found(thrashed).items()} == {("thrash", "memo"): 0.5, ("thrash", "video"): 0.25}
    (key, e), = found(rec(**GROWN)).items()
    assert key == ("grows", "c") and e.problem.ms_row == 12 / 8 and e.problem.share == 12 / 20
    assert not found(rec(c=Node(runs=GROWN["c"].runs, parts=[0.0] * 4 + [5.0] * 4, counts=[0] * 4 + [1] * 4)))     # held, then run: flat
    under_way = rec(c=Node(runs=GROWN["c"].runs, parts=[0.0] * 2 + [5.0] * 2 + [0.0] * 4, counts=[0] * 2 + [1] * 2 + [0] * 4))
    under_way.length = 16
    assert not found(under_way)                                                                 # nor short of its range, held then run over the half it has done
    assert not found(replace(rec(**GROWN), unprobed=200.0))                                     # nor is a growth that is little of what the walk took, most of it between rows
    stepped_again = rec(**GROWN)
    stepped_again.replanned = True
    assert not found(stepped_again)                                                             # a plan changed under it is no growth
    (key, e), = found(rec(**SOUGHT)).items()
    assert key == ("seeks", "video") and e.problem.ms_row == 6 / 8
    assert not found(rec(video={("seek", "walk", "b"): [1, 6.0, 0]}))                           # the one a walk opens with
    run_b = lambda ms: {("run", "walk", "b"): [8, ms, 0]}     # noqa: E731
    (key, e), = found(rec(keys={"b": "k"}, b=run_b(8.0)), rec(1.0, {"b": "k"}, b=run_b(16.0), held={("cache", "walk", "b"): [8, 0.0, 0]})).items()
    assert key == ("slower", "b") and e.problem.ms_row == 1.0 and e.problem.walk == ("window", 1.0)
    late = rec(1.0, {"b": "k"}, b=run_b(8.0))
    late.unprobed = 16.0
    assert list(found(rec(keys={"b": "k"}, b=run_b(8.0)), late)) == [("slower", "unprobed")]
    assert not found(rec(keys={"b": "k"}, b=run_b(8.0)), rec(1.0, {"b": "k2"}, b=run_b(16.0)))  # another plan
    stays = found(*(rec(float(i), {"b": "k"}, b=run_b(ms)) for i, ms in enumerate((8.0, 16.0, 16.0))))[("slower", "b")]
    assert (stays.count, stays.holds, stays.problem.walk) == (2, True, ("window", 2.0))         # a slowdown that stays is still one
    chain = {("run", "walk", "c"): [8, 8.0, 0]}
    held = found(rec(keys={"b": "k"}, b=run_b(8.0), c=chain), rec(1.0, {"b": "k"}, c=chain), rec(2.0, {"b": "k"}, b=run_b(16.0), c=chain))
    assert list(held) == [("slower", "b")] and held[("slower", "b")].problem.walk == ("window", 2.0)    # a walk b was held in is no baseline of b's
    cold = [replace(rec(t, {"b": "k"}, b=Node(runs=runs(run_b(8.0)), ran=8)), unprobed=16.0) for t in (0.0, 2.0)]
    assert not found(cold[0], rec(1.0, {"b": "k"}, b=Node(held=8)), cold[1])                    # nor is one all held a baseline of the time between a cold walk's rows
    told = View(0.25, 0, [Bucket(stores={"memo": (1, 9), "gone": (5, 9), "window stack": (2, 9)}), Bucket(stores={"memo": (3, 9), "clip stack": (4, 9)})], [])
    assert stores_at(told) == {"memo": (3, 9), "window stack": (2, 9), "clip stack": (4, 9)} and "clip stack" not in stores_at(told, 0.1)
    assert {kind for _, kind in SIMULATIONS.values()} == {*CLASSES, *SPANS, *CLOCK} == set(SOURCES)
    quiet = [Bucket(), Bucket()]
    felt = View(0.25, 0, [Bucket(), Bucket(late=300.0, turns={"slot walked": 200.0}, rows={"window": 4}), *quiet,
                          Bucket(late=300.0, longest={"b": [250.0, 240.0, 1.0]}), *quiet, Bucket(late=300.0, longest={"b": [250.0, 10.0, 1.75]}),
                          Bucket(late=99.0), Bucket(late=500.0), Bucket()], [])     # under a turn, under one call on its own CPU, under one that waited; unfelt; the last two not judged
    assert [(p.key, p.ms_row, p.t) for p in SPANS["late"](felt, 0, 8)] == [(("late", "turn", "slot walked"), 75.0, 0.25), (("late", "node", "b"), None, 1.0),
                                                            (("late", "unrecorded", "nothing recorded"), None, 1.75)]
    begun = [Bucket(begins={"window": {"asked": 2, "hand": 9}}, rows={"window": 8}), Bucket(begins={"window": {"given": 1}}, rows={"window": 4}),
             Bucket(begins={"window": {"hand": 5, "edit": 5}}), Bucket(), Bucket()]
    (p,) = SPANS["restarts"](View(0.25, 0, begun, []), 0, 2)       # two by no hand are under it, the third is it, and a hand's and an edit's are none however many
    assert (p.key, p.t, p.walk) == (("restarts", "lane", "window"), 0.25, None) and "3 times in 0.50 s and finished" in p.line and "went stale" in p.target
    assert all(q.says and q.target for q in (p, *SPANS["late"](felt, 0, 8)))
    assert not SPANS["restarts"](View(0.25, 0, [begun[0], replace(begun[1], rows={"window": 24}), *begun[2:]], []), 0, 2)      # rows enough finished a beginning
    turned = rec(b={("run", "walk", "b"): [8, 100.0, 0]})
    turned.wait = 80.0
    waited = View(0.25, 0, [Bucket(wait=40.0, turns={"slot walked": 60.0, "paint plot": 5.0})] * 2, [turned])
    assert not seen(View(0.25, 0, [Bucket(wait=40.0, turns={"slot walked": 60.0}, calls={"slot walked": 100})] * 2, [turned]))     # a slot brief at each call is signals' and no wait
    told = rec(b=Node(runs=runs(run_b(8.0)), ran=8))
    signalled = View(0.25, 0, [Bucket(turns={"slot clipWalked": 0.5, "slot seriesReady": 9.0}, calls={"slot clipWalked": 4, "slot seriesReady": 1})] * 2, [told])
    assert not seen(View(0.25, 0, signalled.buckets, [rec(b=Node(runs=runs(run_b(8.0)), held=8))]))        # a walk the stores held
    assert [e.problem.share for e in seen(signalled).values()] == [None]                                   # the GUI thread's ms, none of the walk's nodes'
    said = {k: (e.problem.says, e.problem.target, e.problem.nodes) for views in (
        [rec(**FOLDED)], [thrashed], [rec(**GROWN)], [rec(**SOUGHT)], [rec(keys={"b": "k"}, b=run_b(8.0)), late], waited, signalled)
        for k, e in (found(*views) if isinstance(views, list) else seen(views)).items()}
    assert {k[0] for k in said} == set(CLASSES) and all(says and target for says, target, _ in said.values())
    assert said[("unread", "a")] == ("Computed on every row and read by nothing", "the fold of a", ("a",))
    assert said[("thrash", "video")][1:] == ("the video cache's limit", ("video",)) and said[("thrash", "memo")][2] == ()
    assert said[("waits", "slot walked")][1:] == ("the walked slot", ()) and seen(waited)[("waits", "slot walked")].problem.turns == ("slot walked",)
    assert said[("signals", "slot clipWalked")][1:] == ("how often clipWalked is signalled", ()) and seen(signalled)[("signals", "slot clipWalked")].problem.turns == ("slot clipWalked",)
    named = rec(keys={"memo": "km"}, b={("run", "walk", "b"): [8, 8.0, 0]})     # a node whose id is a reader's own name is still a node
    named.recomputed, named.recomputed_ms = {"memo": 8, "km": 8}, {"memo": 4.0, "km": 4.0}
    assert {p.key for p in thrash(View(0.25, 0, [], [named]), named)} == {("thrash", "store", "memo"), ("thrash", "node", "memo")}
    p = found(rec(keys={"b": "k"}, unprobed=run_b(8.0)), rec(1.0, {"b": "k"}, unprobed=run_b(16.0)))[("slower", "unprobed")].problem
    assert (p.key, p.target, p.nodes) == (("slower", "node", "unprobed"), "unprobed", ("unprobed",))
    assert said[("slower", "unprobed")][1:] == ("the time between rows, in no node", ())


def test_the_log_holds_one_entry_a_class_and_subject_counted_cleared_and_ordered():
    quiet = {"video": {("decode", "walk", "b"): [8, 8.0, 0]}}
    walks, log = [rec(float(i), **SOUGHT) for i in range(10)], Log()
    for _ in range(2):      # told of the same walks again, it counts none twice
        log.settled(View(0.25, 0, [], walks))
    (e,) = log.ordered()
    assert (e.count, e.holds, e.first) == (10, True, 0.5)
    walks.append(rec(10.0, **quiet))
    log.settled(View(0.25, 0, [], walks))
    assert log.ordered() == [e] and (e.count, e.holds, e.problem.walk) == (10, False, ("window", 9.0))
    again, clip, clean = rec(11.0, **SOUGHT), rec(12.0, **SOUGHT), rec(13.0, **quiet)
    clip.lane = clean.lane = "clip"
    walks += [again, clip, clean]
    log.settled(View(0.25, 0, [], walks))
    assert (e.count, e.holds, e.problem.walk) == (12, True, ("clip", 12.0))       # cleared in one lane, it holds by another's last walk
    short = rec(14.0, **SOUGHT)
    short.done = 2
    walks += [short, rec(15.0, **quiet)]
    log.settled(View(0.25, 0, [], walks))
    assert (e.count, e.holds) == (12, False)     # a walk of two rows is not judged
    walks.append(rec(16.0, **SOUGHT))
    log.settled(View(0.25, 0, [], walks))
    log.settled(View(0.25, 0, [], [clip, clean]))
    assert (e.count, e.holds) == (13, True)      # its walk gone from the history, no walk has shown it gone
    assert "WALK     no longer in the history" in report([e], View(0.25, 0, [], [clip, clean]))      # and no other walk is shown as its
    def told():     # one walk of 32 rows, a tenth of a second each, the first four run again after the memo discarded them
        yield event("begin", 0.0, row=0, length=32)
        for r in range(32):
            if r < 4:
                yield event("evict", r / 10, row=r, key="k")
            yield event("run", r / 10, 1.0, "b", r, key="k", demand="walk", asked="b")
            yield event("progress", (r + 1) / 10, row=r + 1, length=32, facts={})

    led, half = Ledger(watch=Log()), None
    for ev in told():
        led.event(ev)
        if ev.kind == "progress" and ev.row == 16:
            half = led.view()       # under way and short of its range: found of the rows it has
    led.end()
    ended, key = led.view(), ("thrash", "store", "memo")
    assert [w.done for w in (*half.walks, *ended.walks)] == [16, 32] and list(half.found.entries) == list(ended.found.entries) == [key]
    assert [(v.found.entries[key].count, v.found.entries[key].holds) for v in (half, ended)] == [(1, True), (1, True)]     # the rest ran clean: it stands, the walk counted once
    whole = rec(21.0, {"b": "k"}, b={("run", "walk", "b"): [8, 16.0, 0]})
    whole.length = 16
    log, view = Log(), View(0.25, 0, [], [rec(19.0, {"b": "k"}, b={("run", "walk", "b"): [8, 8.0, 0]}), whole])
    log.settled(view, 0)
    assert not log.entries                       # slower is of a whole walk, and says nothing of one under way
    five = rec(keys={"video": "kv"}, a={("run", "fold", "a"): [8, 20.0, 0]}, **SOUGHT, **GROWN)
    five.recomputed, five.recomputed_ms = {"memo": 8, "kv": 4}, {"memo": 4.0, "kv": 2.0}
    assert list(found(five)) == [("unread", "a"), ("grows", "c"), ("seeks", "video"), ("thrash", "memo"), ("thrash", "video")]     # by cost


@pytest.mark.parametrize("kept", [2, 64])
def test_the_log_is_a_fold_of_the_stream_whatever_the_ledger_keeps_and_whenever_it_is_read(kept):
    """One stream into four ledgers, of a long history and of the shortest, each read after every
    event and not until the stream has ended, keeping `kept` walks: the entries are equal, those of
    the classes that judge no walk among them."""
    def told(walks):
        t = 0.0
        yield event("wake", t, lane=None)
        for i, (lane, key, ms) in enumerate(walks):
            yield event("sync", t, keys={"b": key}, facts=PLAN | {"selected": None})
            for _ in range(3 * (i == 1)):
                yield event("begin", t, row=0, length=8, lane=lane, facts={"by": "asked"})
            if i == 2:
                yield "late", 300.0, t
                yield event("run", t - 0.2, 480.0, "x", thread="other", lane=None)      # told after the lateness it ran over
            yield event("begin", t, row=0, length=8, lane=lane)
            for r in range(8):
                yield event("run", t, ms, "b", r, key=key, demand="walk", asked="b", lane=lane)
                t += ms / 1000
                yield event("progress", t, row=r + 1, length=8, lane=lane, facts={})
            t += 3.0        # the loop says nothing from the third walk's lateness until the clip begins, longer than the shortest history: only ledger.SETTLES_BY settles those buckets
        yield event("begin", t, row=0, length=8, lane="clip")
        yield event("begin", t + 0.5, row=0, length=8, lane="window")       # the clip waits behind it from here
        for r in range(8):
            if r == 2:
                yield "still_out", {"w": ["b", t, 0.0, 0.0]}, t             # what a sampler found the thread in as the long row began
            for _ in range(int(STALLS) + 2 if r == 2 else 3):               # a row every three seconds, and one that takes longer than a lane may
                t += 1.0
                yield "late", 0.0, t
            yield event("progress", t, row=r + 1, length=8, lane="window", facts={})
        yield event("progress", t + 0.5, row=8, length=8, lane="clip", facts={})
        t += 1.0        # a row as long under a plan that runs c whole: no stall while c is out, nor between its end and the row's progress
        whole = {"kind": "series", "fed": True, "static": False, "served": False, "steps": False, "whole_by": None, "reads": {}}
        yield event("sync", t, keys={"b": "k3"}, facts=PLAN | {"selected": None, "nodes": {"c": whole}})
        yield event("begin", t, row=0, length=2, lane="window")
        yield event("progress", t, row=1, length=2, lane="window", facts={})
        yield "still_out", {"w": ["c", t, 0.0, 0.0]}, t
        for _ in range(int(STALLS) + 2):
            t += 1.0
            yield "late", 0.0, t
        yield event("run", t - STALLS - 2, (STALLS + 2) * 1000, "c", lane="window")
        yield event("run", t, 100.0, "b", 1, lane="window")
        yield "late", 0.0, t + 0.5
        yield event("progress", t + 0.6, row=2, length=2, lane="window", facts={})

    walks = [("window", "k", 1.0), ("window", "k", 4.0), ("clip", "k", 1.0), ("window", "k", 4.0), ("clip", "k", 4.0),
             ("clip", "k", 1.0), ("window", "k2", 4.0), ("clip", "k", 4.0), ("window", "k2", 1.0), ("window", "k", 4.0)]
    short = Log().back(0.25)
    ledgers = {(history, often): Ledger(walks=kept, history=history, watch=Log()) for history in (2400, short) for often in (True, False)}
    for ev in told(walks):
        for (_, often), led in ledgers.items():
            led.sample(*ev) if isinstance(ev, tuple) else led.event(ev)
            if often:
                led.view()
    for led in ledgers.values():
        led.end()
    (first, entries), *others = ((led.view().first, led.view().found.entries) for led in ledgers.values())
    assert all(e == entries for _, e in others) and first < others[-1][0]       # the shortest history had dropped its first buckets
    assert {k: (e.count, e.holds) for k, e in entries.items()} == {
        ("slower", "node", "b"): (4, True),     # both lanes' slow walks, and the clip's last still slow
        ("restarts", "lane", "window"): (1, False), ("late", "node", "x"): (1, False),
        ("stalls", "lane", "window"): (1, False)}   # the window's long row, and not the clip that waited behind every one
    assert entries["stalls", "lane", "window"].problem.nodes == ("b",)      # named by what its thread was sampled in


def test_a_bucket_under_a_span_still_out_is_not_judged():
    """A thread that says when it rests is under a span, for all the stream says, from its wake
    until it says otherwise: a lateness over that time is judged once the span is told, and then
    as a ledger read only at the end judges it."""
    def told():
        yield event("wake", 0.0)
        yield "late", 400.0, 1.0
        for i in range(1, 9):
            yield "late", 0.0, 1.0 + i / 4      # the GUI thread's loop turning on
        yield None
        yield event("run", 0.5, 2000.0, "x")    # two seconds on its own CPU, told as it ends
        yield "late", 0.0, 3.25

    often, once = Ledger(watch=Log()), Ledger(watch=Log())
    for item in told():
        if item is None:
            assert not often.view().found.entries and often.view().settled is None
            continue
        for led in (often, once):
            led.sample(*item) if isinstance(item, tuple) else led.event(item)
        often.view()
    assert list(often.view().found.entries) == [("late", "node", "x")] and once.view().found.entries == often.view().found.entries


def test_a_changed_param_between_two_walks_is_compared_with_nothing():
    slow = tool("slow", fn=lambda f, p: (time.sleep(p["k"] / 1000), f)[1])
    doc = D.from_tools([gray, slow])
    g = Graph(doc, Dec(), {**TOOLS, "slow": slow})
    led = Ledger()
    g.on_event = led.event
    g.sync()
    walk(g, range(8))
    doc.node("slow").params["k"] = 20
    g.sync()
    walk(g, range(8))
    first, second = led.view().walks
    assert second.nodes["slow"].runs[("run", "walk", "slow")].ms > 3 * first.nodes["slow"].runs[("run", "walk", "slow")].ms
    assert not seen(led.view())
    second.keys = first.keys
    assert list(seen(View(0.25, 0, [], [first, second]))) == [("slower", "slow")]


def test_the_cold_projection_sums_what_the_plan_reaches_by_the_walk_each_node_last_ran_in():
    def node(*reads, **flags):
        return {"kind": "frame", "fed": True, "static": False, "served": False, "steps": False, "whole_by": None,
                "reads": dict(enumerate(reads))} | flags

    def under(served=False, **walk):
        nodes = {"a": node(), "b": node(*() if served else "a", served=served), "c": node("b", "s"), "s": node(static=True)}
        w = rec(**walk)
        w.plan = PLAN | {"nodes": nodes, "walk": "c"}
        return w

    def ran(ms, more=()):
        return Node(runs=runs({("run", "walk", "c"): [8, ms, 0]} | dict(more)), ran=8)
    first = under(t0=0.0, keys={"a": "ka", "b": "kb", "c": "kc"}, a=ran(8.0, {("seek", "walk", "c"): [1, 6.0, 0]}), b=ran(16.0),
                  c=ran(8.0, {("fold", "fold", "c"): [8, 4.0, 0]}))
    first.unprobed = 4.0
    p = cold(View(0.25, 0, [], [first]))
    assert {n: (c.ms_row, c.walk, c.stale) for n, c in p.nodes.items()} == {
        "a": (1.0, ("window", 0.0), False), "b": (2.0, ("window", 0.0), False), "c": (1.0, ("window", 0.0), False), "s": (0.0, None, False)}
    assert (p.unprobed, p.ms_row(), p.missing) == (0.5, 4.5, ())                 # the seek and the fold are no row's
    second = under(t0=1.0, keys={"a": "ka", "b": "kb2", "c": "kc2"}, a=Node(runs=runs({("cache", "walk", "c"): [8, 2.0, 0]}), held=8),
                   b=Node(runs=runs({("run", "walk", "c"): [4, 12.0, 0], ("fold", "fold", "b"): [8, 1.0, 0]}), ran=8),
                   c=ran(8.0))     # a row a cache held is no walk the node ran in, and a row only b's fold ran on is none b ran on
    p = cold(View(0.25, 0, [], [first, second]))
    assert {n: (c.ms_row, c.walk, c.stale) for n, c in p.nodes.items() if c.walk} == {
        "a": (1.0, ("window", 0.0), False), "b": (3.0, ("window", 1.0), False), "c": (1.0, ("window", 1.0), False)}
    served = under(served=True, t0=2.0, keys={"a": "ka", "b": "kb3", "c": "kc3"})
    served.done = 0
    p = cold(View(0.25, 0, [], [first, second, served]))
    assert reach(served.plan) == {"b", "c", "s"} and "a" not in p.nodes         # nothing behind the served node
    assert {n: (c.walk, c.stale) for n, c in p.nodes.items() if c.walk} == {"b": (("window", 1.0), True), "c": (("window", 1.0), True)}


@pytest.mark.simulation
@pytest.mark.parametrize("name", list(SIMULATIONS))
def test_a_simulation_surfaces_its_class_alone(name, tmp_path):
    seen = run(name, tmp_path)
    assert {e.problem.kind for e in seen.log.ordered()} == {SIMULATIONS[name][1]}, [e.problem.line for e in seen.log.ordered()]
    subjects = {e.problem.subject for e in seen.log.ordered()}
    want = {"unread": {"work"}, "memo": {"memo"}, "cache": {"video"}, "reader": {"cut"}, "grows": {"pile"},
            "seeks": {"video"}, "slower": {"work"}, "held": {"unprobed"}, "slot": {"slot walked"}, "signals": {"slot walked"},
            "frozen": {"slot walked"}, "holds": {"work"}, "unspanned": {"nothing recorded"}, "again": {"window"}, "stuck": {"window"},
            "unreturned": {"work"}}[name]
    assert want == subjects


@pytest.mark.simulation
@pytest.mark.parametrize("name", list(HEALTHY))
def test_a_healthy_walk_surfaces_nothing(name, tmp_path):
    seen = run(name, tmp_path)
    assert not seen.log.entries and seen.view.walks[-1].done == seen.view.walks[-1].length
    assert {"late", "restarts", "stalls"} <= seen.log.checked


@pytest.mark.simulation
def test_an_entrys_text_is_enough_to_begin_on_the_fault(tmp_path):
    seen = run("unread", tmp_path)
    entry = seen.log.entries[("unread", "node", "work")]
    t = text(entry, seen.view, seen.context)
    labels = [ln.split()[0] for ln in t.splitlines() if ln and not ln.startswith((" ", "{", "}"))]
    assert labels == ["class", "subject", "line", "cost", "evidence", "walk", "plan", "stores", "video", "decoder", "commit",
                      "dump", "simulation", "source", "document"]
    assert "window, rows 0..63, 64 of 64" in t and "work: frame, fed; reads gray; read by nothing" in t
    assert "gray: frame, fed; reads video; read by work, edge" in t and "clip.avi" in t
    assert "sieve_player.dev.simulations unread" in t and entry.problem.source in t and seen.context["commit"] in t
    doc = D.Document.from_dict(json.loads(t.split("\ndocument\n", 1)[1]))
    assert doc.source("edge").src == "gray" and [n.id for n in doc.nodes] == ["video", "gray", "work", "edge", "mean", "pile"]
