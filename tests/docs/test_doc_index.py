"""The item folder stays readable by machine, and the index never drifts.

The vocabulary tests exist because the statuses are a protocol, not labels:
`awaiting-review` is how a worker's claim and a review's verdict stay two
different edits, and a value outside the vocabulary would let an item slip
out of both lists silently.
"""

from pathlib import Path

import doc_index
import pytest
from doc_index import (
    ItemError,
    adr_summary,
    collect,
    collect_adrs,
    collect_findings,
    collect_modules,
    forbidden_present,
    module_annotation,
    next_takeable,
    parse_groups,
    phase_titles,
    render,
    render_architecture,
    render_findings,
    render_scaffold,
)


def write_item(folder: Path, name: str, front: str, body: str = "words") -> Path:
    path = folder / f"{name}.md"
    path.write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")
    return path


SEQUENCED = """title: A step
step: "02.3"
status: open
gated_on: nothing
done_when: "true"
opened: 2026-08-06"""

POOLED = """title: An aside that can wait
priority: normal
status: open
gated_on: nothing
opened: 2026-08-06"""


def test_a_decimal_aside_orders_between_its_neighbours(tmp_path):
    write_item(tmp_path, "third", SEQUENCED)
    write_item(tmp_path, "fourth", SEQUENCED.replace('"02.3"', '"02.4"'))
    write_item(tmp_path, "aside", SEQUENCED.replace('"02.3"', '"02.3.1"'))

    steps = [item.fields["step"] for item in collect(tmp_path)]
    ordered = sorted(collect(tmp_path), key=lambda i: i.step_key or ())

    assert set(steps) == {"02.3", "02.3.1", "02.4"}
    assert [item.fields["step"] for item in ordered] == ["02.3", "02.3.1", "02.4"]


def test_next_is_the_lowest_open_step_and_skips_claims_awaiting_review(tmp_path):
    early = SEQUENCED.replace('"02.3"', '"01.1"').replace("status: open", "status: done")
    write_item(tmp_path, "early", early)
    write_item(tmp_path, "claimed", SEQUENCED.replace("status: open", "status: awaiting-review"))
    write_item(tmp_path, "takeable", SEQUENCED.replace('"02.3"', '"02.4"'))
    write_item(tmp_path, "pooled", POOLED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "takeable.md"


def test_with_every_step_taken_or_done_there_is_nothing_takeable(tmp_path):
    write_item(tmp_path, "done", SEQUENCED.replace("status: open", "status: done"))
    write_item(tmp_path, "pooled", POOLED)

    assert next_takeable(collect(tmp_path)) is None


#: An aside owed by phase 5, against the phase-6 step in SEQUENCED_6: the
#: boundary between them is the only place a pool item is ever served.
OWED = """title: An aside phase 5 owes
priority: normal
phase: 5
status: open
gated_on: nothing
done_when: "true"
opened: 2026-08-07"""

SEQUENCED_6 = SEQUENCED.replace('"02.3"', '"06.3"')


def test_a_phases_pool_is_drained_before_the_next_phase_opens(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "owed", OWED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "owed.md"


def test_the_drain_runs_by_priority_not_by_name(tmp_path):
    # Named against the alphabet on purpose: sorting on the filename alone
    # would put `a-low` first and pass a test that checks nothing.
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "a-low", OWED.replace("priority: normal", "priority: low"))
    write_item(tmp_path, "b-urgent", OWED.replace("priority: normal", "priority: high"))

    order = [i.path.name for i in doc_index.owed_pool(collect(tmp_path), 6)]

    assert order == ["b-urgent.md", "a-low.md"]


def test_an_unattached_item_drains_after_every_phase_that_has_one(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "a-loose", OWED.replace("phase: 5\n", ""))
    write_item(tmp_path, "z-phased", OWED)

    order = [i.path.name for i in doc_index.owed_pool(collect(tmp_path), 6)]

    assert order == ["z-phased.md", "a-loose.md"]


def test_a_low_is_owed_like_anything_else_in_the_pool(tmp_path):
    # The pool is drained, not filtered: a `low` orders last and still runs.
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "cosmetic", OWED.replace("priority: normal", "priority: low"))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "cosmetic.md"


def test_an_owed_item_with_no_criterion_shuts_the_phase(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "vague", OWED.replace('done_when: "true"\n', ""))

    items = collect(tmp_path)

    assert next_takeable(items) is None
    assert doc_index.unspecified(doc_index.owed_pool(items, 6)) == ["vague.md"]


def test_the_specified_half_of_a_drain_runs_before_the_boundary_shuts(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "vague", OWED.replace('done_when: "true"\n', ""))
    write_item(tmp_path, "ready", OWED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "ready.md"


def test_a_phase_under_way_is_not_held_up_retroactively(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    begun = SEQUENCED.replace('"02.3"', '"06.1"').replace("status: open", "status: done")
    write_item(tmp_path, "begun", begun)
    write_item(tmp_path, "owed", OWED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "step.md"


def test_a_claim_awaiting_review_has_started_its_phase(tmp_path):
    # The live case when this rule landed: 06.2 sat at `awaiting-review`, so
    # whether Phase 6 counted as begun decided whether 06.3 ran at all.
    write_item(tmp_path, "step", SEQUENCED_6)
    claimed = SEQUENCED.replace('"02.3"', '"06.2"').replace(
        "status: open", "status: awaiting-review"
    )
    write_item(tmp_path, "claimed", claimed)
    write_item(tmp_path, "owed", OWED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "step.md"


def test_the_pool_of_the_phase_about_to_open_is_not_owed_yet(tmp_path):
    # The boundary is `<`, not `<=`: phase 6's own pool is drained after
    # phase 6's steps, not before the first of them.
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "own", OWED.replace("phase: 5", "phase: 6"))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "step.md"


def test_an_unattached_item_is_owed_at_every_boundary(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "loose", OWED.replace("phase: 5\n", ""))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "loose.md"


def test_with_no_step_left_every_phases_pool_has_come_due(tmp_path):
    # Not "drained": a plan whose next phase has no steps minted yet would
    # otherwise report itself finished with the whole pool outstanding.
    write_item(tmp_path, "done", SEQUENCED_6.replace("status: open", "status: done"))
    write_item(tmp_path, "owed", OWED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "owed.md"


def test_with_no_step_and_an_empty_pool_the_plan_is_drained(tmp_path):
    write_item(tmp_path, "done", SEQUENCED_6.replace("status: open", "status: done"))

    assert next_takeable(collect(tmp_path)) is None


def test_a_pending_review_outranks_every_other_role(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    claimed = SEQUENCED.replace('"02.3"', '"06.2"').replace(
        "status: open", "status: awaiting-review"
    )
    write_item(tmp_path, "claimed", claimed)

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("review", "claimed.md")


def test_reviews_queue_by_step_not_by_filename(tmp_path):
    # Named against the alphabet: ordering on the path would take `a-later`.
    write_item(tmp_path, "step", SEQUENCED_6)
    for name, step in (("a-later", '"06.2"'), ("z-earlier", '"06.1"')):
        front = SEQUENCED.replace('"02.3"', step).replace(
            "status: open", "status: awaiting-review"
        )
        write_item(tmp_path, name, front)

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("review", "z-earlier.md")


def test_takeable_work_is_the_role_when_no_review_is_pending(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("work", "step.md")


def test_a_boundary_shut_for_want_of_criteria_dispatches_a_specify_run(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "vague", OWED.replace('done_when: "true"\n', ""))

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("specify", "vague.md")


def test_specify_yields_to_the_work_it_unblocks(tmp_path):
    # The specified half of a drain runs first, so `specify` fires only when
    # nothing else can move — otherwise it would starve the drain it exists for.
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "vague", OWED.replace('done_when: "true"\n', ""))
    write_item(tmp_path, "ready", OWED)

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("work", "ready.md")


def test_drained_is_the_only_answer_with_no_item(tmp_path):
    write_item(tmp_path, "done", SEQUENCED_6.replace("status: open", "status: done"))

    assert doc_index.next_action(collect(tmp_path)) == ("drained", None)


DEFERRED = """title: An item nothing can clear
priority: normal
phase: 5
status: deferred
deferred_for: decision
gated_on: whether the formatter is in the gate
opened: 2026-08-07"""


def test_a_deferral_is_owed_by_no_boundary(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "parked", DEFERRED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "step.md"


def test_a_deferral_without_a_typed_reason_is_refused(tmp_path):
    write_item(tmp_path, "bad", DEFERRED.replace("deferred_for: decision\n", ""))

    with pytest.raises(ItemError, match="deferred_for"):
        collect(tmp_path)


def test_a_reason_outside_the_vocabulary_is_refused(tmp_path):
    write_item(tmp_path, "bad", DEFERRED.replace("deferred_for: decision", "deferred_for: later"))

    with pytest.raises(ItemError, match="deferred_for"):
        collect(tmp_path)


def test_a_reason_on_an_item_that_is_not_deferred_is_refused(tmp_path):
    # There is no `deferred_for: criterion`, and this is what stops one being
    # smuggled onto an open item to excuse a missing `done_when`.
    write_item(tmp_path, "bad", OWED + "\ndeferred_for: decision")

    with pytest.raises(ItemError, match="not deferred"):
        collect(tmp_path)


def test_the_waiting_section_separates_a_deferral_from_an_unspecified_item(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "parked", DEFERRED)
    write_item(tmp_path, "vague", OWED.replace('done_when: "true"\n', ""))

    deferred, unspecified_items = doc_index.waiting_on_kendrick(collect(tmp_path))

    assert [i.path.name for i in deferred] == ["parked.md"]
    assert [i.path.name for i in unspecified_items] == ["vague.md"]


def test_the_drain_takes_the_earliest_phase_first(tmp_path):
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "later", OWED)
    write_item(tmp_path, "earlier", OWED.replace("phase: 5", "phase: 3"))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "earlier.md"


def test_a_status_outside_the_vocabulary_is_refused(tmp_path):
    write_item(tmp_path, "bad", SEQUENCED.replace("status: open", "status: in-progress"))

    with pytest.raises(ItemError, match="in-progress"):
        collect(tmp_path)


def test_a_sequenced_item_without_a_criterion_is_refused(tmp_path):
    """An item with a number but no `done_when` is work whose completion the
    session doing it would get to define."""
    write_item(tmp_path, "bad", SEQUENCED.replace('done_when: "true"\n', ""))

    with pytest.raises(ItemError, match="done_when"):
        collect(tmp_path)


def test_a_sequenced_item_carrying_a_priority_is_refused(tmp_path):
    write_item(tmp_path, "bad", SEQUENCED + "\npriority: high")

    with pytest.raises(ItemError, match="no `priority`"):
        collect(tmp_path)


def test_a_deferral_with_no_trigger_is_refused(tmp_path):
    write_item(tmp_path, "bad", POOLED.replace("status: open", "status: deferred"))

    with pytest.raises(ItemError, match="not a deferral"):
        collect(tmp_path)


def test_a_pool_item_without_a_priority_is_refused(tmp_path):
    write_item(tmp_path, "bad", POOLED.replace("priority: normal\n", ""))

    with pytest.raises(ItemError, match="priority"):
        collect(tmp_path)


def test_the_template_is_machinery_not_an_entry(tmp_path):
    write_item(tmp_path, "_TEMPLATE", "not: frontmatter the collector should read")

    assert collect(tmp_path) == []


def test_phase_titles_come_from_the_plan(tmp_path):
    plan = tmp_path / "PLAN.md"
    plan.write_text("## Phase 0 — Skeleton and enforcement\n", encoding="utf-8")

    assert phase_titles(plan) == {0: "Skeleton and enforcement"}


def test_the_index_sections_by_phase_and_pools_the_asides(tmp_path):
    write_item(tmp_path, "step", SEQUENCED)
    write_item(tmp_path, "aside", POOLED + "\nphase: 2")

    text = render(collect(tmp_path), {2: "Vertical slice"})

    assert "## Phase 2 — Vertical slice" in text
    assert text.index("A step") < text.index("Asides that can wait")
    assert "An aside that can wait" in text


# Findings.

FINDING = """title: The seek is irreducible
date: 2026-08-05
status: open
verdict: the seek is ~70% of the cost and has no knob"""


def test_findings_index_newest_first(tmp_path):
    write_item(tmp_path, "2026.08.05-seek", FINDING)
    write_item(tmp_path, "2026.08.06-later", FINDING.replace("2026-08-05", "2026-08-06"))

    dates = [str(finding.fields["date"]) for finding in collect_findings(tmp_path)]

    assert dates == ["2026-08-06", "2026-08-05"]


def test_a_finding_without_a_verdict_is_refused(tmp_path):
    """A row with no verdict cannot be triaged from the table, which defeats
    the table."""
    write_item(tmp_path, "2026.08.05-seek", FINDING.replace("verdict: the seek", "note: the seek"))

    with pytest.raises(ItemError, match="verdict"):
        collect_findings(tmp_path)


def test_a_finding_status_outside_the_vocabulary_is_refused(tmp_path):
    write_item(tmp_path, "2026.08.05-seek", FINDING.replace("status: open", "status: pending"))

    with pytest.raises(ItemError, match="pending"):
        collect_findings(tmp_path)


def test_loop_findings_render_as_their_own_section(tmp_path):
    (tmp_path / "loop").mkdir()
    write_item(tmp_path, "2026.08.05-seek", FINDING)
    write_item(tmp_path / "loop", "2026.08.06-vacuity", FINDING.replace("seek is", "test was"))

    text = render_findings(collect_findings(tmp_path), collect_findings(tmp_path / "loop"))

    assert "## Loop" in text
    assert "loop/2026.08.06-vacuity.md" in text
    assert text.index("irreducible") < text.index("## Loop")


def test_a_missing_findings_folder_is_an_empty_list_not_an_error(tmp_path):
    assert collect_findings(tmp_path / "loop") == []


# ADRs: fixed number as identity, position as placement, the body's first
# paragraph as the index line.

ADR = """title: No kernel apparatus
adr: 2
position: "01.02"
status: settled
decided: 2026-08-06"""

GROUPS = {1: "The tool contract"}


def test_the_index_line_is_the_first_paragraph_joined_across_wraps(tmp_path):
    path = write_item(tmp_path, "adr", ADR, body="One plain run per\ntool module.\n\nWhy: prose.")

    assert adr_summary(path) == "One plain run per tool module."


def test_a_superseded_adr_keeps_its_number_but_leaves_the_index(tmp_path):
    write_item(tmp_path, "kernel-registry", ADR + "\nsuperseded_by: no-kernel-apparatus")
    old = tmp_path / "kernel-registry.md"
    old.write_text(
        old.read_text(encoding="utf-8")
        .replace("status: settled", "status: superseded")
        .replace('position: "01.02"\n', ""),
        encoding="utf-8",
    )
    write_item(tmp_path, "no-kernel-apparatus", ADR.replace("adr: 2", "adr: 3"), body="The one.")

    text = render_architecture(collect_adrs(tmp_path, GROUPS), GROUPS)

    assert "no-kernel-apparatus.md" in text
    assert "kernel-registry" not in text
    assert "*1 settled, 1 superseded.*" in text


def test_a_superseded_adr_holding_a_position_is_refused(tmp_path):
    bad = ADR.replace("status: settled", "status: superseded") + "\nsuperseded_by: successor"
    write_item(tmp_path, "successor", ADR.replace("adr: 2", "adr: 3").replace("01.02", "01.03"))
    write_item(tmp_path, "old", bad)

    with pytest.raises(ItemError, match="no `position`"):
        collect_adrs(tmp_path, GROUPS)


def test_a_minted_number_is_never_reused(tmp_path):
    write_item(tmp_path, "first", ADR)
    write_item(tmp_path, "second", ADR.replace("01.02", "01.03"))

    with pytest.raises(ItemError, match="already"):
        collect_adrs(tmp_path, GROUPS)


def test_two_adrs_on_one_shelf_position_are_refused(tmp_path):
    write_item(tmp_path, "first", ADR)
    write_item(tmp_path, "second", ADR.replace("adr: 2", "adr: 3"))

    with pytest.raises(ItemError, match="position 01.02"):
        collect_adrs(tmp_path, GROUPS)


def test_a_position_outside_the_named_groups_is_refused(tmp_path):
    write_item(tmp_path, "adr", ADR.replace("01.02", "09.01"))

    with pytest.raises(ItemError, match="_GROUPS.md"):
        collect_adrs(tmp_path, GROUPS)


def test_each_further_position_pair_indents_one_level(tmp_path):
    write_item(tmp_path, "parent", ADR, body="The parent.")
    write_item(
        tmp_path,
        "child",
        ADR.replace("adr: 2", "adr: 3").replace("01.02", "01.02.01"),
        body="The child.",
    )

    text = render_architecture(collect_adrs(tmp_path, GROUPS), GROUPS)

    assert "\n- [No kernel apparatus](adr/parent.md) — The parent." in text
    assert "\n  - [No kernel apparatus](adr/child.md) — The child." in text


def test_group_titles_come_from_the_groups_file(tmp_path):
    groups = tmp_path / "_GROUPS.md"
    groups.write_text("<!-- prose -->\n01 — The tool contract\n", encoding="utf-8")

    assert parse_groups(groups) == {1: "The tool contract"}


# The scaffold: derived from docstring first lines, with the rules that make
# a first line an annotation.


def test_a_modules_docstring_first_line_becomes_its_scaffold_annotation(tmp_path):
    (tmp_path / "src").mkdir()
    module = tmp_path / "src" / "thing.py"
    module.write_text('"""Owns the one thing.\n\nMore prose.\n"""\n', encoding="utf-8")

    assert collect_modules(tmp_path) == [("src/thing.py", "Owns the one thing.")]


def test_the_scaffold_lists_packages_by_layer_not_by_name(tmp_path):
    """Alphabetical would put `decode` before `tools`; the stack puts what
    imports above what is imported."""
    for package in ("decode", "tools"):
        folder = tmp_path / "src" / "sieve" / package
        folder.mkdir(parents=True)
        (folder / "x.py").write_text('"""Owns the one thing."""\n', encoding="utf-8")

    paths = [path for path, _ in collect_modules(tmp_path)]

    assert paths == ["src/sieve/tools/x.py", "src/sieve/decode/x.py"]


def test_a_package_outside_the_layer_order_is_refused(tmp_path):
    folder = tmp_path / "src" / "sieve" / "surprise"
    folder.mkdir(parents=True)
    (folder / "x.py").write_text('"""Owns the one thing."""\n', encoding="utf-8")

    with pytest.raises(ItemError, match="LAYER_ORDER"):
        collect_modules(tmp_path)


def test_a_module_without_a_docstring_is_refused():
    with pytest.raises(ItemError, match="no docstring"):
        module_annotation(Path("thing.py"), "x = 1\n")


def test_a_first_line_too_long_for_the_tree_column_is_refused():
    long = '"""' + "words " * 20 + '"""'

    with pytest.raises(ItemError, match="chars"):
        module_annotation(Path("thing.py"), long)


def test_an_annotation_that_dodges_ownership_is_refused():
    """ "Helpers" is the word a module reaches for when it owns more than one
    thing; the gate asks again at the moment renaming is cheapest."""
    with pytest.raises(ItemError, match="helper"):
        module_annotation(Path("thing.py"), '"""Helpers for the pipeline."""')


def test_a_child_of_core_outside_the_adr_enumeration_is_a_stray(tmp_path):
    """ADR-6: core's membership is closed — a new resident revises the ADR
    before the gate admits it."""
    core = tmp_path / "src" / "sieve" / "core"
    (core / "ops").mkdir(parents=True)
    (core / "__pycache__").mkdir()
    (core / "types.py").touch()
    (core / "convenience.py").touch()

    assert doc_index.core_strays(tmp_path) == ["convenience.py"]
    assert doc_index.core_strays(tmp_path / "empty") == []


def test_a_dropped_path_that_gets_built_is_caught(tmp_path):
    (tmp_path / "src" / "sieve" / "backend").mkdir(parents=True)

    assert forbidden_present(tmp_path) == ["src/sieve/backend"]
    assert forbidden_present(tmp_path / "empty") == []


def test_the_scaffold_renders_the_absent_list_beside_the_built_one():
    text = render_scaffold([("src/sieve/core/types.py", "The four quantities.")])

    assert "src/sieve/core/types.py" in text
    assert "## Absent by decision" in text
    assert "src/sieve/backend" in text


# Dead language: vocabulary an ADR renamed away fails in the binding docs,
# so the old word cannot creep back through prose nobody rereads.


def write_doc(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_the_buried_word_fails_in_a_binding_doc(tmp_path):
    write_doc(tmp_path, "docs/VISION.md", "The pipeline is a chain of filters.\n")

    hits = doc_index.dead_language(tmp_path)

    assert len(hits) == 1
    assert hits[0].startswith("docs/VISION.md:1:")
    assert "tools-not-filters" in hits[0]


def test_quoting_history_names_and_the_rename_itself_all_pass(tmp_path):
    write_doc(
        tmp_path,
        "docs/PLAN.md",
        "All ten v2 filters registered CPU-only.\n"
        "`filters/detect.py` ports as `tools/detect.py`.\n"
        "Terminology: tools, not filters.\n"
        "The slug tools-not-filters is citable anywhere.\n",
    )

    assert doc_index.dead_language(tmp_path) == []


def test_findings_speak_the_language_of_what_they_measured(tmp_path):
    write_doc(tmp_path, "docs/findings/2026.08.06-census.md", "all ten filter modules\n")

    assert doc_index.dead_language(tmp_path) == []


# The live gate: the repo's own folders parse, and the checked-in indexes are
# exactly what the tool would write — a stale index fails here, not in review.


def test_the_repos_own_items_are_hygienic():
    collect(doc_index.TODO_DIR)
    collect_findings(doc_index.FINDINGS_DIR)
    collect_findings(doc_index.LOOP_DIR)
    collect_modules(doc_index.REPO)
    collect_adrs(doc_index.ADR_DIR)
    assert forbidden_present(doc_index.REPO) == []
    assert doc_index.core_strays(doc_index.REPO) == []
    assert doc_index.dead_language(doc_index.REPO) == []


def test_the_checked_in_indexes_are_current():
    for index, expected in (
        (
            doc_index.TODO_DIR / doc_index.INDEX_NAME,
            render(collect(doc_index.TODO_DIR), phase_titles()),
        ),
        (
            doc_index.FINDINGS_DIR / doc_index.INDEX_NAME,
            render_findings(
                collect_findings(doc_index.FINDINGS_DIR), collect_findings(doc_index.LOOP_DIR)
            ),
        ),
        (doc_index.SCAFFOLD, render_scaffold(collect_modules(doc_index.REPO))),
        (
            doc_index.ARCHITECTURE,
            render_architecture(collect_adrs(doc_index.ADR_DIR), parse_groups()),
        ),
    ):
        assert index.is_file(), f"{index.name} missing — run `uv run python scripts/doc_index.py`"
        assert index.read_text(encoding="utf-8") == expected, (
            f"stale {index} — run `uv run python scripts/doc_index.py`"
        )
