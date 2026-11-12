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
    assert "pinned" not in doc.to_dict()
    doc.remove_node("gray")
    assert doc.display is None and doc.overlay is None


def test_pinned_is_an_ordered_list_and_a_format_2_id_loads_as_one():
    doc = two_nodes()
    doc.add_node("count", (0.0, 240.0))
    doc.pinned = ["count", "gray"]
    assert D.Document.from_dict(json.loads(json.dumps(doc.to_dict()))).pinned == ["count", "gray"]
    doc.remove_node("count")
    assert doc.pinned == ["gray"]
    doc.remove_node("gray")
    assert doc.pinned == [] and "pinned" not in doc.to_dict()
    old = {**two_nodes().to_dict(), "version": 2, "pinned": "gray"}
    assert D.Document.from_dict(old).pinned == ["gray"]
    assert D.Document.from_dict({**old, "version": 3, "pinned": ["gray", "gray"]}).pinned == ["gray"]
    with pytest.raises(D.FormatError, match="ghost"):
        D.Document.from_dict({**old, "version": 3, "pinned": ["ghost"]})


def test_pinning_a_second_frame_node_unpins_the_first_and_a_series_rides_beside():
    doc = two_nodes()
    doc.add_node("threshold", (0.0, 240.0))
    doc.connect("gray", "threshold")
    doc.add_node("motion", (0.0, 360.0))
    doc.connect("gray", "motion")
    doc.pin("motion", TOOLS)
    doc.pin("gray", TOOLS)
    doc.pin("gray", TOOLS)
    assert doc.pinned == ["motion", "gray"]
    doc.pin("threshold", TOOLS)
    assert doc.pinned == ["motion", "threshold"]
    doc.unpin("motion")
    assert doc.pinned == ["threshold"]


def test_shown_is_the_selection_then_the_pinned_each_once():
    assert D.shown("a", ["b", "c"]) == ["a", "b", "c"]
    assert D.shown("b", ["b", "c"]) == ["b", "c"] and D.shown("c", ["b", "c"]) == ["c", "b"]
    assert D.shown(None, ["b"]) == ["b"] and D.shown("a", []) == ["a"] and D.shown(None, []) == []


def test_band_rides_with_its_node_and_is_absent_until_set():
    doc = two_nodes()
    assert "band" not in doc.to_dict()["nodes"][1]
    doc.node("gray").band = (40, 200.5)
    back = D.Document.from_dict(json.loads(json.dumps(doc.to_dict())))
    assert back.node("gray").band == (40.0, 200.5) and back.node("video").band is None


def test_round_trip(tmp_path):
    doc = two_nodes()
    D.save(doc, tmp_path / "a.sieve")
    assert D.load(tmp_path / "a.sieve") == doc and list(tmp_path.iterdir()) == [tmp_path / "a.sieve"]   # written whole: no part left
    with pytest.raises(OSError):
        D.save(doc, tmp_path / "a.sieve" / "under-a-file")       # a save that fails leaves no part either
    assert list(tmp_path.iterdir()) == [tmp_path / "a.sieve"]


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


def test_the_video_node_produces_what_its_output_param_says():
    doc = D.from_tools(TOOLS)
    assert D.video_output(doc) == D.produces(doc, TOOLS, "video") == "bgr"
    doc.video_node().params["output"] = "gray"
    assert D.produces(doc, TOOLS, "video") == "gray" and D.produces(doc, TOOLS, "rescale") == "gray"
    assert [p.where for p in D.validate(doc, TOOLS) if p.kind == "type"] == ["video -> gray"]   # gray expects bgr
    doc.video_node().params["output"] = "nonsense"
    assert D.video_output(doc) == "bgr"


def test_a_scale_on_the_video_node_loads_as_a_rescale_node_before_every_reader():
    """Format 1 put the decoder's resize on the video node; it is rescale's now, so a saved scale
    becomes that node between the video and each node that read it, and a scale of 1 just goes."""
    doc = D.from_tools([gray, motion])
    doc.connect("video", "motion")
    d = doc.to_dict()
    d["version"], d["nodes"][0]["params"] = 1, {"output": "gray", "scale": 0.5}
    back = D.Document.from_dict(d)
    assert back.node("video").params == {"output": "gray"} and back.node("rescale").params == {"scale": 0.5}
    assert sorted((w.src, w.dst) for w in back.wires) == [("rescale", "gray"), ("rescale", "motion"), ("video", "rescale")]
    d["nodes"][0]["params"] = {"scale": 1.0}
    assert "rescale" not in {n.id for n in D.Document.from_dict(d).nodes} and "scale" not in D.Document.from_dict(d).node("video").params


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


def test_load_fills_missing_params_from_defaults(tmp_path):
    doc = two_nodes()
    doc.add_node("threshold", (0, 240), {})
    D.save(doc, tmp_path / "a.sieve")
    loaded = D.load(tmp_path / "a.sieve", known={"gray": gray, "threshold": threshold})
    assert loaded.node("threshold").params == {"thresh": 128}
    assert loaded.node("gray").params == {"k": 3}
    assert D.load(tmp_path / "a.sieve", known={"gray", "threshold"}).node("threshold").params == {}
