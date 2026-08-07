"""The identifier half of ADR-1's rename: `src/sieve/` never says the dead word.

`dead_language` in `scripts/doc_index.py` holds the prose and deliberately
passes anything fused into an identifier or a path, because a checker that
fires on `filter_base.py` cannot be pointed at code. This is the other half,
and it is the mirror image: text, not prose — identifiers, comments, and string
literals alike, since `filter_id` in a field name and "filter" in a docstring
are the same rename left half-done. The identity *values* (`"crop"`,
`"detect"`, …) are frozen and none of them is a dead word, so freezing them
costs this gate nothing (`adr/tools-not-filters.md`).

The exception list is empty and the emptiness is asserted, which is the whole
of "shrink-only" here: v3 reads no v2 file, so no module has a licensed reason
to spell v2's vocabulary (`adr/v2-does-not-import.md`). What would license an
entry is a revived `compat/`, and reviving it means deleting that assertion —
a visible widening rather than a line appended to a list nobody rereads.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import Path

import pytest

import sieve

SRC = Path(str(sieve.__file__)).resolve().parent

#: `(the dead word, the one live spelling that contains it, the verdict)`.
#: The ADR slug is the rename naming itself; every other occurrence of the word
#: is the rename unfinished. Grows a row per buried word.
DEAD_IDENTIFIERS = (("filter", "tools-not-filters", "adr/tools-not-filters.md"),)

#: `(module relative to src/sieve, dead word)` for a spelling something licenses.
#: Empty, and `test_the_exception_list_is_empty` is what keeps it that way.
SPELLED_BEFORE_THE_RENAME: frozenset[tuple[str, str]] = frozenset()


def _hits(modules: Iterable[Path], root: Path) -> Iterator[tuple[str, str, int]]:
    """`(module, dead word, line number)` for every dead spelling in `modules`.

    Read as text rather than as an AST: a comment is not a node, and a rename
    that stopped at the identifiers leaves its evidence in the comments.
    """
    for path in sorted(modules):
        relative = path.relative_to(root).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for word, live, _ in DEAD_IDENTIFIERS:
                bare = line.replace(live, "")
                if re.search(re.escape(word), bare, re.IGNORECASE):
                    yield (relative, word, lineno)


@pytest.fixture(scope="module")
def spelled() -> list[tuple[str, str, int]]:
    return list(_hits(SRC.rglob("*.py"), SRC))


def test_no_module_spells_a_pre_rename_identifier(
    spelled: list[tuple[str, str, int]],
) -> None:
    verdicts = {word: verdict for word, _, verdict in DEAD_IDENTIFIERS}
    undeclared = [hit for hit in spelled if (hit[0], hit[1]) not in SPELLED_BEFORE_THE_RENAME]
    assert undeclared == [], "the rename is unfinished at: " + "; ".join(
        f"{module}:{lineno}: {word!r} is dead ({verdicts[word]})"
        for module, word, lineno in undeclared
    )


def test_the_exception_list_is_empty() -> None:
    """v3 reads no v2 file, so nothing has earned an entry (`adr/v2-does-not-import.md`)."""
    assert SPELLED_BEFORE_THE_RENAME == frozenset()


def test_the_walk_reaches_the_modules_that_exist() -> None:
    """A checker over a tree it never opened cannot be told from a green one."""
    walked = {path.relative_to(SRC).as_posix() for path in SRC.rglob("*.py")}
    assert "core/tool_base.py" in walked
    assert "core/types.py" in walked


def test_the_walk_sees_a_spelling_in_code_and_in_a_comment(tmp_path: Path) -> None:
    planted = tmp_path / "planted.py"
    planted.write_text(
        'FILTER_ID = "crop"\n# a merging filter\nclass FilterSpec: ...\n', encoding="utf-8"
    )

    assert list(_hits([planted], tmp_path)) == [
        ("planted.py", "filter", 1),
        ("planted.py", "filter", 2),
        ("planted.py", "filter", 3),
    ]


def test_the_adr_slug_is_a_name_and_not_a_spelling(tmp_path: Path) -> None:
    """The rename has to be citable in the code it renamed."""
    citing = tmp_path / "citing.py"
    citing.write_text("#: the field renamed (`adr/tools-not-filters.md`)\n", encoding="utf-8")

    assert list(_hits([citing], tmp_path)) == []


def test_a_frozen_identity_value_is_not_a_dead_word(tmp_path: Path) -> None:
    """ADR-1 froze the values; a gate that scanned for them would refuse them."""
    values = tmp_path / "values.py"
    values.write_text('IDS = ("crop", "detect", "block_signal")\n', encoding="utf-8")

    assert list(_hits([values], tmp_path)) == []
