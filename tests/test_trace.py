"""The dump: what a recorder derives, derived from the file and not from memory."""
import json
from collections import Counter

from sieve_player import document as D
from sieve_player.graph import Graph, Stats
from sieve_player.trace import Dump, read_dump, to_trace, totals
from tests.test_graph import TOOLS, Dec, add, gray


def walk(g, rows):
    for r in rows:
        g.compute("add", r)
        g.progress(r + 1, len(rows))


def dump_of(tmp_path):
    """Two walks of six rows with a param change between them, over a memo too small to hold one
    walk, so the second recomputes and redecodes; one more read of row 0 at the end."""
    doc = D.from_tools([gray, add])
    g = Graph(doc, Dec(), TOOLS, memo_bytes=200)
    Stats(g)
    dump = Dump(g, tmp_path / "d.jsonl")
    g.sync()
    walk(g, range(6))
    doc.node("add").params["k"] = 2
    g.sync()
    walk(g, range(6))
    g.compute("video", 0)
    dump.close()
    assert g.on_event is not None and g.on_event.__self__.__class__ is Stats     # the chain restored
    return g, dump.path


def test_a_recorder_derives_from_the_file(tmp_path):
    g, path = dump_of(tmp_path)
    header, events = read_dump(path)
    assert header["path"] == "fake.mp4" and header["count"] == 10 and header["memo_bytes"] == 200 and "keys" in header["fields"]
    reads = Counter(ev.row for ev in events if ev.node == "video" and ev.kind != "cache")
    assert reads[0] >= 2 and all(n >= 1 for n in reads.values())                       # redecodes: one row read uncached twice
    runs = Counter((ev.key, ev.row) for ev in events if ev.kind == "run")
    assert any(n == 2 and k == g.key("gray") for (k, _), n in runs.items())           # recomputes: one key and row run twice
    b0, b1 = (i for i, ev in enumerate(events) if ev.kind == "sync")
    assert [n for n in events[b1].keys if events[b1].keys[n] != events[b0].keys[n]] == ["add"]

    def means(evs):
        by = {}
        for ev in evs:
            if ev.kind == "run":
                by.setdefault(ev.node, []).append(ev.ms)
        return {n: sum(v) / len(v) for n, v in by.items()}
    before, after = means(events[b0:b1]), means(events[b1:])
    assert set(before) == set(after) == {"gray", "add"} and all(v >= 0 for v in after.values())   # what the change cost, per node
    progress = [ev for ev in events if ev.kind == "progress"]
    assert [ev.row for ev in progress] == list(range(1, 7)) * 2 and {ev.length for ev in progress} == {6}
    (t0, r0), (t1, r1) = (progress[0].t, progress[0].row), (progress[5].t, progress[5].row)
    assert (r1 - r0) / (t1 - t0) > 0                                                   # the walk's rate
    assert all(ev.thread == "MainThread" and ev.serves is None for ev in events)


def test_the_trace_has_a_timestamp_duration_and_thread_on_every_event(tmp_path):
    g, path = dump_of(tmp_path)
    doc = json.loads(json.dumps(to_trace(path, tmp_path / "t.json")))
    spans = [e for e in doc["traceEvents"] if e["ph"] == "X"]
    assert spans and all({"ts", "dur", "tid"} <= set(e) for e in spans)
    assert {e["name"] for e in doc["traceEvents"] if e["ph"] == "M"} == {"thread_name"}
    _, events = read_dump(path)
    total = totals(events)
    first = {ev.node: ev for ev in events if ev.row == 0 and ev.kind in ("run", "step")}
    assert total[id(first["add"])] >= first["add"].ms + total[id(first["gray"])]           # a run's total holds its reads
    assert total[id(first["video"])] == first["video"].ms                                 # a read opens nothing


def test_a_dump_cut_mid_line_reads_to_the_line_before(tmp_path):
    _, path = dump_of(tmp_path)
    _, whole = read_dump(path)
    data = path.read_bytes()
    path.write_bytes(data[: data.rfind(b"\n", 0, -1) + 8])     # a crash: the last line half written
    _, cut = read_dump(path)
    assert len(cut) == len(whole) - 1 and cut == whole[:-1]
