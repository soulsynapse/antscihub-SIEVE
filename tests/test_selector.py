"""One test per `Check: a test` line under "Selector nodes" in spec/graph.md, and the video node's
connector line under "Nodes" in spec/canvas.md."""
import os
import subprocess
import sys
import time
from types import SimpleNamespace as Tool

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sieve_player import document as D  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from tools import file, inrange  # noqa: E402

gray = Tool(NAME="gray", KIND="frame", EXPECTS="bgr", PRODUCES="gray", DEFAULTS={}, run=lambda f, r, p: f(r)[..., 0])
TOOLS = [file, gray]


class Dec:
    fps, count = 30.0, 3

    def __init__(self, path):
        self.path = path

    def read(self, row):
        return None


def tree(tmp_path):
    """doc.json beside a.mp4 and b.mp4, with sub/c.mp4 below; b is newest."""
    for name in ("a.mp4", "b.mp4", "sub/c.mp4"):
        p = tmp_path / name
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(b"")
    now = time.time()
    os.utime(tmp_path / "a.mp4", (now - 20, now - 20))
    os.utime(tmp_path / "b.mp4", (now, now))
    os.utime(tmp_path / "sub" / "c.mp4", (now - 10, now - 10))
    doc = D.from_tools([file, gray])
    D.save(doc, tmp_path / "doc.json")
    return doc


def test_selector_feeds_the_video_node_and_the_registry_knows(tmp_path):
    doc = tree(tmp_path)
    assert doc.selector().id == "file" and D.is_selector(file)
    path, why = D.pick_video(doc, TOOLS)
    assert why == "" and path == os.path.normpath(tmp_path / "a.mp4")
    subprocess.check_call([sys.executable, "-m", "sieve_player.registry", "--check"])


def test_the_answer_is_written_into_video_relative_to_the_document(tmp_path):
    doc = tree(tmp_path)
    doc.node("file").params["order"] = "newest"
    D.pick_video(doc, TOOLS)
    D.save(doc, tmp_path / "doc.json")
    assert D.load(tmp_path / "doc.json").video == "b.mp4"
    doc.node("file").params.update(recurse=True, pattern="c.*")
    D.pick_video(doc, TOOLS)
    assert doc.video == os.path.join("sub", "c.mp4")


def test_neither_the_video_input_nor_a_selector_is_unfed(tmp_path):
    doc = tree(tmp_path)
    assert D.validate(doc, TOOLS) == []
    doc.disconnect("video")
    assert D.validate(doc, TOOLS) == []


def test_a_path_fits_only_a_path_input(tmp_path):
    doc = tree(tmp_path)
    doc.connect("file", "gray")
    assert [p.kind for p in D.validate(doc, TOOLS)] == ["type"]
    doc = tree(tmp_path)
    doc.connect("gray", "video")
    assert [(p.kind, p.where) for p in D.validate(doc, TOOLS) if p.kind == "type"] == [("type", "gray -> video")]


def test_runtime_selector_is_none_and_video_key_follows_the_file(tmp_path):
    doc = tree(tmp_path)
    path, _ = D.pick_video(doc, TOOLS)
    g = Graph(doc, Dec(path), TOOLS)
    assert g.compute("file", 0) is None and g.compute("file", 1) is None
    before = g.key("video")
    doc.remove_node("file")
    doc.add_node("file", params={**file.DEFAULTS, "order": "newest"})
    doc.connect("file", "video")
    path2, _ = D.pick_video(doc, TOOLS)
    assert path2 != path
    assert Graph(doc, Dec(path2), TOOLS).key("video") != before


def test_a_rule_matching_nothing_is_reported_on_the_video_node(tmp_path):
    from PySide6.QtWidgets import QApplication
    from sieve_player.window import PlayerWindow

    from tools import gray as real_gray

    QApplication.instance() or QApplication([])
    tree(tmp_path)
    doc = D.from_tools([file, real_gray])        # a window asks each tool for its settings widget
    doc.node("file").params["pattern"] = "*.nothing"
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [file, real_gray])
    assert win.graph is None
    why = win.canvas.errors["video"]
    assert "file" in why and win.pane.video.info.text() == why      # names the selector; the pane says the same
    assert not win.pane.video.button.isEnabled()
    win.close()


def test_pick_resolves_against_a_tree(tmp_path):
    tree(tmp_path)
    folder = str(tmp_path)
    assert [os.path.basename(p) for p in file.matches(folder, file.DEFAULTS)] == ["a.mp4", "b.mp4"]
    assert os.path.basename(file.select(folder, {**file.DEFAULTS, "order": "newest"})) == "b.mp4"
    assert len(file.matches(folder, {**file.DEFAULTS, "recurse": True})) == 3
    assert file.select(folder, {**file.DEFAULTS, "folder": "sub", "pattern": "a*"}) is None
    out = subprocess.check_output([sys.executable, "-m", "sieve_player.registry", "tools"], text=True)
    assert "file " in out


def test_canvas_inputs_on_the_video_node_and_a_selector(tmp_path):
    from PySide6.QtWidgets import QApplication
    from sieve_player.canvas import Canvas

    QApplication.instance() or QApplication([])
    doc = tree(tmp_path)
    canvas = Canvas({t.NAME: t for t in TOOLS})
    canvas.set_document(doc)
    assert canvas.inputs(doc.node("video")) == [(D.INPUT, (D.PATH,))]
    assert canvas.inputs(doc.node("file")) == [] and canvas.output_type(doc.node("file")) == D.PATH
    doc.disconnect("video")
    assert not canvas.unfed(doc.node("video")) and not canvas.unfed(doc.node("file"))


# -- Path inputs, spec/graph.md, and the path-input connector line in spec/canvas.md -----------
def settings_tree(tmp_path, h=(20, 40)):
    import json

    tree(tmp_path)
    (tmp_path / "colour.json").write_text(json.dumps({"bounds": {"H": list(h), "S": [1, 2], "V": [3, 4]}}), encoding="utf-8")
    from tools import gray as real_gray
    doc = D.from_tools([real_gray, inrange])
    doc.add_node("file", params={**file.DEFAULTS, "pattern": "*.json"})
    doc.connect("file", "inrange", "settings")
    D.save(doc, tmp_path / "doc.json")
    return doc, [file, real_gray, inrange]


def open_window(tmp_path, tools):
    from PySide6.QtWidgets import QApplication
    from sieve_player.window import PlayerWindow

    QApplication.instance() or QApplication([])
    return PlayerWindow(str(tmp_path / "doc.json"), "t", tools)


def test_a_selector_into_a_path_input_lands_params_on_the_node(tmp_path):
    doc, tools = settings_tree(tmp_path)
    assert D.inputs_of(doc, tools, "inrange") == [(D.INPUT, (inrange.EXPECTS,)), ("settings", (D.PATH,))]
    win = open_window(tmp_path, tools)
    said = inrange.load_bounds(str(tmp_path / "colour.json"))
    p, shown = win.doc.node("inrange").params, win.pane.widget("inrange").params()
    assert said and all(p[k] == v and shown[k] == v for k, v in said.items())
    assert "colour.json" in win.pane.notes["inrange"].text() and "inrange" not in win.canvas.errors
    win.close()


def test_a_path_input_validates_like_the_video_input(tmp_path):
    doc, tools = settings_tree(tmp_path)
    doc.disconnect("inrange", "settings")
    assert D.validate(doc, tools) == []
    doc.connect("gray", "inrange", "settings")
    assert [(p.kind, p.where) for p in D.validate(doc, tools)] == [("type", "gray -> inrange")]


def test_a_file_the_loader_rejects_is_said_on_the_node_and_params_stay(tmp_path):
    doc, tools = settings_tree(tmp_path, h=(500, 1))
    win = open_window(tmp_path, tools)
    err = win.canvas.errors["inrange"]
    assert err.startswith("settings") and win.pane.notes["inrange"].text() == err     # names the input; the pane says the same
    p = win.doc.node("inrange").params
    assert {k: p[k] for k in inrange.DEFAULTS} == inrange.DEFAULTS
    win.close()


def test_canvas_pins_and_placing_from_a_pending_path_wire(tmp_path):
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QApplication
    from sieve_player.canvas import Canvas

    QApplication.instance() or QApplication([])
    doc, tools = settings_tree(tmp_path)
    canvas = Canvas({t.NAME: t for t in tools})
    canvas.set_document(doc)
    node = doc.node("inrange")
    a, b = canvas.pin_in(node, D.INPUT), canvas.pin_in(node, "settings")
    assert a.y() == b.y() and a.x() < b.x()
    doc.disconnect("inrange", "settings")
    canvas._pending = ("out", "file", None)
    assert ("inrange", "") in canvas.menu_entries() and ("gray", "") not in canvas.menu_entries()
    new = canvas.place("inrange", QPointF(0, 0))
    assert doc.source(new.id, "settings").src == "file" and doc.source(new.id) is None


def test_a_driven_knob_is_greyed_until_the_wire_is_broken(tmp_path):
    doc, tools = settings_tree(tmp_path)
    win = open_window(tmp_path, tools)
    w = win.pane.widget("inrange")
    said = inrange.load_bounds(str(tmp_path / "colour.json"))
    assert all(not w._rows[k].isEnabled() and "file" in w._rows[k].toolTip() for k in said)
    assert not w.button.isEnabled()
    win.doc.disconnect("inrange", "settings")
    win.sync()
    assert all(r.isEnabled() for r in w._rows.values()) and w.button.isEnabled()
    assert all(win.doc.node("inrange").params[k] == v for k, v in said.items())
    win.close()


def test_clicking_a_match_makes_it_the_choice_and_a_stale_choice_falls_back(tmp_path):
    from PySide6.QtCore import Qt

    tree(tmp_path)
    from tools import gray as real_gray
    doc = D.from_tools([file, real_gray])
    D.save(doc, tmp_path / "doc.json")
    win = open_window(tmp_path, [file, real_gray])
    w = win.pane.widget("file")
    assert [w.list.item(i).data(Qt.UserRole) for i in range(w.list.count())] == ["a.mp4", "b.mp4"]
    assert win.doc.video == "a.mp4" and w.status.text() == ""
    w.list.itemClicked.emit(w.list.item(1))
    assert win.doc.node("file").params["choice"] == "b.mp4" and win.doc.video == "b.mp4"
    w.set_params({**w.params(), "pattern": "a*"})                   # the choice is no longer a match
    assert win.doc.video == "a.mp4" and win.doc.node("file").params["choice"] == "b.mp4"
    assert w.status.text()                                          # and the card says so
    w.set_params({**w.params(), "pattern": "*.mp4"})
    w.list.itemClicked.emit(w.list.item(1))                         # clicking the choice clears it
    assert win.doc.node("file").params["choice"] == "" and w.status.text() == ""
    win.close()
