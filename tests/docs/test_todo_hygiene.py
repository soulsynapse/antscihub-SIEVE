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

from datetime import datetime
from pathlib import Path

from doc_index import (
    DOCS_ROOT,
    PRIORITIES,
    SETTLED_KEYS,
    SKIP_PREFIXES,
    SPECS,
    STATUSES,
    ItemGraph,
    build_graph,
    collect,
    overturns_list,
    render_state,
    settled_rows,
    superseded_by_slugs,
)


def test_every_completed_entry_answers_what_it_settled() -> None:
    # `required` already fails a missing key; this fails a *malformed* one,
    # which is the shape that would render as a blank cell in SETTLED.md and
    # read as "nothing to know here" (rule 6).
    spec = next(spec for spec in SPECS if spec.directory == "completed-todo")
    for entry in collect(spec):
        rows = settled_rows(entry)
        for row in rows:
            assert set(row) == set(SETTLED_KEYS), f"{entry.path}: {row}"


def test_a_settled_row_points_at_something_that_exists() -> None:
    # `where` is the column a reader follows. A row naming a module that moved
    # is worse than no row: it costs a search and then still has to be
    # re-derived.
    spec = next(spec for spec in SPECS if spec.directory == "completed-todo")
    missing: list[str] = []
    for entry in collect(spec):
        for row in settled_rows(entry):
            for token in row["where"].split("`"):
                looks_like_a_path = "/" in token and token.endswith((".py", ".md", ".toml", "/"))
                if looks_like_a_path and not (DOCS_ROOT.parent / token).exists():
                    missing.append(f"{entry.path.name}: {token}")
    assert not missing, "`settled` rows naming paths that do not exist: " + ", ".join(missing)


def test_every_item_status_is_in_the_vocabulary() -> None:
    # `.state.md` splits on exactly these values; another spelling
    # ("blocked", "Open") would silently vanish from every list.
    spec = next(spec for spec in SPECS if spec.directory == "todo")
    bad = [
        (entry.path.name, entry.fields.get("status"))
        for entry in collect(spec)
        if entry.fields.get("status") not in STATUSES
    ]
    assert not bad, f"item status must be one of {STATUSES}: {bad}"


def test_every_superseded_item_names_a_live_successor() -> None:
    # A superseded item with no successor, or one whose successor is itself
    # superseded, is scope that quietly left the tree — the exact silent
    # vanishing the status exists to prevent.
    graph = _graph()
    spec = next(spec for spec in SPECS if spec.directory == "todo")
    problems: list[str] = []
    for entry in collect(spec):
        if entry.fields.get("status") != "superseded":
            continue
        successors = superseded_by_slugs(entry)
        if not successors:
            problems.append(f"{entry.path.name}: no superseded_by")
        for slug in successors:
            target = graph.nodes.get(slug)
            if target is None:
                problems.append(f"{entry.path.name}: superseded_by names no item ({slug})")
            elif target.fields.get("status") == "superseded":
                problems.append(f"{entry.path.name}: successor {slug} is itself superseded")
    assert not problems, "; ".join(problems)


def test_every_overturned_row_was_a_settled_row() -> None:
    # `overturns:` matches on a settled row's `what`, exact. A typo here would
    # leave the old row standing as law while the entry believes it re-decided
    # it — both tables lying in opposite directions.
    spec = next(spec for spec in SPECS if spec.directory == "completed-todo")
    completed = collect(spec)
    whats = {row["what"] for entry in completed for row in settled_rows(entry)}
    missing = [
        f"{entry.path.name}: {what!r}"
        for entry in completed
        for what in overturns_list(entry)
        if what not in whats
    ]
    assert not missing, "overturns naming no settled row: " + "; ".join(missing)


def test_every_item_priority_is_in_the_vocabulary() -> None:
    # An off-vocabulary value ("urgent", "High", "P1") sorts to the bottom
    # beside the unranked, which is the opposite of what whoever typed it
    # meant — a high-priority item made invisible by a spelling.
    spec = next(spec for spec in SPECS if spec.directory == "todo")
    bad = [
        (entry.path.name, entry.fields.get("priority"))
        for entry in collect(spec)
        if entry.fields.get("priority") not in PRIORITIES
    ]
    assert not bad, f"item priority must be one of {PRIORITIES}: {bad}"


#: Filenames chosen so that priority order matches neither alphabetical order
#: nor its reverse. Written against the live folder, the same assertion passed
#: with the sort deleted: the one ranked item happened to sort last by name,
#: and `collect` reverses. A fixture that can only pass one way is the whole
#: point of this test, so it is built rather than borrowed.
_ORDERING_FIXTURE = (("a-item", "normal"), ("m-item", "high"), ("z-item", "low"))


def test_the_primer_orders_open_items_by_priority(tmp_path: Path) -> None:
    # The failure this catches is a field that exists and does nothing: the
    # key required, the column rendered, and the lists still in filename
    # order, so ranking an item changes a cell and moves nothing.
    for directory in ("todo", "completed-todo", "findings"):
        (tmp_path / directory).mkdir()
    for name, priority in _ORDERING_FIXTURE:
        (tmp_path / "todo" / f"{name}.md").write_text(
            f"---\ntitle: {name}\nstatus: open\npriority: {priority}\n"
            # Identical stamps on purpose: this test is about `priority`, and
            # an `opened` that varied would let the tiebreak pass it.
            f"opened: 2026-07-29T09:00:00-07:00\ngated_on: nothing\n---\n",
            encoding="utf-8",
        )

    section = render_state(tmp_path).split("**Open items", 1)[1].split("**Deferred", 1)[0]
    listed = [name for name, _ in _ORDERING_FIXTURE if f"todo/{name}.md" in section]
    assert len(listed) == len(_ORDERING_FIXTURE), f"the primer dropped an item: {listed}"

    # Position, not format: this must keep working when the bullet is restyled.
    at = [section.index(f"todo/{name}.md") for name in ("m-item", "a-item", "z-item")]
    assert at == sorted(at), "the primer's open items are not in priority order"


def test_the_template_offers_every_priority() -> None:
    # The template's comment block is prose asserting the vocabulary. Adding a
    # value to PRIORITIES and not to the form people fill in leaves the form
    # quietly wrong, which is how the value goes unused.
    text = (DOCS_ROOT / "todo" / "_TEMPLATE.md").read_text(encoding="utf-8")
    assert [p for p in PRIORITIES if p not in text] == []


def _graph() -> ItemGraph:
    by_dir = {spec.directory: spec for spec in SPECS}
    return build_graph(
        collect(by_dir["todo"]),
        collect(by_dir["completed-todo"]),
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


def test_every_completed_entry_says_when_it_landed_to_the_minute() -> None:
    # A day-precision `date:` is not a wrong fact, it is a missing one: 90
    # entries fell in five days, so the day fixed only 87% of the pair order
    # and the remaining 13% went to the filename. Measured 2026-08-04 against
    # the commits: within a day, 51-58% of pairs were backwards — a coin flip.
    spec = next(spec for spec in SPECS if spec.directory == "completed-todo")
    dayonly = [
        entry.path.name
        for entry in collect(spec)
        if not isinstance(entry.fields.get("date"), datetime)
    ]
    assert not dayonly, (
        "completed entries dated to the day, so their order inside it is the "
        "filename: " + ", ".join(dayonly)
    )


def test_every_item_says_when_it_was_minted_to_the_minute() -> None:
    # Same defect on the other side: `opened` is the tiebreak inside a
    # priority band, and 24 of 50 items were minted on one day.
    spec = next(spec for spec in SPECS if spec.directory == "todo")
    dayonly = [
        entry.path.name
        for entry in collect(spec)
        if not isinstance(entry.fields.get("opened"), datetime)
    ]
    assert not dayonly, (
        "items opened to the day, so their order inside it is the filename — "
        "mint with tools/new_item.py: " + ", ".join(dayonly)
    )


def test_no_commit_hash_is_read_as_a_number() -> None:
    # `commit: 0707005` is a valid YAML *integer* in octal, and the index
    # rendered it as 232965 — a commit that does not exist — for six days,
    # past a byte-exact `--check` that only ever compared the generator to
    # itself. Quoting is the fix; this is the check that it stays quoted.
    offenders: list[str] = []
    for directory in ("completed-todo", "findings"):
        spec = next(spec for spec in SPECS if spec.directory == directory)
        for entry in collect(spec):
            value = entry.fields.get("commit")
            if value is not None and not isinstance(value, str):
                offenders.append(f"{entry.path.name}: {value!r}")
    assert not offenders, "unquoted `commit:` values parsed as numbers: " + ", ".join(offenders)
