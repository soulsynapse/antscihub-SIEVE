"""The registry's derived category: the ordered list over shaped entries, and csv over tools/;
and a tool's declaration of its params, read or its entry's error."""
from types import SimpleNamespace as Tool

import pytest

from sieve_player.registry import FACETS, category, defaults, description, discover, hint, params, signature


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


def test_a_param_is_declared_once_and_a_declaration_that_cannot_be_read_is_its_entrys_error(tmp_path):
    assert "PARAMS" in FACETS and hint("PARAMS").startswith("PARAMS = {") and "DEFAULTS" not in FACETS
    said = Tool(PARAMS={"radius": {"default": 3, "kind": "int", "range": (1, 15)}, "held": {"default": []}})
    assert defaults(said) == {"radius": 3, "held": []} and params(said)["radius"]["range"] == (1, 15)
    assert params(Tool()) == {} and list(defaults(discover("tools")[0].module)) == list(params(discover("tools")[0].module))
    for bad in ({"r": {"kind": "int", "range": (0, 1)}}, {"r": {"default": 3, "kind": "int"}}, {"r": {"default": 3, "kind": "slider"}},
                {"r": {"default": "a", "kind": "choice", "choices": ()}}, {"r": {"default": 1, "range": (0, 1)}}, ["r"]):
        with pytest.raises(ValueError):
            params(Tool(PARAMS=bad))
    folder = tmp_path / "declared_wrong"
    folder.mkdir()
    (folder / "bad.py").write_text('SIEVE_TOOL = True; NAME = "bad"; PARAMS = {"r": {"default": 3, "kind": "slider"}}', encoding="utf-8")
    (entry,) = discover(str(folder))
    assert not entry.ok and entry.name == "bad" and "slider" in entry.error
