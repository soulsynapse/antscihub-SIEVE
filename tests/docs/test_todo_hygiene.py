"""The item folder and the completed-todo folder stay honest.

`tools/complete_item.py` scaffolds entries with `TODO —` markers; an entry
that still carries one was filed, not finished, and must not sit in an index
looking done (rule 6). That marker is also the whole enforcement behind
`settled:` — the key is required, `none` is a legal answer, and the scaffold
makes answering it the step rather than an optional extra in another file.
The hand-written table this replaced grew 20 -> 26 rows in one afternoon and
then took twelve commits of real building without gaining a single row.
"""

from __future__ import annotations

from pathlib import Path

from doc_index import (
    DOCS_ROOT,
    SETTLED_KEYS,
    SKIP_PREFIXES,
    SPECS,
    ItemGraph,
    build_graph,
    collect,
    settled_rows,
)


def test_every_completed_entry_answers_what_it_settled() -> None:
    # `required` already fails a missing key; this fails a *malformed* one,
    # which is the shape that would render as a blank cell in SETTLED.md and
    # read as "nothing to know here" (rule 6).
    spec = next(spec for spec in SPECS if spec.directory == "completed-todo")
    for entry in collect(DOCS_ROOT / "completed-todo", spec.required):
        rows = settled_rows(entry)
        for row in rows:
            assert set(row) == set(SETTLED_KEYS), f"{entry.path}: {row}"


def test_a_settled_row_points_at_something_that_exists() -> None:
    # `where` is the column a reader follows. A row naming a module that moved
    # is worse than no row: it costs a search and then still has to be
    # re-derived.
    spec = next(spec for spec in SPECS if spec.directory == "completed-todo")
    missing: list[str] = []
    for entry in collect(DOCS_ROOT / "completed-todo", spec.required):
        for row in settled_rows(entry):
            for token in row["where"].split("`"):
                looks_like_a_path = "/" in token and token.endswith((".py", ".md", ".toml", "/"))
                if looks_like_a_path and not (DOCS_ROOT.parent / token).exists():
                    missing.append(f"{entry.path.name}: {token}")
    assert not missing, "`settled` rows naming paths that do not exist: " + ", ".join(missing)


def test_every_item_status_is_in_the_vocabulary() -> None:
    # `.state.md` splits on exactly these two values; a third spelling
    # ("blocked", "Open") would silently vanish from both lists.
    spec = next(spec for spec in SPECS if spec.directory == "todo")
    bad = [
        (entry.path.name, entry.fields.get("status"))
        for entry in collect(DOCS_ROOT / "todo", spec.required)
        if entry.fields.get("status") not in ("open", "deferred")
    ]
    assert not bad, f"item status must be open or deferred: {bad}"


def _graph() -> ItemGraph:
    by_dir = {spec.directory: spec for spec in SPECS}
    return build_graph(
        collect(DOCS_ROOT / "todo", by_dir["todo"].required),
        collect(DOCS_ROOT / "completed-todo", by_dir["completed-todo"].required),
    )


def test_every_after_slug_resolves_to_an_item() -> None:
    # The failure this replaces: an edge written as a sentence points only the
    # way the sentence runs, and a rename breaks it with no trace. A slug
    # survives completion (`completed-todo/YYYY.MM.DD-<slug>.md`), so an edge
    # into finished work resolves rather than dangling.
    unresolved = _graph().unresolved()
    assert not unresolved, "`after:` slugs naming no item file: " + ", ".join(
        f"{item} -> {target}" for item, target in unresolved
    )


def test_the_item_graph_has_no_cycle() -> None:
    # Two items each claiming to come first. Nothing else in the tree would
    # notice; it would read as an ordering.
    cycles = _graph().cycles()
    assert not cycles, "cyclic `after:` edges: " + "; ".join(" -> ".join(c) for c in cycles)


def test_no_completed_entry_still_carries_a_scaffold_marker() -> None:
    offenders: list[Path] = []
    for path in (DOCS_ROOT / "completed-todo").glob("*.md"):
        if path.name.startswith(SKIP_PREFIXES):
            continue
        if "TODO —" in path.read_text(encoding="utf-8"):
            offenders.append(path)
    assert not offenders, (
        "entries still carrying complete_item.py's 'TODO —' markers: "
        + ", ".join(p.name for p in offenders)
    )
