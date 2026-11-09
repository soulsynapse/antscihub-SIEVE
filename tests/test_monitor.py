"""Dev > Monitor: this walk's shares reset on a restart; the per-run means and what they feed do not."""
from sieve_player import document as D
from sieve_player.dev.monitor import Monitor, summary, table, walk_order
from sieve_player.graph import Graph
from tests.test_graph import TOOLS, Dec, fan_out


def walk(g, rows):
    g.serving("walk")
    for r in rows:
        g.compute("add", r)
        g.compute("same", r)
        g.progress(r + 1, len(rows))


def test_a_static_node_costs_a_change_and_not_a_row():
    from types import SimpleNamespace as Tool
    const = Tool(NAME="const", KIND="frame", EXPECTS="gray", PRODUCES="gray", DEFAULTS={}, STATIC=True,
                 run=lambda frames, row, params: frames(row) * 0)
    doc = fan_out()
    doc.add_node("const", (0, 400))
    doc.connect("gray", "const")
    g = Graph(doc, Dec(), {**TOOLS, "const": const})
    mon = Monitor(g)
    g.serving("walk")
    for r in range(5):
        g.compute("const", r)
        g.progress(r + 1, 5)
    s = mon.snapshot()
    const_n = next(n for n in s["nodes"] if n["node"] == "const")
    assert const_n["static"] and const_n["runs"] == 1 and const_n["row_ms"] == 0.0
    assert s["cold_row_ms"] == sum(n["row_ms"] for n in s["nodes"]) + s["other_row_ms"] + s["series_row_ms"]
    assert const_n["change_s"] >= const_n["run_ms"] / 1000 and "per change" in table(s)


def test_shares_are_this_walks_and_the_means_outlive_a_restart():
    doc = fan_out()
    g = Graph(doc, Dec(), TOOLS, memo_bytes=200)             # too small: every row reruns
    mon = Monitor(g)
    walk(g, range(5))
    s = mon.snapshot()
    assert [n["node"] for n in s["nodes"]] == walk_order(doc) == ["video", "gray", "add", "same"]
    assert s["done"] == 5 and all(n["runs"] == 5 for n in s["nodes"])
    assert abs(sum(n["share"] for n in s["nodes"]) + s["other_ms"] / (s["wall_s"] * 1000) - 1) < 1e-9
    assert s["cold_row_ms"] == sum(n["row_ms"] for n in s["nodes"]) + s["other_row_ms"] + s["series_row_ms"]
    assert s["series_row_ms"] == 0                           # no chain here; with one its time leaves unprobed for this
    assert all(n["row_ms"] == n["run_ms"] + n["fold_ms"] for n in s["nodes"]) and s["nodes"][1]["fold_ms"] == 0   # gray's density is not asked for here
    assert s["clip_s"] == g.count * s["cold_row_ms"] / 1000 and s["multiple"] == s["footage_s"] / s["clip_s"]
    video, gray, add = s["nodes"][:3]
    assert video["kinds"]["decode"] == 5 and video["run_bytes"] == 4 * 6 * 3
    assert gray["change_s"] >= add["change_s"]              # gray reruns add and same too
    assert s["memo"]["windows"] < 1 and s["cache"]["windows"] is None    # Dec has no limit
    g.memo.limit = 1 << 30
    doc.node("add").params["k"] = 2
    g.sync()
    walk(g, range(5))                                        # a restart in which only add reran
    s = mon.snapshot()
    assert s["changed"] == ("add",)
    runs = {n["node"]: n["runs"] for n in s["nodes"]}
    assert runs["add"] == 5 and runs["gray"] < 5 and runs["video"] == runs["gray"] == runs["same"]   # the rows the small memo lost
    assert s["nodes"][0]["run_ms"] and s["memo"]["row_bytes"] and s["clip_s"]      # still read, from the latest walk each ran in
    assert "x realtime" in summary(s) and "5 / 5 rows" in summary(s)
    assert "changes 1, last touched add" in summary(s)
    assert table(s).splitlines()[2].startswith("video") and f"{runs['video']} decode" in table(s)   # the reads are this walk's
    g.serving("walk")
    for r in range(5):
        g.compute("add", r)                                 # a third walk, every row held: nothing runs, nothing is unprobed
        g.progress(r + 1, 5)
    t = mon.snapshot()
    assert t["done"] == 5 and all(n["runs"] == 0 for n in t["nodes"])
    assert t["cold_row_ms"] == s["cold_row_ms"] and t["other_row_ms"] == s["other_row_ms"]   # the latest walk with figures stands
    mon.close()
    assert g.on_event is None
