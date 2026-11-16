"""The registry's derived category: the ordered list over shaped entries, and csv over tools/."""
from types import SimpleNamespace as Tool

from sieve_player.registry import FACETS, category, description, discover, hint, signature


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
