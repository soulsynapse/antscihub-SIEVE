"""The ledger: buckets and walks off the stream alone, the same from a dump as live."""
import copy
import threading

import pytest

from sieve_player import document as D
from sieve_player.graph import Event, Graph
from sieve_player.ledger import PARTS, Ledger, replay, save, saved
from sieve_player.trace import FIELDS, Dump
from tests.test_graph import TOOLS, Dec, add, gray


def walk(g, rows):
    g.serving("walk", "window")
    g.began(rows[0], len(rows))
    for i, r in enumerate(rows):
        g.walk_row(r)
        g.progress(i + 1, len(rows))


def event(kind, t, ms=0.0, node=None, row=None, **more):
    return Event(**{f: None for f in FIELDS} | {"kind": kind, "t": t, "ms": ms, "node": node, "row": row, "bytes": 0,
                                                "thread": "w", "lane": "window"} | more)


def runs(node, kind="run"):
    return sum(r[0] for (k, _, _), r in node.runs.items() if k == kind)


def test_a_dump_replays_into_the_ledger_the_live_one_was(tmp_path):
    doc = D.from_tools([gray, add])
    g = Graph(doc, Dec(), TOOLS)
    live = Ledger()
    g.on_event = live.event
    dump = Dump(g, tmp_path / "d.jsonl")
    g.sync()
    walk(g, range(6))
    doc.node("add").params["k"] = 2
    g.sync()
    walk(g, range(6))
    t = live.view().walks[-1].t1
    for led in (live, dump):
        led.sample("late", 40.0, t)
    dump.close()
    seen = live.view()
    assert replay(dump.path).view() == seen and max(b.late for b in seen.buckets) == 40.0
    first, second = seen.walks
    assert (first.lane, first.start, first.length, first.done) == ("window", 0, 6, 6) and first.t0 < first.t1 <= second.t0
    assert first.plan["walk"] == "add" and first.keys["gray"] == second.keys["gray"] and first.keys["add"] != second.keys["add"]
    assert {n: runs(v) for n, v in first.nodes.items()} == {"add": 6, "gray": 6, "video": 0} and runs(first.nodes["video"], "decode") == 6
    assert {n: runs(v) for n, v in second.nodes.items() if v.runs} == {"add": 6}       # gray was held: only what changed ran, and all of it
    assert set(first.nodes["gray"].runs) == {("run", "walk", "add")} and not (first.replanned or second.replanned)
    assert sum(b.rows.get("window", 0) for b in seen.buckets) == 12 and seen.buckets[-1].stores["memo"] == (g.memo.bytes, g.memo.limit)
    save(seen, tmp_path / "history.json", document=doc.to_dict())      # the hand-over for a slowdown of no class: history, plans, document
    back, more = saved(tmp_path / "history.json")
    assert back.view() == seen and D.Document.from_dict(more["document"]).node("add").params["k"] == 2


def test_a_walk_says_how_cold_it_was_and_what_a_store_made_it_compute_again():
    g = Graph(D.from_tools([gray, add]), Dec(), TOOLS)
    led = Ledger()
    g.on_event = led.event
    g.sync()
    walk(g, range(6))
    walk(g, range(6))
    walk(g, range(3, 9))
    cold, held, half = ({n: (v.ran, v.held, v.served) for n, v in w.nodes.items()} for w in led.view().walks)
    assert cold == {"add": (6, 0, 0), "gray": (6, 0, 0), "video": (6, 0, 0)}
    assert held == {"add": (0, 6, 0)} and half == {"add": (3, 3, 0), "gray": (3, 0, 0), "video": (3, 0, 0)}
    assert not any(w.recomputed for w in led.view().walks)

    g = Graph(D.from_tools([gray, add]), Dec(), TOOLS, memo_bytes=3 * 48)      # a row is gray's plane and add's, 24 bytes each
    led = Ledger()
    g.on_event = led.event
    walk(g, range(6))
    discarded = 12 - len(g.memo._big)
    walk(g, range(6))
    first, second = led.view().walks
    # Under an LRU the second walk discards, before it reaches them, the rows the first left held: every row is computed again.
    assert not first.recomputed and discarded == 6 and second.recomputed == {"memo": 12} and second.recomputed_ms["memo"] > 0
    assert sum(b.recomputed.get("memo", 0) for b in led.view().buckets) == 12


def test_a_span_is_spread_over_its_buckets_and_a_cost_keeps_its_place_along_the_range():
    led = Ledger(width=0.25, history=8)
    led.event(event("run", 1.0, 750.0, "slow"))
    led.event(event("decode", 2.05, 20.0, "video", reader="outer"))
    led.event(event("run", 2.0, 80.0, "outer"))                # 100 ms in all, the decode inside it from 50 to 70
    v = led.view()
    assert [b.ms.get("w", {}).get("slow") for b in v.buckets[:4]] == [pytest.approx(250.0)] * 3 + [None] and v.first == 4
    assert v.buckets[4].ms["w"] == {"outer": pytest.approx(80.0), "video": pytest.approx(20.0)}
    led.event(event("run", 100.0, 3100.0, "long"))             # thirteen buckets touched
    assert len(led.view().buckets) == 8 and led.view().first == 405 and len(v.buckets) == 5     # the bound; the view held is as it was

    led = Ledger()
    led.event(event("begin", -2.0, row=5, length=9))            # a drag: begun and begun again with no row between
    led.event(event("run", -1.5, 1.0, "dropped", row=5))
    led.event(event("begin", 0.0, row=0, length=64))
    for r in range(64):
        led.event(event("step", r, 2.0 ** (r // 8), "grows", row=r))
        led.event(event("step", r + 0.5, 3.0, "flat", row=r))
        led.event(event("progress", r + 0.9, row=r + 1, length=64))
    assert [w.start for w in led.view().walks] == [0]
    nodes = led.view().walks[0].nodes
    assert len(nodes["grows"].parts) == PARTS and nodes["grows"].parts[-1] == 128 * nodes["grows"].parts[0]
    assert set(nodes["flat"].parts) == {24.0} and nodes["flat"].counts == [8] * PARTS and nodes["flat"].ran == 64
    unprobed = 63900.0 - sum(2.0 ** (r // 8) + 3.0 for r in range(64))      # from the begin to the last progress
    assert sum(b.unprobed for b in led.view().buckets) == pytest.approx(unprobed) == led.view().walks[0].unprobed


def test_a_view_is_the_readers_to_hold_while_another_thread_feeds():
    events = [event("begin", 0.0, row=0, length=4000)]
    for r in range(4000):
        events += [event("run", r * 0.01, 5.0, "node", row=r), event("progress", r * 0.01 + 0.009, row=r + 1, length=4000)]
    led, alone = Ledger(), Ledger()
    feeder = threading.Thread(target=lambda: [led.event(ev) for ev in events])
    feeder.start()
    early = led.view()
    kept = copy.deepcopy(early)
    while feeder.is_alive():
        led.view()
    feeder.join()
    for ev in events:
        alone.event(ev)
    assert led.view() == alone.view() and early == kept and led.view().walks[0].done == 4000
