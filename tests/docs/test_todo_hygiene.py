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

import re
from datetime import datetime
from pathlib import Path

import pytest

import new_item
from doc_index import (
    DOCS_ROOT,
    PRIORITIES,
    SETTLED_KEYS,
    SKIP_PREFIXES,
    SPECS,
    STATUSES,
    IndexSpec,
    ItemGraph,
    build_graph,
    collect,
    overturns_list,
    render,
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


#: A key line in a frontmatter block, either live at column 0 or commented out
#: because the field is optional. Both count as *offered*: an optional key is
#: only discoverable if it is on the form the author fills in, which is why
#: `new_item.BODY` comments them out rather than leaving them off.
_LIVE_KEY = re.compile(r"^([a-z_]+):", re.MULTILINE)
_COMMENTED_KEY = re.compile(r"^[ \t]*#[ \t]*([a-z_]+):", re.MULTILINE)

#: Written when an item is superseded, never when one is minted, so the
#: scaffold does not offer it and `_TEMPLATE.md` documents it where the
#: decision is actually made: the comment on `status`.
_WRITTEN_AFTER_MINTING = frozenset({"superseded_by"})


#: The fence, as a whole line. Splitting on the bare string instead finds the
#: `# ---- identity ----` rule inside `_TEMPLATE.md`'s own frontmatter and
#: returns an empty block — which reads as "offers no keys" and would pass the
#: agreement test below in the one case it exists to catch.
_FENCE = re.compile(r"^---[ \t]*$", re.MULTILINE)


def _offered_keys(text: str) -> set[str]:
    """Frontmatter keys a scaffold offers, live or commented out."""
    block = _FENCE.split(text, maxsplit=2)[1]
    return set(_LIVE_KEY.findall(block)) | set(_COMMENTED_KEY.findall(block))


def _todo_spec() -> IndexSpec:
    return next(spec for spec in SPECS if spec.directory == "todo")


def test_a_minted_item_survives_every_generator_with_no_hand_editing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Minting is the only supported way to make an item, so what the tool
    # writes has to satisfy `collect`'s required tuple and render through both
    # consumers untouched. Nothing checked that: the scaffold and the template
    # were separate texts, and only the template was ever asserted against
    # anything (`test_the_template_offers_every_priority`, alone).
    for directory in ("todo", "completed-todo", "findings"):
        (tmp_path / directory).mkdir()
    monkeypatch.setattr(new_item, "TODO_DIR", tmp_path / "todo")
    assert new_item.main(["a-minted-item", "--title", "A minted item"]) == 0

    spec = _todo_spec()
    # Raises FrontmatterError naming any required key the scaffold forgot.
    entries = collect(spec, tmp_path)
    assert [entry.path.name for entry in entries] == ["a-minted-item.md"]
    assert "A minted item" in render(spec, entries)
    assert "todo/a-minted-item.md" in render_state(tmp_path)


def test_a_minted_item_is_valid_at_every_status_and_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The flags are the part of the form the tool fills in rather than the
    # author, so an off-vocabulary default would be minted rather than typed —
    # invisible to the two vocabulary tests above, which only ever see what
    # already got written.
    for directory in ("todo", "completed-todo", "findings"):
        (tmp_path / directory).mkdir()
    monkeypatch.setattr(new_item, "TODO_DIR", tmp_path / "todo")
    minted = [(status, priority) for status in ("open", "deferred") for priority in PRIORITIES]
    for index, (status, priority) in enumerate(minted):
        assert new_item.main([f"item-{index}", "--status", status, "--priority", priority]) == 0

    entries = collect(_todo_spec(), tmp_path)
    assert len(entries) == len(minted)
    assert {entry.fields["status"] for entry in entries} == {"open", "deferred"}
    assert {entry.fields["priority"] for entry in entries} == set(PRIORITIES)


def test_the_scaffold_and_the_template_offer_the_same_keys() -> None:
    # `_TEMPLATE.md` annotates the scaffold; it is not a second thing to copy.
    # While it was both, they disagreed for exactly as long as nothing compared
    # them: the tool emitted two body headings that 0 of 49 items carried, and
    # omitted `reads`, which 49 of 49 did.
    scaffold = _offered_keys(new_item.BODY)
    template = _offered_keys((DOCS_ROOT / "todo" / "_TEMPLATE.md").read_text(encoding="utf-8"))
    assert scaffold == template, (
        f"only in tools/new_item.py: {sorted(scaffold - template)}; "
        f"only in _TEMPLATE.md: {sorted(template - scaffold)}"
    )


def test_every_key_the_live_items_use_is_one_the_scaffold_offers() -> None:
    # The drift check in the direction that actually happened. A key invented
    # in one item and then read by a generator is invisible to the next author,
    # who fills in the form and never sees the question — which is how `after:`
    # (25 items, cycle-checked) and `serves:` (10 items, grouping the primer's
    # aspiration block) came to be named in neither scaffold nor template.
    used = {key for entry in collect(_todo_spec()) for key in entry.fields}
    undocumented = used - _WRITTEN_AFTER_MINTING - _offered_keys(new_item.BODY)
    assert not undocumented, (
        "item frontmatter keys the scaffold never offers, so nobody minting an "
        "item learns they exist: " + ", ".join(sorted(undocumented))
    )
