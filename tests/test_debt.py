import subprocess
from pathlib import Path

import pytest

from sieve.debt import (
    FILE_QUALNAME,
    LEDGER_NAME,
    MODULE_QUALNAME,
    Entry,
    EnumerationError,
    Owed,
    entry_diff,
    enumerate_markers,
    main,
    parse,
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


def store_src(stamp: str) -> str:
    return (
        '"""Store placeholder; behavior governed by ARCHITECTURE.md section 5."""\n'
        "from sieve.debt import Owed\n"
        "\n"
        f'raise Owed("{stamp}: store: content-addressed blob store")\n'
    )


def kernel_src(stamp_a: str, stamp_b: str) -> str:
    return (
        "from sieve.debt import Owed\n"
        "\n"
        "\n"
        "def lower(tool):\n"
        '    """Quoted from the settled record."""\n'
        f'    raise Owed("{stamp_a}: kernel: lower() producing a Resample")\n'
        "\n"
        "\n"
        "class Resample:\n"
        "    def apply(self, image):\n"
        f'        raise Owed("{stamp_b}: Resample.apply")\n'
    )


STORE = store_src("20260801T120000Z")


def test_finds_module_level_marker(tmp_path):
    make_tree(tmp_path, {"pkg/store.py": STORE})
    assert enumerate_markers(tmp_path, roots=("pkg",)) == [
        Entry(
            "pkg/store.py",
            MODULE_QUALNAME,
            "20260801T120000Z",
            "store: content-addressed blob store",
        )
    ]


def test_finds_callable_markers_with_qualnames(tmp_path):
    make_tree(tmp_path, {"pkg/kernel.py": kernel_src("20260801T120001Z", "20260801T120002Z")})
    assert enumerate_markers(tmp_path, roots=("pkg",)) == [
        Entry("pkg/kernel.py", "Resample.apply", "20260801T120002Z", "Resample.apply"),
        Entry(
            "pkg/kernel.py",
            "lower",
            "20260801T120001Z",
            "kernel: lower() producing a Resample",
        ),
    ]


def test_output_is_sorted_and_deterministic(tmp_path):
    make_tree(
        tmp_path,
        {
            "pkg/b.py": store_src("20260801T120004Z"),
            "pkg/a.py": store_src("20260801T120003Z"),
            "pkg/sub/c.py": kernel_src("20260801T120005Z", "20260801T120006Z"),
        },
    )
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
        '    raise Owed("20260801T120000Z: part one, " "part two")\n'
    )
    make_tree(tmp_path, {"pkg/m.py": source})
    (entry,) = enumerate_markers(tmp_path, roots=("pkg",))
    assert entry.stamp == "20260801T120000Z"
    assert entry.reason == "part one, part two"


CANON = "from sieve.debt import Owed\n"
S = "20260801T120000Z"

VIOLATIONS = {
    "f_string_reason": CANON + f'def f():\n    raise Owed(f"{S}: owed {{1}}")\n',
    "non_literal_reason": CANON + f'REASON = "{S}: x"\ndef f():\n    raise Owed(REASON)\n',
    "no_reason": CANON + "def f():\n    raise Owed()\n",
    "empty_reason": CANON + 'def f():\n    raise Owed("")\n',
    "aliased_import": f'from sieve.debt import Owed as Debt\ndef f():\n    raise Debt("{S}: x")\n',
    "attribute_raise": f'import sieve.debt\ndef f():\n    raise sieve.debt.Owed("{S}: x")\n',
    "missing_canonical_import": f'def f():\n    raise Owed("{S}: x")\n',
    "raise_inside_if": CANON + f'def f():\n    if True:\n        raise Owed("{S}: x")\n',
    "raise_not_sole_statement": CANON + f'def f():\n    x = 1\n    raise Owed("{S}: x")\n',
    "module_raise_with_extra_statements": CANON + f'x = 1\nraise Owed("{S}: x")\n',
    "unparseable": "def f(:\n",
    "cr_in_reason": CANON + f'def f():\n    raise Owed("{S}: a\\rb")\n',
    "unicode_line_separator_in_reason": CANON + f'def f():\n    raise Owed("{S}: a\\u2028b")\n',
    # Rule v2: the stamp is required and validated at enumeration.
    "missing_stamp": CANON + 'def f():\n    raise Owed("no stamp here")\n',
    "malformed_stamp": CANON + 'def f():\n    raise Owed("2026-08-01T12:00:00Z: x")\n',
    "nonsense_calendar": CANON + 'def f():\n    raise Owed("20261301T120000Z: x")\n',
    "pre_epoch_stamp": CANON + 'def f():\n    raise Owed("20250101T120000Z: x")\n',
    "future_stamp": CANON + 'def f():\n    raise Owed("20991231T235959Z: x")\n',
    "stamp_without_reason": CANON + f'def f():\n    raise Owed("{S}: ")\n',
}


@pytest.mark.parametrize("source", VIOLATIONS.values(), ids=VIOLATIONS.keys())
def test_rule_violations_are_enumeration_errors(tmp_path, source):
    make_tree(tmp_path, {"pkg/bad.py": source})
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("pkg",))


def test_bom_and_coding_cookie_files_are_parseable(tmp_path):
    bom = tmp_path / "pkg" / "bom.py"
    bom.parent.mkdir(parents=True)
    bom.write_bytes(b"\xef\xbb\xbf" + STORE.encode("utf-8"))
    latin = tmp_path / "pkg" / "latin.py"
    latin.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\nx = 1\n")
    (entry,) = enumerate_markers(tmp_path, roots=("pkg",))
    assert entry.path == "pkg/bom.py"


def test_undecodable_python_file_is_an_enumeration_error(tmp_path):
    bad = tmp_path / "pkg" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"\x80\x81\x82")
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("pkg",))


def test_duplicate_key_is_an_enumeration_error(tmp_path):
    source = CANON + (
        'def f():\n    raise Owed("20260801T120000Z: a")\n'
        '\ndef f():\n    raise Owed("20260801T120001Z: b")\n'
    )
    make_tree(tmp_path, {"pkg/m.py": source})
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("pkg",))


def test_duplicate_stamp_is_an_enumeration_error(tmp_path):
    make_tree(
        tmp_path,
        {"pkg/a.py": store_src("20260801T120000Z"), "pkg/b.py": store_src("20260801T120000Z")},
    )
    with pytest.raises(EnumerationError, match="duplicate stamp"):
        enumerate_markers(tmp_path, roots=("pkg",))


def test_missing_root_is_an_enumeration_error(tmp_path):
    with pytest.raises(EnumerationError):
        enumerate_markers(tmp_path, roots=("nowhere",))


# --- the text surface -------------------------------------------------------


def test_text_marker_enumerates_with_file_qualname(tmp_path):
    make_tree(
        tmp_path,
        {"docs/thing.md": "# A record\n\nOwed: 20260802T090000Z: the design owed\n"},
    )
    assert enumerate_markers(tmp_path, roots=("docs",)) == [
        Entry("docs/thing.md", FILE_QUALNAME, "20260802T090000Z", "the design owed")
    ]


def test_owed_word_midline_or_indented_is_prose(tmp_path):
    make_tree(
        tmp_path,
        {
            "docs/a.md": (
                "Catching Owed: outside the machinery is out of contract.\n"
                "  Owed: 20260802T090000Z: indented, so prose\n"
                "The word Owed alone is fine.\n"
            )
        },
    )
    assert enumerate_markers(tmp_path, roots=("docs",)) == []


def test_malformed_text_marker_is_an_enumeration_error(tmp_path):
    for bad in (
        "Owed: no stamp\n",
        "Owed:20260802T090000Z: no space\n",
        "Owed: 20260802T090000Z:missing space\n",
        "Owed: 20260802T090000Z: \n",
    ):
        make_tree(tmp_path, {"docs/bad.md": bad})
        with pytest.raises(EnumerationError):
            enumerate_markers(tmp_path, roots=("docs",))


def test_two_text_markers_in_one_file_is_an_enumeration_error(tmp_path):
    make_tree(
        tmp_path,
        {
            "docs/bad.md": (
                "Owed: 20260802T090000Z: one\n"
                "\n"
                "Owed: 20260802T090001Z: two\n"
            )
        },
    )
    with pytest.raises(EnumerationError, match="duplicate marker key"):
        enumerate_markers(tmp_path, roots=("docs",))


def test_non_utf8_file_is_outside_the_text_surface(tmp_path):
    bad = tmp_path / "docs" / "blob.bin"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"\x00\x80\x81Owed: junk")
    assert enumerate_markers(tmp_path, roots=("docs",)) == []


def test_crlf_checkout_enumerates_identical_bytes(tmp_path):
    lf = make_tree(tmp_path / "lf", {"d/r.md": "x\nOwed: 20260802T090000Z: same\n"})
    crlf_file = tmp_path / "crlf" / "d" / "r.md"
    crlf_file.parent.mkdir(parents=True)
    crlf_file.write_bytes(b"x\r\nOwed: 20260802T090000Z: same\r\n")
    a = enumerate_markers(lf, roots=("d",))
    b = enumerate_markers(tmp_path / "crlf", roots=("d",))
    assert serialize(a) == serialize(b)


# --- the git-index universe -------------------------------------------------


def git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)


def test_git_universe_sees_untracked_and_honors_gitignore(tmp_path):
    make_tree(
        tmp_path,
        {
            "pkg/store.py": STORE,
            "junk/ignored.md": "Owed: 20260899T000000Z: never scanned\n",
            ".gitignore": "junk/\n",
        },
    )
    git_init(tmp_path)
    entries = enumerate_markers(tmp_path)
    assert [(e.path, e.qualname) for e in entries] == [("pkg/store.py", MODULE_QUALNAME)]


def test_non_git_root_without_roots_is_an_enumeration_error(tmp_path):
    with pytest.raises(EnumerationError, match="git"):
        enumerate_markers(tmp_path)


# --- the ledger format ------------------------------------------------------


HEADER = (
    b"# SIEVE automatic ledger. Generated; never hand-edit.\n"
    b"# Regenerate: python -m sieve.debt write\n"
    b"format-version: 2\n"
    b"marker-rule: v2\n"
)


def test_serialize_golden_bytes():
    entries = [
        Entry(
            "src/sieve/store.py",
            MODULE_QUALNAME,
            "20260801T120001Z",
            "store: content-addressed blob store",
        ),
        Entry(
            "src/sieve/kernel.py",
            "lower",
            "20260801T120000Z",
            "kernel: lower() producing a Resample",
        ),
    ]
    assert serialize(entries) == HEADER + (
        b"\n"
        b"src/sieve/kernel.py :: lower :: 20260801T120000Z\n"
        b"    kernel: lower() producing a Resample\n"
        b"src/sieve/store.py :: <module> :: 20260801T120001Z\n"
        b"    store: content-addressed blob store\n"
    )


def test_serialize_zero_entries_is_header_only():
    assert serialize([]) == HEADER


def test_serialize_multiline_reason():
    entries = [Entry("pkg/m.py", "f", "20260801T120000Z", "first\n\nsecond")]
    assert serialize(entries) == HEADER + (
        b"\n"
        b"pkg/m.py :: f :: 20260801T120000Z\n"
        b"    first\n"
        b"    \n"
        b"    second\n"
    )


def test_serialize_is_byte_deterministic():
    entries = [Entry("pkg/m.py", "f", "20260801T120000Z", "reason")]
    out = serialize(entries)
    assert out == serialize(list(entries))
    assert b"\r" not in out


def test_write_mode_writes_the_ledger(tmp_path, capsys):
    make_tree(tmp_path, {"src/sieve/store.py": STORE})
    git_init(tmp_path)
    assert main(["write", str(tmp_path)]) == 0
    ledger = tmp_path / LEDGER_NAME
    assert ledger.read_bytes() == serialize(enumerate_markers(tmp_path))
    assert b"src/sieve/store.py :: <module> :: 20260801T120000Z" in ledger.read_bytes()
    assert "1 entries" in capsys.readouterr().out


def test_write_mode_requires_the_subcommand(capsys):
    assert main([]) == 2
    assert main(["frobnicate"]) == 2
    assert "usage" in capsys.readouterr().err


def test_parse_round_trips_serialize():
    entries = [
        Entry("pkg/a.py", MODULE_QUALNAME, "20260801T120000Z", "one"),
        Entry("pkg/b.py", "C.m", "20260801T120001Z", "first\n\nsecond"),
    ]
    assert parse(serialize(entries)) == entries
    assert parse(serialize([])) == []


def test_parse_never_reads_header_lines_as_entries():
    doctored = HEADER + b"# future field :: looks :: like an entry\n" + (
        b"\n"
        b"pkg/m.py :: f :: 20260801T120000Z\n"
        b"    reason\n"
    )
    assert parse(doctored) == [Entry("pkg/m.py", "f", "20260801T120000Z", "reason")]


def test_excluded_prefix_is_not_walked(tmp_path):
    make_tree(
        tmp_path,
        {
            "pkg/real.py": "x = 1\n",
            "pkg/skip/marker.py": STORE,
            "pkg/skip/broken.py": "def f(:\n",
        },
    )
    assert enumerate_markers(tmp_path, roots=("pkg",), excluded=("pkg/skip",)) == []


# --- the entry diff ---------------------------------------------------------


def test_entry_diff_reports_added_removed_changed():
    old = [
        Entry("a.py", "f", "20260801T120000Z", "same"),
        Entry("b.py", "g", "20260801T120001Z", "old"),
        Entry("c.py", "h", "20260801T120002Z", "gone"),
    ]
    new = [
        Entry("a.py", "f", "20260801T120000Z", "same"),
        Entry("b.py", "g", "20260801T120001Z", "new"),
        Entry("d.py", "i", "20260801T120003Z", "fresh"),
    ]
    assert entry_diff(old, new) == (
        "changed: b.py :: g :: 20260801T120001Z\n"
        "removed: c.py :: h :: 20260801T120002Z\n"
        "added:   d.py :: i :: 20260801T120003Z"
    )


def test_entry_diff_joins_on_the_stamp_so_moves_are_exact():
    old = [Entry("old/place.py", "f", "20260801T120000Z", "same reason")]
    new = [Entry("new/place.py", "f", "20260801T120000Z", "same reason")]
    assert entry_diff(old, new) == (
        "moved:   old/place.py :: f -> new/place.py :: f [20260801T120000Z]"
    )


def test_entry_diff_move_plus_reword_stays_one_identity():
    old = [Entry("old/place.py", "f", "20260801T120000Z", "before")]
    new = [Entry("new/place.py", "f", "20260801T120000Z", "after")]
    assert entry_diff(old, new) == (
        "moved:   old/place.py :: f -> new/place.py :: f [20260801T120000Z]\n"
        "changed: new/place.py :: f :: 20260801T120000Z"
    )


def test_entry_diff_flags_identity_churn_at_one_location():
    old = [Entry("a.py", "f", "20260801T120000Z", "reason")]
    new = [Entry("a.py", "f", "20260801T120009Z", "reason")]
    out = entry_diff(old, new)
    assert "removed: a.py :: f :: 20260801T120000Z" in out
    assert "added:   a.py :: f :: 20260801T120009Z" in out
    assert "rekeyed? a.py :: f (20260801T120000Z -> 20260801T120009Z)" in out
