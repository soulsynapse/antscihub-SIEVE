"""The registry's derived category: the ordered list over shaped entries, and csv over tools/;
and a tool's declaration of its params, read or its entry's error."""
from types import SimpleNamespace as Tool

import pytest

from sieve_player.registry import FACETS, category, changes_nothing, code_print, cuts, defaults, description, discover, hint, imported_print, params, reach_of, serves_cut_file, signature


def test_the_first_rule_that_fits_decides_the_category():
    assert category(Tool(EXPECTS=None, PRODUCES="path")) == "source"
    assert category(Tool(EXPECTS="blobs", PRODUCES="signal")) == "measure"
    assert category(Tool(EXPECTS="blobs", PRODUCES="blobs", INPUTS={"plane": "gray"})) == "relate"
    assert category(Tool(EXPECTS=("bgr", "gray"), PRODUCES="same", INPUTS={"roi": "mask"})) == "relate"
    assert category(Tool(EXPECTS="gray", PRODUCES="mask")) == "convert"
    assert category(Tool(EXPECTS="gray", PRODUCES="same")) == "transform"
    assert category(Tool(EXPECTS="signal", PRODUCES="signal")) == "transform"


def test_over_the_catalogue_csv_is_a_transform():
    by_name = {e.name: e.module for e in discover("tools") if e.ok}
    assert category(by_name["csv"]) == "transform"
    assert description(by_name["gray"]) == "BGR to gray by luma (cv2's Rec. 601 weights)"
    assert description(Tool()) == ""
    assert signature(by_name["blobs"]) == "mask, gray → blobs" and signature(by_name["file"]) == "→ path"
    assert "key_params" in FACETS and hint("key_params").startswith("def key_params(params)")
    assert "key_params" not in {f for e in discover("tools") if e.name == "region" for f in e.missing}
    assert cuts(by_name["region"]) and cuts(Tool(cut_extents=lambda params, result: [])) and not cuts(Tool(cut_file=lambda *a: None))
    assert serves_cut_file(by_name["region"]) and not serves_cut_file(Tool(cut_extents=lambda params, result: []))


def test_a_param_is_declared_once_and_a_declaration_that_cannot_be_read_is_its_entrys_error(tmp_path):
    assert "PARAMS" in FACETS and hint("PARAMS").startswith("PARAMS = {") and "DEFAULTS" not in FACETS
    said = Tool(PARAMS={"radius": {"default": 3, "kind": "int", "range": (1, 15)}, "held": {"default": []}})
    assert defaults(said) == {"radius": 3, "held": []} and params(said)["radius"]["range"] == (1, 15)
    assert params(Tool()) == {} and list(defaults(discover("tools")[0].module)) == list(params(discover("tools")[0].module))
    drawn = Tool(PARAMS={"radius": {"default": 3}, "outline": {"default": "box", "changes result": False}, "fill": {"default": 1, "changes result": True}})
    assert changes_nothing(drawn) == {"outline"} and changes_nothing(Tool()) == set() and "changes result" in hint("PARAMS")
    for bad in ({"r": {"kind": "int", "range": (0, 1)}}, {"r": {"default": 3, "kind": "int"}}, {"r": {"default": 3, "kind": "slider"}}, {"r": {"default": 3, "changes result": "no"}},
                {"r": {"default": "a", "kind": "choice", "choices": ()}}, {"r": {"default": 1, "range": (0, 1)}}, ["r"]):
        with pytest.raises(ValueError):
            params(Tool(PARAMS=bad))
    folder = tmp_path / "declared_wrong"
    folder.mkdir()
    (folder / "bad.py").write_text('SIEVE_TOOL = True; NAME = "bad"; PARAMS = {"r": {"default": 3, "kind": "slider"}}', encoding="utf-8")
    (entry,) = discover(str(folder))
    assert not entry.ok and entry.name == "bad" and "slider" in entry.error


def test_a_tools_code_print_is_its_own_file_and_the_shared_ones_and_the_imported_one_is_as_discover_found_it(tmp_path):
    folder = tmp_path / "printed_tools"
    folder.mkdir()
    write = lambda name, text: (folder / name).write_text(text, encoding="utf-8", newline="\n")
    for name in ("a", "b"):
        write(f"{name}.py", f'SIEVE_TOOL = True; NAME = "{name}"\n')
    write("_shared.py", "X = 1\n")
    a, b = (e.module for e in discover(str(folder)))
    was = imported_print(a), imported_print(b)
    assert was == (code_print(a), code_print(b)) and None not in was and was[0] != was[1]
    write("a.py", '"""Said of it."""\nSIEVE_TOOL = True; NAME = "a"  # a comment\n')
    assert (code_print(a), code_print(b)) == was
    write("a.py", 'SIEVE_TOOL = True; NAME = "a"; X = 2\n')       # another length each time, so the file's stamp moves whatever the clock's grain
    assert code_print(a) != was[0] and code_print(b) == was[1]
    write("_shared.py", "X = 2\n")
    assert code_print(b) != was[1]
    discover(str(folder))
    assert (imported_print(a), imported_print(b)) == was and imported_print(Tool()) is None and code_print(Tool()) is None


def test_a_tool_says_its_reach_a_nodes_is_added_down_the_wires_and_a_frame_read_past_it_raises():
    from sieve_player import document as D
    from sieve_player.graph import Graph
    from sieve_player.plan import plan
    from tests.test_graph import Dec, gray

    by_name = {e.name: e.module for e in discover("tools") if e.ok}
    assert (reach_of(by_name["motion"], {}), reach_of(by_name["smooth"], {"reach": 3}), reach_of(by_name["track"], {})) == ((1, 0), (3, 3), (None, 0))
    assert reach_of(Tool(), {}) == reach_of(by_name["background"], {}) == reach_of(Tool(reach_in_rows=lambda params: (1, -1)), {}) == (None, None)
    below = D.from_tools([by_name["gray"], by_name["motion"], by_name["travel"]])
    below.wires.append(D.Wire("motion", "travel"))      # no type of motion's fits travel, and a reach is added whatever the wire carries
    e = plan(below, by_name, "base").entries
    assert (e["video"].reach, e["gray"].reach, e["motion"].reach, e["travel"].reach) == ((0, 0), (0, 0), (1, 0), (2, 0))

    def reads(name, reach, at=0, **more):
        return Tool(NAME=name, KIND="frame", EXPECTS="gray", PRODUCES="gray", reach_in_rows=lambda params: reach, run=lambda frames, row, params: frames(row + at), **more)

    gray = Tool(**{**vars(gray), "reach_in_rows": lambda params: (0, 0)})
    tools = {t.NAME: t for t in (gray, reads("ahead", (0, 3)), reads("behind", (1, 0), -1), reads("both", (1, 1), INPUTS={"other": "gray"}), reads("lies", (0, 0), -1), Tool(NAME="unsaid"))}
    doc = D.from_tools([gray, tools["ahead"], tools["both"]])
    for name, src, into in (("behind", "gray", "in"), ("lies", "gray", "in"), ("unsaid", "both", "in")):
        doc.add_node(name)
        doc.connect(src, name, into)
    doc.connect("behind", "both", "other")
    g = Graph(doc, Dec(), tools)
    assert (g.entry("both").reach, g.entry("unsaid").reach) == ((2, 4), (None, None))        # the furthest of what it reads, a side, and its own
    assert g.compute("behind", 3) is not None
    with pytest.raises(ValueError, match="reach_in_rows"):
        g.compute("lies", 3)
