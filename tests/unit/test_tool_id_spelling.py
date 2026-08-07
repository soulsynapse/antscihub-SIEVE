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

`SPEAKS_A_FOREIGN_VOCABULARY` is the other claim and deliberately not that
list. `filter`, `roi`, and `clip` are FFmpeg's, every imaging library's, and
English's words as much as they were v2's, and `decode/` exists to talk to
FFmpeg, so a line there can carry a dead spelling while saying nothing v2 said.
Two granularities, because one does not reach: a spelling an outside tool owns
whole (`-filter_threads`, `filtergraph`) is a token and belongs in the row,
where it stays invisible to every other line in the file; a module whose
*subject* is the foreign sense (`quiet.py` filters a byte stream, and no
lexical rule tells that `filter` from `reader.py`'s) can only be declared by
module. Module granularity is the coarse one and 03.2.1 is why it is not the
only one: `lowered.py` held FFmpeg's `filtergraph` and v2's `filter_id` at
once, and a module-wide waiver would have hidden the second while excusing the
first.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import Path

import pytest

import sieve

SRC = Path(str(sieve.__file__)).resolve().parent

#: `(the dead word, the live spellings that contain it, the verdict)`. The ADR
#: slug is the rename naming itself; every other occurrence of the word is the
#: rename unfinished. Grows a row per buried word.
#:
#: The live column is a tuple because one slot cannot hold both an ADR slug and
#: an FFmpeg flag — which is the shape 03.2.1 was opened to pick, though not
#: from the collision that was predicted for it.
#:
#: The `adr/v2-does-not-import.md` rows are the three `Project`/`Replicate`
#: fields ADR-3 turned into graph nodes, read off v2's `pipeline_model.py` at
#: `main`. Two of them bury a whole word; the third cannot, because `detector`
#: is *alive* — ADR-3 names the detector a node, `mutual/shares.py` budgets one,
#: and Phase 4 builds one — so what is buried is the pair of spellings only v2's
#: document has, its settings type and its per-replicate deviation map. A name
#: schema v1 keeps because it is the right name gets no row: this is a gate on
#: names v3 would inherit without deciding to, not a vocabulary ban.
#:
#: `DetectorSettings`' own field names are deliberately absent. The detect tool
#: is Phase 4 and owns its parameter names; a row here would settle that naming
#: now, in a spelling test, for a tool nobody has designed.
DEAD_IDENTIFIERS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    # `-filter_threads` and `-filter_complex_threads` are FFmpeg's CLI, and a
    # filtergraph is what `-vf` takes; none of the three is a step in a SIEVE
    # pipeline, and all three would survive a word-boundary match anyway.
    (
        "filter",
        ("tools-not-filters", "filter_complex_threads", "filter_threads", "filtergraph"),
        "adr/tools-not-filters.md",
    ),
    ("clip", (), "adr/v2-does-not-import.md"),
    # `ROI` is the live type a region is written in; `roi` was the field name,
    # and `region` is how v3 spells the thing (`CropRecord.region`).
    ("roi", ("ROI",), "adr/v2-does-not-import.md"),
    ("DetectorSettings", (), "adr/v2-does-not-import.md"),
    ("detector_overrides", (), "adr/v2-does-not-import.md"),
)

#: `(module relative to src/sieve, dead word)` for a spelling something licenses.
#: Empty, and `test_the_exception_list_is_empty` is what keeps it that way.
SPELLED_BEFORE_THE_RENAME: frozenset[tuple[str, str]] = frozenset()

#: `(module relative to src/sieve, dead word, whose word it is)` for a module
#: whose subject *is* the foreign sense, where no token strip separates the two
#: because the word appears as itself, in prose. Bounded by
#: `test_every_declared_vocabulary_is_still_spoken`: an entry that stops
#: matching is a stale waiver and fails, so the table shrinks with the modules.
SPEAKS_A_FOREIGN_VOCABULARY: frozenset[tuple[str, str, str]] = frozenset(
    {
        (
            "decode/quiet.py",
            "filter",
            "a stderr line filter, down to the pump thread's name",
        ),
        (
            "storage/crop_writer.py",
            "clip",
            "English's noun for a video, in the docs for streaming one through",
        ),
    }
)


def _hits(modules: Iterable[Path], root: Path) -> Iterator[tuple[str, str, int]]:
    """`(module, dead word, line number)` for every dead spelling in `modules`.

    Read as text rather than as an AST: a comment is not a node, and a rename
    that stopped at the identifiers leaves its evidence in the comments.
    """
    for path in sorted(modules):
        relative = path.relative_to(root).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for word, live, _ in DEAD_IDENTIFIERS:
                bare = line
                # Longest first: a shorter live spelling that is a substring of a
                # longer one would eat the longer one's middle and leave the dead
                # word standing in the wreckage.
                for spelling in sorted(live, key=len, reverse=True):
                    bare = bare.replace(spelling, "")
                if re.search(re.escape(word), bare, re.IGNORECASE):
                    yield (relative, word, lineno)


def _undeclared(
    hits: Iterable[tuple[str, str, int]],
    declared: Iterable[tuple[str, str, str]],
) -> list[tuple[str, str, int]]:
    """`hits` minus the ones a module's declared foreign vocabulary accounts for."""
    speaks = {(module, word) for module, word, _ in declared}
    return [
        hit
        for hit in hits
        if (hit[0], hit[1]) not in speaks and (hit[0], hit[1]) not in SPELLED_BEFORE_THE_RENAME
    ]


@pytest.fixture(scope="module")
def spelled() -> list[tuple[str, str, int]]:
    return list(_hits(SRC.rglob("*.py"), SRC))


def test_no_module_spells_a_pre_rename_identifier(
    spelled: list[tuple[str, str, int]],
) -> None:
    verdicts = {word: verdict for word, _, verdict in DEAD_IDENTIFIERS}
    undeclared = _undeclared(spelled, SPEAKS_A_FOREIGN_VOCABULARY)
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


def test_a_v2_field_the_graph_absorbed_is_a_spelling(tmp_path: Path) -> None:
    """The three fields ADR-3 turned into nodes, spelt as v2's document spelt them."""
    ported = tmp_path / "ported.py"
    ported.write_text(
        "clip: ClipRange | None = None\n"
        "roi: ROI\n"
        "detector: DetectorSettings | None = None\n"
        "detector_overrides: dict[str, Any]\n",
        encoding="utf-8",
    )

    assert list(_hits([ported], tmp_path)) == [
        ("ported.py", "clip", 1),
        ("ported.py", "roi", 2),
        ("ported.py", "DetectorSettings", 3),
        ("ported.py", "detector_overrides", 4),
    ]


def test_the_geometry_type_survived_its_field(tmp_path: Path) -> None:
    """`Replicate.roi` is dead and `ROI` is what the live region is typed as."""
    region = tmp_path / "region.py"
    region.write_text("    region: ROI\n    def clamped_to(self) -> ROI: ...\n", encoding="utf-8")

    assert list(_hits([region], tmp_path)) == []


def test_a_row_strips_every_spelling_the_outside_vocabulary_owns(tmp_path: Path) -> None:
    """FFmpeg's flags and its graph are one word each, not the word SIEVE renamed."""
    lowering = tmp_path / "lowering.py"
    lowering.write_text(
        '        "-filter_threads",\n'
        '        "-filter_complex_threads",\n'
        "        prefix.filtergraph,\n",
        encoding="utf-8",
    )

    assert list(_hits([lowering], tmp_path)) == []


def test_a_declared_vocabulary_waives_only_its_own_word_in_its_own_module() -> None:
    """The waiver is a module speaking one foreign word, not a module exempted."""
    declared = frozenset({("decode/quiet.py", "filter", "stderr's word")})
    hits = [
        ("decode/quiet.py", "filter", 27),
        ("decode/quiet.py", "roi", 27),
        ("decode/reader.py", "filter", 135),
    ]

    assert _undeclared(hits, declared) == [
        ("decode/quiet.py", "roi", 27),
        ("decode/reader.py", "filter", 135),
    ]


def test_every_declared_vocabulary_is_still_spoken(
    spelled: list[tuple[str, str, int]],
) -> None:
    """A waiver outlives the line it was written for unless something says so."""
    spoken = {(module, word) for module, word, _ in spelled}
    stale = sorted(
        (module, word)
        for module, word, _ in SPEAKS_A_FOREIGN_VOCABULARY
        if (module, word) not in spoken
    )

    assert stale == []


def test_the_word_detector_is_alive(tmp_path: Path) -> None:
    """ADR-3 made the detector a node; `mutual/` budgets one. The *field* is dead."""
    share = tmp_path / "share.py"
    share.write_text(
        "DETECTOR_WORKERS = 2\n    detector: int\nSENSED = {'detector'}\n", encoding="utf-8"
    )

    assert list(_hits([share], tmp_path)) == []
