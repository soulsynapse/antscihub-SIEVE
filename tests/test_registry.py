"""The registry's class table: which tools strain a class, and that the table names only live types."""
from types import SimpleNamespace

from sieve_player.registry import Entry, strains
from sieve_player.registry.__main__ import failures

CLASSES = {"plane": frozenset({"bgr", "gray", "mask"}), "table": frozenset({"blobs", "tracks"})}


def entry(name, expects):
    return Entry(name, SimpleNamespace(EXPECTS=expects))


def test_a_proper_subset_of_a_class_strains_and_the_whole_class_or_one_type_does_not():
    whole, subset, single = entry("whole", ("bgr", "gray", "mask")), entry("subset", ("gray", "mask")), entry("single", "gray")
    assert strains([whole, subset, single, entry("broken", None)], CLASSES) == [("subset", "plane", frozenset({"bgr"}))]


def test_the_check_fails_on_a_class_naming_a_type_no_tool_uses(tmp_path):
    root = tmp_path / "toolz"
    root.mkdir()
    (root / "one.py").write_text('SIEVE_TOOL = True\nNAME = "one"\nEXPECTS = "gray"\nPRODUCES = "gray"\n', encoding="utf-8")
    found = failures([str(root)], {"plane": frozenset({"gray", "ghost"})})
    assert [m for m in found if "'ghost'" in m and "'plane'" in m]
    assert not [m for m in found if "'gray'" in m and "class" in m]
