"""The generated `.index.md` files must match the entries they describe.

A derived summary that is allowed to drift is worse than no summary: readers
trust it and it lies. So the same check that regenerates the indexes runs here
in `--check` mode, and a missing frontmatter field fails the suite rather than
producing a blank table cell nobody notices.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from doc_index import (
    DOCS_ROOT,
    SPECS,
    Entry,
    FrontmatterError,
    build,
    item_order,
    parse_frontmatter,
    render,
)


class TestGeneratedIndexesAreCurrent:
    """The committed indexes agree with the files in their folders."""

    def test_every_index_matches_its_folder(self) -> None:
        for path, expected in build():
            assert path.exists(), f"{path} has never been generated — run `uv run nox -s docs`"
            assert path.read_text(encoding="utf-8") == expected, (
                f"{path} is stale — run `uv run nox -s docs`"
            )

    def test_every_entry_parses_and_carries_its_required_fields(self) -> None:
        # `build` raises on a malformed or incomplete entry. Calling it is the
        # assertion; the loop exists so a failure names the folder.
        for spec in SPECS:
            assert (DOCS_ROOT / spec.directory).is_dir()
        list(build())

    def test_templates_are_excluded_from_the_tables(self) -> None:
        # The empty-folder guidance names `_TEMPLATE.md` in prose, so the check
        # is for a *link* to it — that is what would mean it got indexed.
        for path, content in build():
            assert "(_TEMPLATE.md)" not in content, f"{path} indexed its own template"


class TestPriorityOrdering:
    """`priority` ranks items, and an unrecognised value does not jump the queue."""

    def _item(self, name: str, priority: object) -> Entry:
        return Entry(path=Path(name), fields={"title": name, "priority": priority})

    def test_items_sort_in_vocabulary_order_then_by_filename(self) -> None:
        entries = [
            self._item("z.md", "high"),
            self._item("a.md", "low"),
            self._item("b.md", "high"),
            self._item("c.md", "normal"),
        ]
        assert [e.path.name for e in item_order(entries)] == ["b.md", "z.md", "c.md", "a.md"]

    def test_an_unrecognised_priority_sorts_last_rather_than_first(self) -> None:
        # `P1` is what somebody types who means *most urgent*. Ranking it as
        # written would put an untriaged typo at the top of the frontier —
        # rule 6, at the one place a session reads to choose what to do.
        # The gate rejects it; until the gate runs, it sits with `unassessed`.
        entries = [self._item("typo.md", "P1"), self._item("real.md", "low")]
        assert [e.path.name for e in item_order(entries)] == ["real.md", "typo.md"]

    def test_takeable_work_leads_its_priority_band(self) -> None:
        # Only the index table interleaves the two statuses; the primer splits
        # on status first. Without this, a `high` item nobody can start yet
        # heads the table over a `high` item somebody can.
        waiting = Entry(path=Path("a.md"), fields={"priority": "high", "status": "deferred"})
        takeable = Entry(path=Path("z.md"), fields={"priority": "high", "status": "open"})
        assert [e.path.name for e in item_order([waiting, takeable])] == ["z.md", "a.md"]


class TestFrontmatterParsing:
    """Malformed entries fail loudly rather than producing empty cells."""

    def test_reads_a_well_formed_block(self, tmp_path: Path) -> None:
        path = tmp_path / "2026.07.25-thing.md"
        path.write_text("---\ntitle: Thing\ndate: 2026-07-25\n---\n\nBody.\n", encoding="utf-8")
        assert parse_frontmatter(path) == {"title": "Thing", "date": date(2026, 7, 25)}

    def test_an_unquoted_date_arrives_as_a_date_object(self, tmp_path: Path) -> None:
        """YAML resolves `2026-07-25` to `datetime.date`, not to a string.

        Both the sort key and the table cell go through `str()` for exactly
        this reason. ISO-8601 is what `str(date)` produces, so lexicographic
        sorting stays chronological — but only because the format is ISO. A
        quoted `"July 25"` would render and sort as written, which is the
        argument for keeping the field unquoted.
        """
        path = tmp_path / "2026.07.25-typed.md"
        path.write_text("---\ntitle: T\ndate: 2026-07-25\n---\n", encoding="utf-8")
        parsed = parse_frontmatter(path)["date"]
        assert isinstance(parsed, date)
        assert str(parsed) == "2026-07-25"

    def test_an_empty_block_is_a_mapping_with_nothing_in_it(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.md"
        path.write_text("---\n---\nBody.\n", encoding="utf-8")
        assert parse_frontmatter(path) == {}

    def test_a_missing_block_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bare.md"
        path.write_text("# Just a heading\n", encoding="utf-8")
        with pytest.raises(FrontmatterError, match="no frontmatter"):
            parse_frontmatter(path)

    def test_an_unclosed_block_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "unclosed.md"
        path.write_text("---\ntitle: Thing\n\nBody with no closing rule.\n", encoding="utf-8")
        with pytest.raises(FrontmatterError, match="never closed"):
            parse_frontmatter(path)

    def test_a_non_mapping_block_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "list.md"
        path.write_text("---\n- one\n- two\n---\n", encoding="utf-8")
        with pytest.raises(FrontmatterError, match="must be a mapping"):
            parse_frontmatter(path)


class TestRendering:
    """Table construction survives the values frontmatter actually contains."""

    def _entry(self, name: str, **fields: object) -> Entry:
        return Entry(path=Path(name), fields=dict(fields))

    def test_folded_summaries_do_not_break_the_table(self) -> None:
        spec = next(spec for spec in SPECS if spec.directory == "findings")
        entry = self._entry(
            "2026.07.25-seek.md",
            date="2026-07-25",
            title="Seek",
            status="closed",
            verdict="One line\nfolded across\ntwo more",
        )
        row = render(spec, [entry]).splitlines()[-3]
        assert "One line folded across two more" in row
        assert row.count("|") == len(spec.columns) + 1

    def test_pipes_in_a_value_are_escaped(self) -> None:
        spec = next(spec for spec in SPECS if spec.directory == "findings")
        entry = self._entry(
            "2026.07.25-pipe.md",
            date="2026-07-25",
            title="Pipe",
            status="open",
            verdict="a | b",
        )
        row = render(spec, [entry]).splitlines()[-3]
        assert r"a \| b" in row
        # Only the escaped pipe should survive inside a cell; the unescaped
        # ones are the column separators and must still number columns + 1.
        assert row.replace(r"\|", "").count("|") == len(spec.columns) + 1

    def test_lists_flatten_and_the_title_links_to_the_file(self) -> None:
        spec = next(spec for spec in SPECS if spec.directory == "completed-todo")
        entry = self._entry(
            "2026.07.25-work.md",
            date="2026-07-25",
            title="Work",
            commit=["e09b8bf", "4b2431a"],
            summary="Did the thing.",
        )
        row = render(spec, [entry]).splitlines()[-3]
        assert "[Work](2026.07.25-work.md)" in row
        assert "e09b8bf, 4b2431a" in row

    def test_newest_entry_comes_first(self) -> None:
        spec = next(spec for spec in SPECS if spec.directory == "findings")
        older = self._entry("a.md", date="2026-01-01", title="Older", status="closed", verdict="x")
        newer = self._entry("b.md", date="2026-07-25", title="Newer", status="closed", verdict="y")
        sorted_entries = sorted([older, newer], key=lambda e: e.sort_key, reverse=True)
        body = render(spec, sorted_entries)
        assert body.index("Newer") < body.index("Older")

    def test_an_empty_folder_renders_guidance_rather_than_a_headerless_table(self) -> None:
        spec = next(spec for spec in SPECS if spec.directory == "findings")
        body = render(spec, [])
        assert "No entries yet" in body
        assert "|" not in body
