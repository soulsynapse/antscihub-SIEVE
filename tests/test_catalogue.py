"""The catalogue: each class read off a view, each simulation surfacing its class alone, the log and an entry's text."""
import json
import shutil
import time
from dataclasses import replace

import pytest

from sieve_player import document as D
from sieve_player.catalogue import (CLASSES, SOURCES, SPANS, Entry, Log, cold, reach, seeks, signals, slower, stores_at, thrash,
                                    unread, waits)
from sieve_player.dev.simulations import HEALTHY, SERVED, SIMULATIONS, run
from sieve_player.graph import Graph
from sieve_player.ledger import Bucket, Ledger, Node, Total, Under, View, Walk
from sieve_player.report import report, text
from tests.test_graph import TOOLS, Dec, gray, tool
from tests.test_ledger import event, walk

PLAN = {"nodes": {}, "chain": [], "walk": "b", "shown": "b", "over": None, "pinned": []}
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="a bake's clip writer runs ffmpeg from PATH")


def runs(by):
    return {Under(*u): Total(*r) for u, r in by.items()}


def rec(t0=0.0, keys=None, **nodes):
    """A finished window walk of eight rows whose nodes are `nodes`, each a Node or its runs."""
    nodes = {n: v if isinstance(v, Node) else Node(runs=runs(v)) for n, v in nodes.items()}
    return Walk("window", 0, 8, PLAN, keys, t0, t0 + 0.5, done=8, nodes=nodes)


def found(*walks, pinned=()):
    for w in walks:
        w.plan = PLAN | {"pinned": list(pinned)}
    log = Log()
    log.read(View(0.25, 0, [], list(walks)))
    return {(e.problem.kind, e.problem.subject): e for e in log.ordered()}


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
    a, t = unread(View(0.25, 0, [], [both]))
    assert [" t " in x for x in a.evidence] == [True, True, False]                             # the run and the decode t's fold would open, not a's own fold
    assert "no plane" in t.line and "no plane" in t.target and "no plane" not in a.line        # t ran under its fold and folded nothing
    thrashed = rec(keys={"video": "kv"}, b={("run", "walk", "b"): [8, 8.0, 0]})
    thrashed.recomputed, thrashed.recomputed_ms = {"memo": 8, "kv": 4, "other": 1}, {"memo": 4.0, "kv": 2.0, "other": 1.0}
    assert {k: e.problem.ms_row for k, e in found(thrashed).items()} == {("thrash", "memo"): 0.5, ("thrash", "video"): 0.25}
    (key, e), = found(rec(**GROWN)).items()
    assert key == ("grows", "c") and e.problem.ms_row == 12 / 8 and e.problem.share == 12 / 20
    assert not found(rec(c=Node(runs=GROWN["c"].runs, parts=[0.0] * 4 + [5.0] * 4, counts=[0] * 4 + [1] * 4)))     # held, then run: flat
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
    assert {kind for _, kind in SIMULATIONS.values()} == {*CLASSES, *SPANS} == set(SOURCES)
    quiet = [Bucket(), Bucket()]
    felt = View(0.25, 0, [Bucket(), Bucket(late=300.0, turns={"slot walked": 200.0}, rows={"window": 4}), *quiet,
                          Bucket(late=300.0, longest={"b": [250.0, 240.0]}), *quiet, Bucket(late=300.0, longest={"b": [250.0, 10.0]}),
                          Bucket(late=99.0), Bucket(late=500.0), Bucket()], [])     # under a turn, under one call on its own CPU, under one that waited; unfelt; the bucket after it unsettled
    assert [(p.key, p.ms_row, p.t) for p in SPANS["late"](felt)] == [(("late", "turn", "slot walked"), 75.0, 0.25), (("late", "node", "b"), None, 1.0),
                                                            (("late", "unrecorded", "nothing recorded"), None, 1.75)]
    begun = [Bucket(begins={"window": {"asked": 2, "hand": 9}}, rows={"window": 8}), Bucket(begins={"window": {"given": 1}}, rows={"window": 4}),
             Bucket(begins={"window": {"hand": 5, "edit": 5}}), Bucket(), Bucket()]
    (p,) = SPANS["restarts"](View(0.25, 0, begun, []))       # two by no hand are under it, the third is it, and a hand's and an edit's are none however many
    assert (p.key, p.t, p.walk) == (("restarts", "lane", "window"), 0.25, None) and "3 times in 0.50 s and finished" in p.line and "went stale" in p.target
    assert all(q.says and q.target for q in (p, *SPANS["late"](felt)))
    assert not SPANS["restarts"](View(0.25, 0, [begun[0], replace(begun[1], rows={"window": 24}), *begun[2:]], []))      # rows enough finished a beginning
    turned = rec(b={("run", "walk", "b"): [8, 100.0, 0]})
    turned.wait = 80.0
    waited = View(0.25, 0, [Bucket(wait=40.0, turns={"slot walked": 60.0, "paint plot": 5.0})] * 2, [turned])
    told = rec(b=Node(runs=runs(run_b(8.0)), ran=8))
    signalled = View(0.25, 0, [Bucket(turns={"slot clipWalked": 0.5, "slot seriesReady": 9.0}, calls={"slot clipWalked": 4, "slot seriesReady": 1})] * 2, [told])
    assert not signals(View(0.25, 0, signalled.buckets, [rec(b=Node(runs=runs(run_b(8.0)), held=8))]))     # a walk the stores held
    assert [p.share for p in signals(signalled)] == [None]                                                 # the GUI thread's ms, none of the walk's nodes'
    said = {k: (e.problem.says, e.problem.target, e.problem.nodes) for views in (
        [rec(**FOLDED)], [thrashed], [rec(**GROWN)], [rec(**SOUGHT)], [rec(keys={"b": "k"}, b=run_b(8.0)), late], waited, signalled)
        for k, e in (found(*views) if isinstance(views, list) else
                     {(p.kind, p.subject): Entry(p, p.t) for p in (*waits(views), *signals(views))}).items()}
    assert {k[0] for k in said} == set(CLASSES) and all(says and target for says, target, _ in said.values())
    assert said[("unread", "a")] == ("Computed on every row and read by nothing", "the fold of a", ("a",))
    assert said[("thrash", "video")][1:] == ("the video cache's limit", ("video",)) and said[("thrash", "memo")][2] == ()
    assert said[("waits", "slot walked")][1:] == ("the walked slot", ()) and waits(waited)[0].turns == ("slot walked",)
    assert said[("signals", "slot clipWalked")][1:] == ("how often clipWalked is signalled", ()) and signals(signalled)[0].turns == ("slot clipWalked",)
    named = rec(keys={"memo": "km"}, b={("run", "walk", "b"): [8, 8.0, 0]})     # a node whose id is a reader's own name is still a node
    named.recomputed, named.recomputed_ms = {"memo": 8, "km": 8}, {"memo": 4.0, "km": 4.0}
    assert {p.key for p in thrash(View(0.25, 0, [], [named]))} == {("thrash", "store", "memo"), ("thrash", "node", "memo")}
    (p,) = slower(View(0.25, 0, [], [rec(keys={"b": "k"}, unprobed=run_b(8.0)), rec(1.0, {"b": "k"}, unprobed=run_b(16.0))]))
    assert (p.key, p.target, p.nodes) == (("slower", "node", "unprobed"), "unprobed", ("unprobed",))
    assert said[("slower", "unprobed")][1:] == ("the time between rows, in no node", ())


def test_the_log_holds_one_entry_a_class_and_subject_counted_cleared_and_ordered():
    walks, judged = [rec(float(i), **SOUGHT) for i in range(10)], []
    log = Log({"seeks": lambda view, walks, baselines: (judged.append(len(walks)), seeks(view, walks))[1]})
    for _ in range(2):      # a view read again counts no walk twice
        made = log.read(View(0.25, 0, [], walks))
    (e,) = log.ordered()
    assert (e.count, e.holds, e.first, made) == (10, True, 0.5, [])
    log.read(View(0.25, 0, [], walks + [rec(10.0, video={("decode", "walk", "b"): [8, 8.0, 0]})]))
    assert log.ordered() == [e] and (e.count, e.holds, e.problem.walk) == (10, False, ("window", 9.0))
    assert judged == [10, 1, 2]     # a walk its lane has begun another after is judged once more and then kept
    again, clip, quiet = rec(11.0, **SOUGHT), rec(12.0, **SOUGHT), rec(13.0, video={("decode", "walk", "b"): [8, 8.0, 0]})
    clip.lane = quiet.lane = "clip"
    log.read(View(0.25, 0, [], walks + [again, clip, quiet]))
    assert (e.count, e.holds, e.problem.walk) == (12, True, ("window", 11.0))     # cleared in one lane, it holds by another's last walk
    short = rec(14.0, **SOUGHT)
    short.done = 2
    log.read(View(0.25, 0, [], walks + [again, clip, quiet, short, rec(15.0, video={("decode", "walk", "b"): [8, 8.0, 0]})]))
    assert (e.count, e.holds) == (12, False)     # a walk of two rows is not judged
    log.read(View(0.25, 0, [], walks + [again, clip, quiet, short, rec(16.0, **SOUGHT)]))
    log.read(View(0.25, 0, [], [clip, quiet]))
    assert (e.count, e.holds) == (13, True)      # its walk gone from the history, no walk has shown it gone
    assert "WALK     no longer in the history" in report([e], View(0.25, 0, [], [clip, quiet]))      # and no other walk is shown as its
    turned = rec(20.0, b={("run", "walk", "b"): [8, 100.0, 0]})
    turned.wait, turned.replanned = 80.0, True
    log = Log()
    log.read(View(0.25, 80, [Bucket(wait=40.0, turns={"slot walked": 60.0})] * 2, [rec(19.0, **FOLDED), turned]))
    log.read(View(0.25, 90, [], [turned]))      # its buckets gone from the history, and replanned
    assert all(e.holds for e in log.ordered()) and set(log.entries) == {("waits", "turn", "slot walked"), ("unread", "node", "a")}     # a walk a class cannot judge shows nothing gone
    assert "waits" in log.checked and "slower" not in log.checked
    fast, *slow = (rec(30.0 + i, {"b": "k"}, b={("run", "walk", "b"): [8, ms, 0]}) for i, ms in enumerate((8.0, 16.0, 16.0, 16.0)))
    log = Log()
    log.read(View(0.25, 0, [], [fast, *slow[:2]]))
    log.read(View(0.25, 0, [], slow))
    e = log.entries[("slower", "node", "b")]
    assert (e.count, e.holds, e.problem.walk) == (3, True, ("window", 33.0))     # the walk it is slower than gone from the history, it is slower still
    five = rec(keys={"video": "kv"}, a={("run", "fold", "a"): [8, 20.0, 0]}, **SOUGHT, **GROWN)
    five.recomputed, five.recomputed_ms = {"memo": 8, "kv": 4}, {"memo": 4.0, "kv": 2.0}
    assert list(found(five)) == [("unread", "a"), ("grows", "c"), ("seeks", "video"), ("thrash", "memo"), ("thrash", "video")]     # by cost


@pytest.mark.parametrize("kept", [2, 3])
def test_the_log_reads_the_same_however_few_walks_the_ledger_keeps(kept):
    """One stream into a ledger that keeps every walk and one that keeps `kept`, each read by its
    own Log after every event: the entries are equal throughout, those of the classes that judge
    no walk among them, and equal at the end to those of a Log that reads the whole once."""
    def told(walks):
        t = 0.0
        for i, (lane, key, ms) in enumerate(walks):
            yield event("sync", t, keys={"b": key}, facts=PLAN | {"selected": None})
            for _ in range(3 * (i == 1)):
                yield event("begin", t, row=0, length=8, lane=lane, facts={"by": "asked"})
            if i == 2:
                yield "late", 300.0, t
                yield "late", 0.0, t + 0.26
                yield event("run", t - 0.2, 480.0, "x", thread="other", lane=None)      # told a bucket after the lateness it ran over
            yield event("begin", t, row=0, length=8, lane=lane)
            for r in range(8):
                yield event("run", t, ms, "b", r, key=key, demand="walk", asked="b", lane=lane)
                t += ms / 1000
                yield event("progress", t, row=r + 1, length=8, lane=lane, facts={})
            t += 1.0

    walks = [("window", "k", 1.0), ("window", "k", 4.0), ("clip", "k", 1.0), ("window", "k", 4.0), ("clip", "k", 4.0),
             ("clip", "k", 1.0), ("window", "k2", 4.0), ("clip", "k", 4.0), ("window", "k2", 1.0), ("window", "k", 4.0)]
    (all_, some), (whole, short) = (Ledger(), Ledger(walks=kept)), (Log(), Log())
    for i, ev in enumerate(told(walks)):
        for led, log in ((all_, whole), (some, short)):
            led.sample(*ev) if isinstance(ev, tuple) else led.event(ev)
            log.read(led.view())
        assert whole.entries == short.entries, (i, ev)
    once = Log()
    once.read(all_.view())
    assert once.entries == whole.entries
    assert {k: (e.count, e.holds) for k, e in whole.entries.items()} == {
        ("slower", "node", "b"): (4, True),     # both lanes' slow walks, and the clip's last still slow
        ("restarts", "lane", "window"): (1, False), ("late", "node", "x"): (1, False)}


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
    assert not slower(led.view())
    second.keys = first.keys
    assert [p.subject for p in slower(View(0.25, 0, [], [first, second]))] == ["slow"]


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
@pytest.mark.parametrize("name", [pytest.param(n, marks=needs_ffmpeg) if n in SERVED else n for n in SIMULATIONS])
def test_a_simulation_surfaces_its_class_alone(name, tmp_path):
    seen = run(name, tmp_path)
    assert {e.problem.kind for e in seen.log.ordered()} == {SIMULATIONS[name][1]}, [e.problem.line for e in seen.log.ordered()]
    subjects = {e.problem.subject for e in seen.log.ordered()}
    want = {"unread": {"gray", "work"}, "memo": {"memo"}, "cache": {"video"}, "reader": {"bake"}, "grows": {"pile"},
            "seeks": {"video"}, "slower": {"work"}, "held": {"unprobed"}, "slot": {"slot walked"}, "signals": {"slot walked"},
            "frozen": {"slot walked"}, "holds": {"work"}, "unspanned": {"nothing recorded"}, "again": {"window"}}[name]
    assert want <= subjects and (name == "unread" or want == subjects)


@pytest.mark.simulation
@pytest.mark.parametrize("name", [pytest.param(n, marks=needs_ffmpeg) if n in SERVED else n for n in HEALTHY])
def test_a_healthy_walk_surfaces_nothing(name, tmp_path):
    seen = run(name, tmp_path)
    assert not seen.log.entries and seen.view.walks[-1].done == seen.view.walks[-1].length
    assert {"late", "restarts"} <= seen.log.checked


@pytest.mark.simulation
@needs_ffmpeg
def test_an_entrys_text_is_enough_to_begin_on_the_fault(tmp_path):
    seen = run("unread", tmp_path)
    entry = seen.log.entries[("unread", "node", "work")]
    t = text(entry, seen.view, seen.context)
    labels = [ln.split()[0] for ln in t.splitlines() if ln and not ln.startswith((" ", "{", "}"))]
    assert labels == ["class", "subject", "line", "cost", "evidence", "walk", "plan", "stores", "video", "decoder", "commit",
                      "dump", "simulation", "source", "document"]
    assert "window, rows 0..63, 64 of 64" in t and "work: frame, fed; reads gray; read by nothing" in t      # the served bake cut its wire
    assert "gray: frame, fed; reads video; read by work" in t and "bake cache" in t and "clip.avi" in t
    assert "sieve_player.dev.simulations unread" in t and entry.problem.source in t and seen.context["commit"] in t
    doc = D.Document.from_dict(json.loads(t.split("\ndocument\n", 1)[1]))
    assert doc.node("bake").mode == D.BAKED and [n.id for n in doc.nodes] == ["video", "gray", "work", "bake", "edge", "mean", "pile"]
