from pathlib import Path

import pytest

from sieve.debt import (
    LEDGER_NAME,
    MODULE_QUALNAME,
    Entry,
    EnumerationError,
    Owed,
    enumerate_markers,
    main,
    serialize,
)


def test_owed_is_the_marker_exception():
    assert issubclass(Owed, Exception)


def make_tree(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, source in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return tmp_path


STORE = (
    '"""Store placeholder; behavior governed by ARCHITECTURE.md section 5."""\n'
    "from sieve.debt import Owed\n"
    "\n"
    'raise Owed("store: content-addressed blob store")\n'
)

KERNEL = (
    "from sieve.debt import Owed\n"
    "\n"
    "\n"
    "def lower(tool):\n"
    '    """Quoted from the settled record."""\n'
    '    raise Owed("kernel: lower() producing a Resample")\n'
    "\n"
    "\n"
    "class Resample:\n"
    "    def apply(self, image):\n"
    '        raise Owed("Resample.apply")\n'
)


def test_finds_module_level_marker(tmp_path):
    make_tree(tmp_path, {"pkg/store.py": STORE})
    assert enumerate_markers(tmp_path, roots=("pkg",)) == [
        Entry("pkg/store.py", MODULE_QUALNAME, "store: content-addressed blob store")
    ]


def test_finds_callable_markers_with_qualnames(tmp_path):
    make_tree(tmp_path, {"pkg/kernel.py": KERNEL})
    assert enumerate_markers(tmp_path, roots=("pkg",)) == [
        Entry("pkg/kernel.py", "Resample.apply", "Resample.apply"),
        Entry("pkg/kernel.py", "lower", "kernel: lower() producing a Resample"),
    ]


def test_output_is_sorted_and_deterministic(tmp_path):
    make_tree(tmp_path, {"pkg/b.py": STORE, "pkg/a.py": STORE, "pkg/sub/c.py": KERNEL})
    first = enumerate_markers(tmp_path, roots=("pkg",))
    assert first == enumerate_markers(tmp_path, roots=("pkg",))
    assert [(e.path, e.qualname) for e in first] == [
        ("pkg/a.py", MODULE_QUALNAME),
        ("pkg/b.py", MODULE_QUALNAME),
        ("pkg/sub/c.py", "Resample.apply"),
        ("pkg/sub/c.py", "lower"),
    ]


def test_markerless_tree_is_empty(tmp_path):
    make_tree(tmp_path, {"pkg/real.py": "def add(a, b):\n    return a + b\n"})
    assert enumerate_markers(tmp_path, roots=("pkg",)) == []


def test_adjacent_literal_concatenation_is_one_literal(tmp_path):
    source = (
        "from sieve.debt import Owed\n"
        "\n"
        "\n"
        "def f():\n"
        '    raise Owed("part one, " "part two")\n'
    )
    make_tree(tmp_path, {"pkg/m.py": source})
    (entry,) = enumerate_markers(tmp_path, roots=("pkg",))
    assert entry.reason == "part one, part two"


CANON = "from sieve.debt import Owed\n"

VIOLATIONS = {
    "f_string_reason": CANON + 'def f():\n    raise Owed(f"owed {1}")\n',
    "non_literal_reason": CANON + 'REASON = "x"\ndef f():\n    raise Owed(REASON)\n',
    "no_reason": CANON + "def f():\n    raise Owed()\n",
    "empty_reason": CANON + 'def f():\n    raise Owed("")\n',
    "aliased_import": 'from sieve.debt import Owed as Debt\ndef f():\n    raise Debt("x")\n',
    "attribute_raise": 'import sieve.debt\ndef f():\n    raise sieve.debt.Owed("x")\n',
    "missing_canonical_import": 'def f():\n    raise Owed("x")\n',
    "raise_inside_if": CANON + 'def f():\n    if True:\n        raise Owed("x")\n',
    "raise_not_sole_statement": CANON + 'def f():\n    x = 1\n    raise Owed("x")\n',
    "module_raise_with_extra_statements": CANON + 'x = 1\nraise Owed("x")\n',
    "unparseable": "def f(:\n",
}


@pytest.mark.parametrize("source", VIOLATIONS.values(), ids=VIOLATIONS.keys())
def test_rule_violations_are_enumeration_errors(tmp_path, source):
    make_tree(tmp_path, {"pkg/bad.py": source})
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("pkg",))


def test_undecodable_file_is_an_enumeration_error(tmp_path):
    bad = tmp_path / "pkg" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"\x80\x81\x82")
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("pkg",))


def test_duplicate_key_is_an_enumeration_error(tmp_path):
    source = CANON + 'def f():\n    raise Owed("a")\n\ndef f():\n    raise Owed("b")\n'
    make_tree(tmp_path, {"pkg/m.py": source})
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("pkg",))


def test_missing_root_is_an_enumeration_error(tmp_path):
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("nowhere",))


HEADER = (
    b"# SIEVE automatic ledger. Generated; never hand-edit.\n"
    b"# Regenerate: python -m sieve.debt write\n"
    b"format-version: 1\n"
    b"marker-rule: v1\n"
)


def test_serialize_golden_bytes():
    entries = [
        Entry("src/sieve/store.py", MODULE_QUALNAME, "store: content-addressed blob store"),
        Entry("src/sieve/kernel.py", "lower", "kernel: lower() producing a Resample"),
    ]
    assert serialize(entries) == HEADER + (
        b"\n"
        b"src/sieve/kernel.py :: lower\n"
        b"    kernel: lower() producing a Resample\n"
        b"src/sieve/store.py :: <module>\n"
        b"    store: content-addressed blob store\n"
    )


def test_serialize_zero_entries_is_header_only():
    assert serialize([]) == HEADER


def test_serialize_multiline_reason():
    entries = [Entry("pkg/m.py", "f", "first\n\nsecond")]
    assert serialize(entries) == HEADER + (
        b"\n"
        b"pkg/m.py :: f\n"
        b"    first\n"
        b"    \n"
        b"    second\n"
    )


def test_serialize_is_byte_deterministic():
    entries = [Entry("pkg/m.py", "f", "reason")]
    out = serialize(entries)
    assert out == serialize(list(entries))
    assert b"\r" not in out


def test_write_mode_writes_the_ledger(tmp_path, capsys):
    make_tree(tmp_path, {"src/sieve/store.py": STORE})
    (tmp_path / "tests").mkdir()
    assert main(["write", str(tmp_path)]) == 0
    ledger = tmp_path / LEDGER_NAME
    assert ledger.read_bytes() == serialize(enumerate_markers(tmp_path))
    assert b"src/sieve/store.py :: <module>" in ledger.read_bytes()
    assert "1 entries" in capsys.readouterr().out


def test_write_mode_requires_the_subcommand(capsys):
    assert main([]) == 2
    assert main(["frobnicate"]) == 2
    assert "usage" in capsys.readouterr().err
