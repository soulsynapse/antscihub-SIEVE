"""The catalogue: each class read off a view, each simulation surfacing its class alone, the log and an entry's text."""
import json
import shutil
import time

import pytest

from sieve_player import document as D
from sieve_player.catalogue import CLASSES, SOURCES, Entry, Log, cold, reach, seeks, signals, slower, waits
from sieve_player.dev.simulations import HEALTHY, SERVED, SIMULATIONS, run
from sieve_player.graph import Graph
from sieve_player.ledger import Bucket, Ledger, Node, Total, Under, View, Walk
from sieve_player.report import text
from tests.test_graph import TOOLS, Dec, gray, tool
from tests.test_ledger import walk

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
    thrashed = rec(keys={"video": "kv"}, b={("run", "walk", "b"): [8, 8.0, 0]})
    thrashed.recomputed, thrashed.recomputed_ms = {"memo": 8, "kv": 4, "other": 1}, {"memo": 4.0, "kv": 2.0, "other": 1.0}
    assert {k: e.problem.ms_row for k, e in found(thrashed).items()} == {("thrash", "memo"): 0.5, ("thrash", "video"): 0.25}
    (key, e), = found(rec(**GROWN)).items()
    assert key == ("grows", "c") and e.problem.ms_row == 12 / 8 and e.problem.share == 12 / 20
    assert not found(rec(c=Node(runs=GROWN["c"].runs, parts=[0.0] * 4 + [5.0] * 4, counts=[0] * 4 + [1] * 4)))     # held, then run: flat
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
    assert {kind for _, kind in SIMULATIONS.values()} == set(CLASSES) == set(SOURCES)
    turned = rec(b={("run", "walk", "b"): [8, 100.0, 0]})
    turned.wait = 80.0
    waited = View(0.25, 0, [Bucket(wait=40.0, turns={"slot walked": 60.0, "paint plot": 5.0})] * 2, [turned])
    told = rec(b=Node(runs=runs(run_b(8.0)), ran=8))
    signalled = View(0.25, 0, [Bucket(turns={"slot clipWalked": 0.5, "slot seriesReady": 9.0}, calls={"slot clipWalked": 4, "slot seriesReady": 1})] * 2, [told])
    assert not signals(View(0.25, 0, signalled.buckets, [rec(b=Node(runs=runs(run_b(8.0)), held=8))]))     # a walk the stores held
    said = {k: (e.problem.says, e.problem.target, e.problem.nodes) for views in (
        [rec(**FOLDED)], [thrashed], [rec(**GROWN)], [rec(**SOUGHT)], [rec(keys={"b": "k"}, b=run_b(8.0)), late], waited, signalled)
        for k, e in (found(*views) if isinstance(views, list) else
                     {(p.kind, p.subject): Entry(p, p.t) for p in (*waits(views), *signals(views))}).items()}
    assert {k[0] for k in said} == set(CLASSES) and all(says and target for says, target, _ in said.values())
    assert said[("unread", "a")] == ("Computed on every row and read by nothing", "the fold of a", ("a",))
    assert said[("thrash", "video")][1:] == ("the video cache's limit", ("video",)) and said[("thrash", "memo")][2] == ()
    assert said[("waits", "slot walked")][1:] == ("the walked slot", ("slot walked",))
    assert said[("signals", "slot clipWalked")][1:] == ("how often clipWalked is signalled", ("slot clipWalked",))
    assert said[("slower", "unprobed")][1:] == ("the time between rows, in no node", ())


def test_the_log_holds_one_entry_a_class_and_subject_counted_cleared_and_ordered():
    walks, judged = [rec(float(i), **SOUGHT) for i in range(10)], []
    log = Log({"seeks": lambda view, walks: (judged.append(len(walks)), seeks(view, walks))[1]})
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
    five = rec(keys={"video": "kv"}, a={("run", "fold", "a"): [8, 20.0, 0]}, **SOUGHT, **GROWN)
    five.recomputed, five.recomputed_ms = {"memo": 8, "kv": 4}, {"memo": 4.0, "kv": 2.0}
    assert list(found(five)) == [("unread", "a"), ("grows", "c"), ("seeks", "video"), ("thrash", "memo"), ("thrash", "video")]     # by cost


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
    second = under(t0=1.0, keys={"a": "ka", "b": "kb2", "c": "kc2"}, a=Node(held=8), b=ran(24.0), c=ran(8.0))
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
            "seeks": {"video"}, "slower": {"work"}, "held": {"unprobed"}, "slot": {"slot walked"}, "signals": {"slot walked"}}[name]
    assert want <= subjects and (name == "unread" or want == subjects)


@pytest.mark.simulation
@pytest.mark.parametrize("name", [pytest.param(n, marks=needs_ffmpeg) if n in SERVED else n for n in HEALTHY])
def test_a_healthy_walk_surfaces_nothing(name, tmp_path):
    seen = run(name, tmp_path)
    assert not seen.log.entries and seen.view.walks[-1].done == seen.view.walks[-1].length


@pytest.mark.simulation
@needs_ffmpeg
def test_an_entrys_text_is_enough_to_begin_on_the_fault(tmp_path):
    seen = run("unread", tmp_path)
    entry = seen.log.entries[("unread", "work")]
    t = text(entry, seen.view, seen.context)
    labels = [ln.split()[0] for ln in t.splitlines() if ln and not ln.startswith((" ", "{", "}"))]
    assert labels == ["class", "subject", "line", "cost", "evidence", "walk", "plan", "stores", "video", "decoder", "commit",
                      "dump", "simulation", "source", "document"]
    assert "window, rows 0..63, 64 of 64" in t and "work: frame, fed; reads gray; read by nothing" in t      # the served bake cut its wire
    assert "gray: frame, fed; reads video; read by work" in t and "bake cache" in t and "clip.avi" in t
    assert "sieve_player.dev.simulations unread" in t and entry.problem.source in t and seen.context["commit"] in t
    doc = D.Document.from_dict(json.loads(t.split("\ndocument\n", 1)[1]))
    assert doc.node("bake").mode == D.BAKED and [n.id for n in doc.nodes] == ["video", "gray", "work", "bake", "edge", "mean", "pile"]
