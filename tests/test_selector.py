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
from dummies import pick  # noqa: E402

gray = Tool(NAME="gray", KIND="frame", EXPECTS="bgr", PRODUCES="gray", DEFAULTS={}, run=lambda f, r, p: f(r)[..., 0])
TOOLS = [pick, gray]


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
    doc = D.from_tools([pick, gray])
    D.save(doc, tmp_path / "doc.json")
    return doc


def test_selector_feeds_the_video_node_and_the_registry_knows(tmp_path):
    doc = tree(tmp_path)
    assert doc.selector().id == "pick" and D.is_selector(pick)
    path, why = D.pick_video(doc, TOOLS)
    assert why == "" and path == os.path.normpath(tmp_path / "a.mp4")
    subprocess.check_call([sys.executable, "-m", "sieve_player.registry", "--check"])


def test_the_answer_is_written_into_video_relative_to_the_document(tmp_path):
    doc = tree(tmp_path)
    doc.node("pick").params["order"] = "newest"
    D.pick_video(doc, TOOLS)
    D.save(doc, tmp_path / "doc.json")
    assert D.load(tmp_path / "doc.json").video == "b.mp4"
    doc.node("pick").params.update(recurse=True, pattern="c.*")
    D.pick_video(doc, TOOLS)
    assert doc.video == os.path.join("sub", "c.mp4")


def test_neither_the_video_input_nor_a_selector_is_unfed(tmp_path):
    doc = tree(tmp_path)
    assert D.validate(doc, TOOLS) == []
    doc.disconnect("video")
    assert D.validate(doc, TOOLS) == []


def test_a_path_fits_only_a_path_input(tmp_path):
    doc = tree(tmp_path)
    doc.connect("pick", "gray")
    assert [p.kind for p in D.validate(doc, TOOLS)] == ["type"]
    doc = tree(tmp_path)
    doc.connect("gray", "video")
    assert [(p.kind, p.where) for p in D.validate(doc, TOOLS) if p.kind == "type"] == [("type", "gray -> video")]


def test_runtime_selector_is_none_and_video_key_follows_the_file(tmp_path):
    doc = tree(tmp_path)
    path, _ = D.pick_video(doc, TOOLS)
    g = Graph(doc, Dec(path), TOOLS)
    assert g.compute("pick", 0) is None and g.compute("pick", 1) is None
    before = g.key("video")
    doc.remove_node("pick")
    doc.add_node("pick", params={**pick.DEFAULTS, "order": "newest"})
    doc.connect("pick", "video")
    path2, _ = D.pick_video(doc, TOOLS)
    assert path2 != path
    assert Graph(doc, Dec(path2), TOOLS).key("video") != before


def test_a_rule_matching_nothing_is_reported_on_the_video_node(tmp_path):
    from PySide6.QtWidgets import QApplication
    from sieve_player.window import PlayerWindow

    from dummies import to_gray

    QApplication.instance() or QApplication([])
    tree(tmp_path)
    doc = D.from_tools([pick, to_gray])          # a window asks each tool for its settings widget
    doc.node("pick").params["pattern"] = "*.nothing"
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [pick, to_gray])
    assert win.graph is None
    assert win.pane.video.info.text() == "pick matched nothing"
    assert win.canvas.errors["video"] == "pick matched nothing"
    assert not win.pane.video.button.isEnabled()
    win.close()


def test_dummy_selector_resolves_against_a_tree(tmp_path):
    tree(tmp_path)
    folder = str(tmp_path)
    assert [os.path.basename(p) for p in pick.matches(folder, pick.DEFAULTS)] == ["a.mp4", "b.mp4"]
    assert os.path.basename(pick.select(folder, {**pick.DEFAULTS, "order": "newest"})) == "b.mp4"
    assert len(pick.matches(folder, {**pick.DEFAULTS, "recurse": True})) == 3
    assert pick.select(folder, {**pick.DEFAULTS, "folder": "sub", "pattern": "a*"}) is None
    out = subprocess.check_output([sys.executable, "-m", "sieve_player.registry", "dummies"], text=True)
    assert "pick " in out


def test_canvas_inputs_on_the_video_node_and_a_selector(tmp_path):
    from PySide6.QtWidgets import QApplication
    from sieve_player.canvas import Canvas

    QApplication.instance() or QApplication([])
    doc = tree(tmp_path)
    canvas = Canvas({t.NAME: t for t in TOOLS})
    canvas.set_document(doc)
    assert canvas.inputs(doc.node("video")) == [(D.INPUT, (D.PATH,))]
    assert canvas.inputs(doc.node("pick")) == [] and canvas.output_type(doc.node("pick")) == D.PATH
    doc.disconnect("video")
    assert not canvas.unfed(doc.node("video")) and not canvas.unfed(doc.node("pick"))
