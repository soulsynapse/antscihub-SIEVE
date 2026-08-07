"""The item folder stays readable by machine, and the index never drifts.

The vocabulary tests exist because the statuses are a protocol, not labels:
`awaiting-review` is how a worker's claim and a review's verdict stay two
different edits, and a value outside the vocabulary would let an item slip
out of both lists silently.
"""

from pathlib import Path

import pytest
import todo_index
from todo_index import ItemError, collect, next_takeable, phase_titles, render


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


# The live gate: the repo's own folder parses, and the checked-in index is
# exactly what the tool would write — a stale index fails here, not in review.


def test_the_repos_own_items_are_hygienic():
    collect(todo_index.TODO_DIR)


def test_the_checked_in_index_is_current():
    index = todo_index.TODO_DIR / todo_index.INDEX_NAME
    assert index.is_file(), "no index — run `uv run python tools/todo_index.py`"
    expected = render(collect(todo_index.TODO_DIR), phase_titles())
    assert index.read_text(encoding="utf-8") == expected, (
        "stale index — run `uv run python tools/todo_index.py`"
    )
