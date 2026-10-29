"""The document: its imports, round trips, versions, unresolved and foreign keys, list building, validation and paths."""
import json
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace as Tool

import pytest

from sieve_player import document as D

gray = Tool(NAME="gray", KIND="frame", EXPECTS="bgr", PRODUCES="gray", DEFAULTS={})
rescale = Tool(NAME="rescale", KIND="frame", EXPECTS=("bgr", "gray"), PRODUCES="same", DEFAULTS={"scale": 0.5})
threshold = Tool(NAME="threshold", KIND="frame", EXPECTS="gray", PRODUCES="gray", DEFAULTS={"thresh": 128})
motion = Tool(NAME="motion", KIND="series", EXPECTS="gray", DEFAULTS={"gate": 2.0})
TOOLS = [gray, rescale, threshold, motion]


def two_nodes():
    doc = D.Document(video="clip.mp4")
    doc.add_node(D.VIDEO_TOOL, (0, 0))
    doc.add_node("gray", (10.5, 120), {"k": 3})
    doc.connect("video", "gray")
    doc.display = doc.overlay = "gray"
    return doc


def test_import_is_light():
    code = "import sys, sieve_player.document; print(sorted(sys.modules))"
    mods = eval(subprocess.check_output([sys.executable, "-c", code], text=True))
    assert not [m for m in mods if m.split(".")[0] in ("PySide6", "shiboken6", "cv2")]
    assert not [m for m in mods if m in ("sieve_player.canvas", "sieve_player.window")]


def test_holds_nodes_wires_flags_video():
    doc = two_nodes()
    assert doc.node("gray") == D.Node("gray", "gray", {"k": 3}, (10.5, 120.0))
    assert doc.wires == [D.Wire("video", "gray", D.INPUT)]
    assert doc.display == "gray" and doc.overlay == "gray" and doc.video == "clip.mp4"
    doc.remove_node("gray")
    assert doc.display is None and doc.overlay is None


def test_band_rides_with_its_node_and_is_absent_until_set():
    doc = two_nodes()
    assert "band" not in doc.to_dict()["nodes"][1]
    doc.node("gray").band = (40, 200.5)
    back = D.Document.from_dict(json.loads(json.dumps(doc.to_dict())))
    assert back.node("gray").band == (40.0, 200.5) and back.node("video").band is None


def test_round_trip(tmp_path):
    doc = two_nodes()
    D.save(doc, tmp_path / "a.sieve")
    assert D.load(tmp_path / "a.sieve") == doc


def test_file_is_versioned_readable_json(tmp_path):
    D.save(two_nodes(), tmp_path / "a.sieve")
    text = (tmp_path / "a.sieve").read_text(encoding="utf-8")
    assert json.loads(text)["version"] == D.VERSION
    assert '"gray"' in text and '"video"' in text


def test_newer_version_refused(tmp_path):
    (tmp_path / "a.sieve").write_text(json.dumps({"version": D.VERSION + 1, "nodes": []}), encoding="utf-8")
    with pytest.raises(D.FormatError, match=f"{D.VERSION + 1}.*{D.VERSION}"):
        D.load(tmp_path / "a.sieve")


def test_unresolved_tool_kept(tmp_path):
    doc = two_nodes()
    doc.add_node("nope", (0, 240), {"x": 1})
    D.save(doc, tmp_path / "a.sieve")
    loaded = D.load(tmp_path / "a.sieve", known={"gray"})
    assert loaded.node("nope").unresolved and not loaded.node("gray").unresolved
    assert loaded.node("nope") == doc.node("nope")
    D.save(loaded, tmp_path / "b.sieve")
    assert json.load(open(tmp_path / "b.sieve")) == json.load(open(tmp_path / "a.sieve"))


def test_foreign_keys_survive(tmp_path):
    doc = two_nodes()
    doc.extra["colour"] = "teal"
    doc.node("gray").extra["note"] = "hi"
    D.save(doc, tmp_path / "a.sieve")
    loaded = D.load(tmp_path / "a.sieve")
    assert loaded.extra["colour"] == "teal" and loaded.node("gray").extra["note"] == "hi"


def test_from_tools_wires_nearest_producer():
    doc = D.from_tools(TOOLS)
    assert [(w.src, w.dst) for w in doc.wires] == [("video", "gray"), ("gray", "rescale"),
                                                   ("rescale", "threshold"), ("threshold", "motion")]
    assert doc.nodes[0].tool == D.VIDEO_TOOL and [n.pos[1] for n in doc.nodes] == sorted(n.pos[1] for n in doc.nodes)
    assert doc.display == "threshold" and doc.node("threshold").params == {"thresh": 128}


def test_validate_type_cycle_unfed():
    doc = D.from_tools(TOOLS)
    doc.connect("video", "threshold")                       # bgr into a gray input
    assert [p.where for p in D.validate(doc, TOOLS) if p.kind == "type"] == ["video -> threshold"]
    doc = D.from_tools(TOOLS)
    doc.connect("threshold", "gray")                        # gray <- rescale <- threshold <- gray
    assert [p.kind for p in D.validate(doc, TOOLS)].count("cycle") == 1
    doc = D.from_tools(TOOLS)
    doc.disconnect("rescale")
    assert [p.where for p in D.validate(doc, TOOLS) if p.kind == "unfed"] == ["rescale"]


def test_video_path_relative_to_document(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "clip.mp4").write_bytes(b"")
    D.save(two_nodes(), tmp_path / "a" / "doc.sieve")
    shutil.move(tmp_path / "a", tmp_path / "b")
    doc = D.load(tmp_path / "b" / "doc.sieve")
    assert doc.video == "clip.mp4" and os.path.exists(doc.video_path())
    assert doc.video_path() == os.path.normpath(tmp_path / "b" / "clip.mp4")
    doc.video = os.path.abspath("elsewhere.mp4")
    assert doc.video_path() == doc.video
