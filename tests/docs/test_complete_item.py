"""The one-call completion writes a finished entry, or refuses to look like one.

`tools/complete_item.py` grew `--new`/`--summary`/`--settled` because the two
fields it scaffolds with markers were being filled by opening a neighbouring
entry and imitating it. The risk in filling them from arguments is that the
marker is the whole enforcement behind `settled:` being answered at all — so
the load-bearing test here is not that the flags work, it is that omitting
`--settled` still leaves the marker `tests/docs/test_todo_hygiene.py` fails on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import complete_item
from doc_index import SPECS, Entry, IndexSpec, collect, render, settled_rows


@pytest.fixture
def docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A docs tree the tool writes into, with the real one left alone."""
    for directory in ("todo", "completed-todo", "findings"):
        (tmp_path / directory).mkdir()
    monkeypatch.setattr(complete_item, "COMPLETED", tmp_path / "completed-todo")
    monkeypatch.setattr(complete_item, "TODO_DIR", tmp_path / "todo")
    return tmp_path


def _spec() -> IndexSpec:
    return next(spec for spec in SPECS if spec.directory == "completed-todo")


def _only_entry(docs: Path) -> Entry:
    """The single entry in the fixture tree, parsed as the generators parse it.

    `collect` raises `FrontmatterError` naming any required key the render
    forgot or malformed, so calling it is most of the assertion.
    """
    entries = collect(_spec(), docs)
    assert len(entries) == 1, [entry.path.name for entry in entries]
    return entries[0]


def test_one_call_writes_an_entry_every_generator_accepts(docs: Path) -> None:
    # End to end on the path the work loop now takes for unplanned work: no
    # item file, no editor, and an entry that is finished when the call
    # returns. The last run minted an item at t=331s and completed it at
    # t=348s; what those seventeen seconds bought was a file that never
    # reached a commit.
    assert (
        complete_item.main(
            [
                "the-one-call-path",
                "--new",
                "--title",
                "The one-call path",
                "--summary",
                "complete_item.py fills summary and settled from arguments.",
                "--settled",
                "The one-call completion|`tools/complete_item.py`|"
                "An omitted --settled writes the marker rather than `none`.",
            ]
        )
        == 0
    )

    entry = _only_entry(docs)
    text = entry.path.read_text(encoding="utf-8")
    assert "TODO —" not in text, "the one-call path left a marker the gate fails on"
    assert entry.fields["title"] == "The one-call path"
    assert settled_rows(entry) == [
        {
            "what": "The one-call completion",
            "where": "`tools/complete_item.py`",
            "do_not_redecide": "An omitted --settled writes the marker rather than `none`.",
        }
    ]
    assert "The one-call path" in render(_spec(), [entry])


def test_an_unanswered_settled_still_fails_the_gate(docs: Path) -> None:
    # The one that matters. `--summary` given and `--settled` not is the shape
    # a hurried call takes, and if the marker went missing with it the entry
    # would render into SETTLED.md as having nothing to say — which is not
    # what an unanswered question means (rule 6).
    assert (
        complete_item.main(
            ["half-answered", "--new", "--summary", "Half of the frontmatter is filled."]
        )
        == 0
    )
    text = _only_entry(docs).path.read_text(encoding="utf-8")
    assert "TODO —" in text.split("settled:", 1)[1]
    assert "TODO —" not in text.split("settled:", 1)[0], "the summary marker survived --summary"


def test_settled_none_is_an_answer_and_not_a_marker(docs: Path) -> None:
    # `none` is the common case and is a real answer; it has to be reachable
    # from the flag, or the flag is only usable on the rarer half of entries.
    assert complete_item.main(["nothing-settled", "--new", "--settled", "none"]) == 0
    entry = _only_entry(docs)
    assert settled_rows(entry) == []
    assert "TODO —" in entry.path.read_text(encoding="utf-8"), "summary was not asked for"


def test_new_refuses_a_slug_that_has_an_item(docs: Path) -> None:
    # `--new` asserts something about the tree, so it has to be checked
    # against the tree. A typo'd slug used to scaffold a second entry beside
    # the untouched item, and both files then looked deliberate.
    (docs / "todo" / "already-open.md").write_text("---\ntitle: Already open\n---\n", "utf-8")
    assert complete_item.main(["already-open", "--new"]) == 1
    assert (docs / "todo" / "already-open.md").exists()
    assert not list((docs / "completed-todo").glob("*.md"))


def test_a_missing_item_without_new_is_refused(docs: Path) -> None:
    assert complete_item.main(["never-existed"]) == 1
    assert not list((docs / "completed-todo").glob("*.md"))


def test_the_moved_item_is_not_listed_as_a_file_this_entry_added(docs: Path) -> None:
    # git status is read before the item file is deleted, so the item minted
    # in the same session landed in `files.added` as a path that never reached
    # a commit — `2026.08.05-the-gate-ends-with-a-verdict.md` claims one.
    item = docs / "todo" / "moved-not-added.md"
    item.write_text("---\ntitle: Moved not added\n---\n", encoding="utf-8")
    added, _, _ = complete_item.changed_files(docs / "completed-todo" / "x.md", item)
    assert not [path for path in added if path.endswith("moved-not-added.md")]


@pytest.mark.parametrize(
    "value", ["what|where", "what|where|why|extra", "|where|why", "what|where|"]
)
def test_a_malformed_settled_row_is_refused_rather_than_padded(value: str) -> None:
    # Three columns or none of them. A row short a column renders as a blank
    # cell in SETTLED.md, which reads as "nothing to know here".
    with pytest.raises(ValueError):
        complete_item.parse_settled([value])


def test_none_cannot_be_combined_with_a_row() -> None:
    with pytest.raises(ValueError):
        complete_item.parse_settled(["none", "what|where|why"])


def test_an_unanswered_settled_is_not_the_same_object_as_none() -> None:
    # The distinction the render depends on, asserted where it is decided.
    assert complete_item.parse_settled([]) is None
    assert complete_item.parse_settled(["none"]) == []
