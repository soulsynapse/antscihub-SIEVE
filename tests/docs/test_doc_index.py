"""The item folder stays readable by machine, and the index never drifts.

The vocabulary tests exist because the statuses are a protocol, not labels:
`awaiting-review` is how a worker's claim and a review's verdict stay two
different edits, and a value outside the vocabulary would let an item slip
out of both lists silently.
"""

import re
import subprocess
from pathlib import Path

import doc_index
import pytest
import yaml
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

#: A pool item on phase 5, against the phase-6 step in SEQUENCED_6 — the pair
#: most of the ordering cases are built from.
OWED = """title: An aside phase 5 holds
priority: normal
phase: 5
status: open
gated_on: nothing
done_when: "true"
opened: 2026-08-07"""

SEQUENCED_6 = SEQUENCED.replace('"02.3"', '"06.3"')


def test_a_decimal_aside_orders_between_its_neighbours(tmp_path):
    write_item(tmp_path, "third", SEQUENCED)
    write_item(tmp_path, "fourth", SEQUENCED.replace('"02.3"', '"02.4"'))
    write_item(tmp_path, "aside", SEQUENCED.replace('"02.3"', '"02.3.1"'))

    steps = [item.fields["step"] for item in collect(tmp_path)]
    ordered = sorted(collect(tmp_path), key=lambda i: i.step_key or ())

    assert set(steps) == {"02.3", "02.3.1", "02.4"}
    assert [item.fields["step"] for item in ordered] == ["02.3", "02.3.1", "02.4"]


def test_a_step_outranks_a_pool_item_in_its_own_phase(tmp_path):
    write_item(tmp_path, "aside", OWED.replace("phase: 5", "phase: 2"))
    write_item(tmp_path, "step", SEQUENCED)

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "step.md"


def test_an_earlier_phase_outranks_everything_in_a_later_one(tmp_path):
    # Including its steps and including its urgency: the number already claims
    # that one must hold before the other is worth doing, so a priority able to
    # jump it would be a second ordering laid over the first.
    write_item(tmp_path, "later-step", SEQUENCED_6)
    urgent = OWED.replace("phase: 5", "phase: 6").replace("priority: normal", "priority: high")
    write_item(tmp_path, "later-urgent", urgent)
    write_item(tmp_path, "earlier", OWED.replace("priority: normal", "priority: low"))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "earlier.md"


def test_a_claim_awaiting_review_is_not_in_the_queue(tmp_path):
    write_item(tmp_path, "claimed", SEQUENCED.replace("status: open", "status: awaiting-review"))
    write_item(tmp_path, "takeable", SEQUENCED.replace('"02.3"', '"02.4"'))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "takeable.md"


def test_the_pool_runs_by_priority_and_then_by_name(tmp_path):
    # Named against the alphabet on purpose: sorting on the filename alone
    # would put `a-low` first and pass a test that checks nothing.
    write_item(tmp_path, "a-low", OWED.replace("priority: normal", "priority: low"))
    write_item(tmp_path, "b-urgent", OWED.replace("priority: normal", "priority: high"))

    order = [i.path.name for i in doc_index.queue(collect(tmp_path))]

    assert order == ["b-urgent.md", "a-low.md"]


def test_an_unattached_item_sorts_after_every_phase(tmp_path):
    write_item(tmp_path, "a-loose", OWED.replace("phase: 5\n", ""))
    write_item(tmp_path, "z-phased", OWED)

    order = [i.path.name for i in doc_index.queue(collect(tmp_path))]

    assert order == ["z-phased.md", "a-loose.md"]


def test_a_step_minted_into_a_completed_phase_outranks_the_current_one(tmp_path):
    # The reading this refuses: a phase whose steps all say `done` looks shut,
    # so an item belonging to it gets filed forward onto whatever phase is
    # running. The number is the ordering, not a record of what is finished.
    write_item(tmp_path, "started", SEQUENCED_6.replace("status: open", "status: done"))
    write_item(tmp_path, "current", SEQUENCED_6.replace('"06.3"', '"06.4"'))
    closed = SEQUENCED.replace('"02.3"', '"05.8"').replace("status: open", "status: done")
    write_item(tmp_path, "closed", closed)
    write_item(tmp_path, "reopened", SEQUENCED.replace('"02.3"', '"05.9"'))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "reopened.md"


def test_next_is_the_first_open_item_reading_the_index_top_to_bottom(tmp_path):
    """The invariant that makes the generated index the authority.

    Two orderings — the one `queue_key` sorts by and the one `render` lays its
    tables out in — and a reader who scrolls to the first `open` row has to
    land on the item the loop is about to take. Asserted against the rendered
    text rather than a second sort, because a test that re-derived the order
    would agree with the selector while the page disagreed with both.
    """
    write_item(tmp_path, "shut", SEQUENCED.replace("status: open", "status: done"))
    write_item(tmp_path, "step", SEQUENCED.replace('"02.3"', '"02.4"'))
    write_item(tmp_path, "aside", OWED.replace("phase: 5", "phase: 2"))
    write_item(tmp_path, "later", SEQUENCED_6)
    write_item(tmp_path, "loose", OWED.replace("phase: 5\n", ""))
    items = collect(tmp_path)

    seen: list[str] = []
    for match in re.finditer(r"\]\((?P<name>[a-z0-9-]+\.md)\)", render(items, {})):
        if match["name"] not in seen:
            seen.append(match["name"])
    status = {i.path.name: i.status for i in items}

    head = next_takeable(items)
    assert head is not None
    assert head.path.name == next(name for name in seen if status[name] == "open")


def test_a_pending_review_outranks_every_other_role(tmp_path):
    write_item(tmp_path, "claimed", SEQUENCED.replace("status: open", "status: awaiting-review"))
    write_item(tmp_path, "takeable", SEQUENCED.replace('"02.3"', '"02.4"'))

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("review", "claimed.md")


def test_reviews_queue_by_step_not_by_filename(tmp_path):
    claimed = SEQUENCED.replace("status: open", "status: awaiting-review")
    write_item(tmp_path, "z-early", claimed.replace('"02.3"', '"02.1"'))
    write_item(tmp_path, "a-late", claimed.replace('"02.3"', '"02.9"'))

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("review", "z-early.md")


def test_work_is_the_role_when_the_head_carries_a_criterion(tmp_path):
    write_item(tmp_path, "step", SEQUENCED)

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("work", "step.md")


def test_a_head_with_no_criterion_is_a_specify_run_on_that_same_item(tmp_path):
    # It is not skipped and it shuts nothing: the item that would have been
    # worked is handed to the one role permitted to write a `done_when`.
    write_item(tmp_path, "vague", OWED.replace('done_when: "true"\n', ""))
    write_item(tmp_path, "ready", OWED.replace("phase: 5", "phase: 6"))

    role, item = doc_index.next_action(collect(tmp_path))

    assert (role, item.path.name) == ("specify", "vague.md")


def test_a_later_item_does_not_jump_the_queue_by_having_a_criterion(tmp_path):
    # The rule this refuses is the one the boundary drain had. Serving the
    # first *specified* item makes the queue drainable by ignoring exactly the
    # work that needs specifying, and lets a criterion act as a priority.
    write_item(tmp_path, "vague", OWED.replace('done_when: "true"\n', ""))
    write_item(tmp_path, "ready", OWED.replace("priority: normal", "priority: low"))

    item = next_takeable(collect(tmp_path))

    assert item is not None and item.path.name == "vague.md"


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


def test_a_deferral_is_not_in_the_queue_at_all(tmp_path):
    # From an earlier phase, which under a phase-first order is the only way
    # to tell "not queued" from "queued behind everything".
    write_item(tmp_path, "step", SEQUENCED_6)
    write_item(tmp_path, "parked", DEFERRED.replace("phase: 5", "phase: 1"))

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


def test_the_pool_takes_the_earliest_phase_first(tmp_path):
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


def test_a_value_opening_with_a_code_span_names_its_line_and_its_field(tmp_path):
    """The commonest way to write invalid frontmatter here, because the fields
    are prose about code: YAML reserves a leading backtick, and the scanner's
    own message names that character in a file full of them."""
    write_item(tmp_path, "bad", SEQUENCED.replace("nothing", "`ruff` being pinned"))

    with pytest.raises(ItemError, match=r"line 5, `gated_on`"):
        collect(tmp_path)


def test_the_field_named_is_the_key_inside_the_list_entry_not_the_list(tmp_path):
    write_item(
        tmp_path,
        "bad",
        SEQUENCED + "\nmeasurements:\n  - probe: a run\n    result: `n=3` frames",
    )

    with pytest.raises(ItemError, match=r"line 10, `result`"):
        collect(tmp_path)


def test_frontmatter_that_stops_nowhere_in_particular_still_reports(tmp_path):
    """A `YAMLError` carrying no mark — the message degrades to the plain one
    rather than the blame becoming the thing that raises."""
    assert "not valid YAML" in doc_index._yaml_blame([], yaml.YAMLError("no mark on this"))


def test_the_template_is_machinery_not_an_entry(tmp_path):
    write_item(tmp_path, "_TEMPLATE", "not: frontmatter the collector should read")

    assert collect(tmp_path) == []


def _repo_with_items(tmp_path, *names: str):
    """A git repo whose `docs/todo` holds `names`, committed.

    A real repository rather than a stubbed `_git`, because what is being
    checked is the reading of `ls-files` and `git grep` output — a stub would
    assert that the parser matches the fixture's idea of the format, which is
    the half that was never in doubt.
    """
    todo = tmp_path / "docs" / "todo"
    todo.mkdir(parents=True)
    for name in names:
        write_item(todo, name, POOLED)
    # Identity and signing are pinned on the command rather than inherited:
    # a fixture that borrowed the developer's git config would pass or fail by
    # whether they sign their commits.
    git = ["git", "-C", str(tmp_path)]
    identity = ["-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    for command in (["init", "-q"], ["add", "-A"], [*identity, "commit", "-q", "-m", "items"]):
        subprocess.run([*git, *command], check=True, capture_output=True)
    return todo


def test_minting_over_a_taken_slug_is_refused(tmp_path):
    # The accident this exists for: the write succeeds, the item is gone, and
    # the index is exactly as consistent as it was before.
    write_item(tmp_path, "_TEMPLATE", "title: t")
    write_item(tmp_path, "taken", POOLED, body="the item that would be deleted")

    with pytest.raises(ItemError, match="already exists"):
        doc_index.mint("taken", tmp_path)

    assert "would be deleted" in (tmp_path / "taken.md").read_text(encoding="utf-8")


def test_a_file_whose_name_differs_only_in_case_still_holds_the_slug(tmp_path):
    # The listing is case-folded rather than trusting `exists()`, because NTFS
    # and the index disagree about whether these are one file — and a rule that
    # is right only on the machine that wrote it is the wrong kind of guard.
    write_item(tmp_path, "_TEMPLATE", "title: t")
    write_item(tmp_path, "Taken", POOLED)

    with pytest.raises(ItemError, match="already exists"):
        doc_index.mint("taken", tmp_path)


def test_a_slug_with_capitals_or_underscores_is_refused(tmp_path):
    write_item(tmp_path, "_TEMPLATE", "title: t")

    with pytest.raises(ItemError, match="not a slug"):
        doc_index.mint("Two_Words", tmp_path)


def test_minting_a_free_slug_starts_from_the_template(tmp_path):
    write_item(tmp_path, "_TEMPLATE", "title: t", body="what should be different")

    path = doc_index.mint("a-new-item", tmp_path)

    assert path.name == "a-new-item.md"
    assert "what should be different" in path.read_text(encoding="utf-8")


def test_an_item_gone_since_the_commit_is_named_with_where_it_still_is(tmp_path):
    todo = _repo_with_items(tmp_path, "kept", "lost")
    (todo / "lost.md").unlink()

    problems = doc_index.tracked_drift(todo, tmp_path)

    assert len(problems) == 1
    assert "lost.md" in problems[0] and "HEAD" in problems[0]


def test_an_opened_date_that_moved_means_the_slug_was_written_over(tmp_path):
    # Forward, which is the direction a collision actually moves it: the run
    # that overwrites stamps today. The finding this closes says "backwards".
    todo = _repo_with_items(tmp_path, "hit")
    written_over = POOLED.replace("opened: 2026-08-06", "opened: 2026-08-09")
    write_item(todo, "hit", written_over)

    problems = doc_index.tracked_drift(todo, tmp_path)

    assert len(problems) == 1
    assert "2026-08-06 -> 2026-08-09" in problems[0]


def test_an_untracked_folder_has_nothing_to_have_drifted_from(tmp_path):
    # The check may never be the reason the index will not build.
    write_item(tmp_path, "loose", POOLED)

    assert doc_index.tracked_drift(tmp_path, tmp_path) == []


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


# The ownership line against the decision that assigns it. Deriving SCAFFOLD
# from the docstring proves the annotation was copied into the tree faithfully
# and proves nothing about the docstring naming what VISION.md's component
# table gives the package — which is the link a module gets misfiled across.


COMPONENTS = """## Components, and what each must never own

| Package | Owns | Never |
|---|---|---|
| `core` | the **dimensioned types**, **schema v1** — membership closed | Qt |

## Vision
"""


def _repo_with_components(tmp_path: Path, annotation: str, table: str = COMPONENTS) -> Path:
    write_doc(tmp_path, "docs/VISION.md", table)
    write_doc(tmp_path, "src/sieve/core/__init__.py", f'"""{annotation}"""\n')
    return tmp_path


def test_an_ownership_the_table_assigns_and_the_line_omits_is_caught(tmp_path):
    # The case that motivated the gate: `core` owned schema v1 by decision and
    # said so nowhere, and every check in the repo was green.
    repo = _repo_with_components(tmp_path, "The dimensioned types and spec-free array math.")

    problems = doc_index.annotation_gaps(repo)

    assert len(problems) == 1
    assert "schema v1" in problems[0] and "core" in problems[0]


def test_a_line_that_names_every_marked_phrase_passes(tmp_path):
    # Extra words are fine and the case is ignored: the claim is that the line
    # names the thing, not that it is the cell.
    repo = _repo_with_components(tmp_path, "Dimensioned types, `schema v1`, and array math.")

    assert doc_index.annotation_gaps(repo) == []


def test_a_row_that_marks_nothing_it_owns_is_refused(tmp_path):
    """The convention is the whole gate: an unmarked cell checks nothing, and
    would read from the table as a package that owns nothing."""
    repo = _repo_with_components(tmp_path, "Anything at all.", COMPONENTS.replace("**", ""))

    problems = doc_index.annotation_gaps(repo)

    assert len(problems) == 1 and "marks nothing" in problems[0]


def test_a_row_whose_package_does_not_exist_is_reported(tmp_path):
    repo = _repo_with_components(tmp_path, "Anything at all.", COMPONENTS.replace("core", "kernel"))

    problems = doc_index.annotation_gaps(repo)

    assert len(problems) == 1 and "kernel" in problems[0]


def test_a_table_that_has_gone_missing_fails_rather_than_passing_vacuously(tmp_path):
    repo = _repo_with_components(tmp_path, "Anything at all.", "# Vision\n\nProse and no table.\n")

    problems = doc_index.annotation_gaps(repo)

    assert len(problems) == 1 and "component table" in problems[0]


# A broken module tree is one target's problem, not four — and never the
# selection rule's, which reads no docstring.


def _tree_with_a_bad_docstring(tmp_path: Path) -> Path:
    """A repo whose items are clean and whose one module is over the limit.

    The shape that motivated the split: only SCAFFOLD.md is derived from a
    docstring, and the annotation limit is the one gate a module trips by
    being written normally rather than by being wrong.
    """
    todo = tmp_path / "docs" / "todo"
    todo.mkdir(parents=True)
    (tmp_path / "docs" / "findings").mkdir()
    write_item(todo, "step", SEQUENCED)
    module = tmp_path / "src" / "thing.py"
    module.parent.mkdir(parents=True)
    module.write_text(
        '"""Owns ' + "the one thing " * 8 + 'and nothing else."""\n', encoding="utf-8"
    )
    return tmp_path


def test_next_is_answered_from_the_items_while_the_module_tree_is_broken(tmp_path, capsys):
    # The loop's selection rule has no dependency on a docstring, so a bad one
    # must not be able to stop the queue — least of all when the item that
    # would record it is in the tree it blocked.
    repo = _tree_with_a_bad_docstring(tmp_path)

    code = doc_index.main(["--next"], repo=repo)

    assert code == 0
    assert capsys.readouterr().out.strip() == "work docs/todo/step.md"


def test_the_three_targets_that_render_are_written_and_only_the_scaffold_is_refused(
    tmp_path, capsys
):
    repo = _tree_with_a_bad_docstring(tmp_path)

    code = doc_index.main([], repo=repo)

    assert code == 1
    assert "SCAFFOLD.md" in capsys.readouterr().err
    assert not (repo / "docs" / "SCAFFOLD.md").exists()
    assert "A step" in (repo / "docs" / "todo" / ".index.md").read_text(encoding="utf-8")
    assert (repo / "docs" / "findings" / ".index.md").is_file()
    assert (repo / "docs" / "ARCHITECTURE.md").is_file()


# The rest of the command line. Each of these is driven through `main` rather
# than through the function it exercises, because every one of them was found
# individually well covered and wired to nothing: `tracked_drift`, `mint` and
# all four gate predicates could be cut out of `main` with the suite green.


def test_the_index_build_refuses_a_drifted_item(tmp_path, capsys):
    todo = _repo_with_items(tmp_path, "hit")
    (tmp_path / "docs" / "findings").mkdir()
    write_item(todo, "hit", POOLED.replace("opened: 2026-08-06", "opened: 2026-08-09"))

    code = doc_index.main([], repo=tmp_path)

    assert code == 1
    assert "overwritten or removed" in capsys.readouterr().err


def test_mint_over_a_taken_slug_exits_one_and_leaves_the_file(tmp_path, capsys):
    todo = tmp_path / "docs" / "todo"
    todo.mkdir(parents=True)
    write_item(todo, "_TEMPLATE", "title: t")
    write_item(todo, "taken", POOLED, body="the item that would be deleted")

    code = doc_index.main(["--mint", "taken"], repo=tmp_path)

    assert code == 1
    assert "already exists" in capsys.readouterr().err
    assert "would be deleted" in (todo / "taken.md").read_text(encoding="utf-8")


def test_every_gate_is_reported_and_none_of_them_stops_a_write(tmp_path, capsys):
    # All five at once, because the claim is about `gates` reporting rather
    # than any one refusal: a run that stopped at the first would report one of
    # these, and a run that let a refusal shadow the render would write none of
    # the four targets. Nothing here is a `.py` file — the tree has to trip the
    # gates while the scaffold still renders, or the second half of the
    # assertion would be testing the annotation limit again.
    todo = _repo_with_items(tmp_path, "hit")
    docs = tmp_path / "docs"
    (docs / "findings").mkdir()
    write_item(todo, "hit", POOLED.replace("opened: 2026-08-06", "opened: 2026-08-09"))
    (tmp_path / "src" / "sieve" / "backend").mkdir(parents=True)
    (tmp_path / "src" / "sieve" / "core").mkdir(parents=True)
    (tmp_path / "src" / "sieve" / "core" / "stray.txt").write_text("", encoding="utf-8")
    (docs / "NOTES.md").write_text("the filter runs first\n", encoding="utf-8")
    # `core/` here is a directory with no `__init__.py`, so the row is a
    # component the tree does not have.
    (docs / "VISION.md").write_text(COMPONENTS, encoding="utf-8")

    code = doc_index.main([], repo=tmp_path)

    errors = capsys.readouterr().err
    assert code == 1
    for reported in (
        "overwritten or removed",
        "absent-by-decision paths exist",
        "core has children ADR-6 does not admit",
        "dead language",
        "component table",
    ):
        assert reported in errors, f"{reported!r} not reported: {errors}"
    for target, _ in doc_index.derived(collect(todo), tmp_path):
        assert target.is_file(), f"{target.name} was not written past the gates"


# The live gate: the repo's own folders parse, and the checked-in indexes are
# exactly what the tool would write — a stale index fails here, not in review.


def test_the_repos_own_items_are_hygienic():
    collect(doc_index.TODO_DIR)
    collect_findings(doc_index.FINDINGS_DIR)
    collect_findings(doc_index.LOOP_DIR)
    collect_modules(doc_index.REPO)
    collect_adrs(doc_index.ADR_DIR)
    assert doc_index.gates() == []


def test_the_checked_in_indexes_are_current():
    # Over `derived` rather than a second list of the four, which would let a
    # target added to the tool arrive here untested and look covered.
    for index, build in doc_index.derived(collect(doc_index.TODO_DIR)):
        assert index.is_file(), f"{index.name} missing — run `uv run python scripts/doc_index.py`"
        assert index.read_text(encoding="utf-8") == build(), (
            f"stale {index} — run `uv run python scripts/doc_index.py`"
        )
