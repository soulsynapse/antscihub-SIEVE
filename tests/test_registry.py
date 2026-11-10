"""The registry's class table: which tools strain a class, that the table names only live types, and which pairs look like one tool."""
from types import SimpleNamespace

from sieve_player.registry import Entry, discover, pairs, strains
from sieve_player.registry.__main__ import failures

CLASSES = {"plane": frozenset({"bgr", "gray", "mask"}), "table": frozenset({"blobs", "tracks"})}


def entry(name, expects):
    return Entry(name, SimpleNamespace(EXPECTS=expects))


def tool(name, type):
    return f'SIEVE_TOOL = True\nNAME = "{name}"\nEXPECTS = "{type}"\nPRODUCES = "{type}"\n'


def test_a_proper_subset_of_a_class_strains_and_the_whole_class_or_one_type_does_not():
    whole, subset, single = entry("whole", ("bgr", "gray", "mask")), entry("subset", ("gray", "mask")), entry("single", "gray")
    assert strains([whole, subset, single, entry("broken", None)], CLASSES) == [("subset", "plane", frozenset({"bgr"}))]


def test_the_check_fails_on_a_class_naming_a_type_no_tool_uses(tmp_path):
    root = tmp_path / "toolz"
    root.mkdir()
    (root / "one.py").write_text(tool("one", "gray"), encoding="utf-8")
    found = failures([str(root)], {"plane": frozenset({"gray", "ghost"})})
    assert [m for m in found if "'ghost'" in m and "'plane'" in m]
    assert not [m for m in found if "'gray'" in m and "class" in m]


def test_a_kind_prefixed_twin_sharing_its_sink_is_the_one_pair(tmp_path):
    root = tmp_path / "pairz"
    root.mkdir()
    sink = "def count(result): ...\ndef lines(result): ...\ndef write(path, result): ...\n"
    (root / "csv.py").write_text(tool("csv", "signal") + sink, encoding="utf-8")
    (root / "tracks_csv.py").write_text(tool("tracks-csv", "tracks") + "def fields(dtype): ...\n" + sink, encoding="utf-8")
    (root / "blur.py").write_text(tool("blur", "gray") + "RADIUS = 3\ndef kernel(r): ...\ndef run(frames, row, params): ...\n", encoding="utf-8")
    assert pairs(discover(str(root))) == [("csv", "tracks-csv", True, 3, 4)]
