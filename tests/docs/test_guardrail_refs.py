"""A guardrail that names a check must name one that exists.

`tests/docs/test_doc_refs.py` already resolves the *path* half of every
pointer in the live docs. The half left open is the one that reads as done
forever: a check that existed when it was cited and has since been renamed,
and a **Trigger:** that fired with nobody noticing — which is exactly what
happened to AUTO-GUARDRAILS §2 at schema v3.

Each test below fails for a distinct reason: a renamed check, a renamed
contract, a trigger that fired without becoming an item, and a rule claiming a
gate that does not exist. The negative cases exist because a checker over a
tree that currently satisfies it cannot otherwise be told from a checker that
never looks — the failure `doc_refs.py`'s docstring records cutting a symbol
checker over.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardrail_refs import GUARDRAILS as G
from guardrail_refs import (
    REWORK,
    contract_claims,
    gate_paragraphs,
    named_checks,
    trigger_health,
    triggers,
    ungated,
    unresolved_contracts,
    unresolved_tests,
)

# --- the live tree ----------------------------------------------------------


def test_every_named_check_still_exists() -> None:
    missing = unresolved_tests()
    assert not missing, "renamed or removed:\n" + "\n".join(f"  {d} -> {t}" for d, t in missing)


def test_every_cited_contract_still_exists() -> None:
    missing = unresolved_contracts()
    assert not missing, "no such contract:\n" + "\n".join(f"  {d} -> {t}" for d, t in missing)


def test_every_trigger_parses_and_a_fired_one_carries_an_item() -> None:
    parsed, complaints = triggers()
    assert not complaints, "\n".join(f"  {c}" for c in complaints)
    assert all(t.item is not None for t in parsed if t.fired)


def test_every_gate_names_a_live_check_or_says_open() -> None:
    bad = ungated()
    assert not bad, "gates naming nothing that exists:\n" + "\n".join(f"  {g}" for g in bad)


def test_the_claims_being_checked_are_actually_there() -> None:
    # Every assertion above passes vacuously on a document the parser cannot
    # read, which is the way a doc checker dies.
    assert len(named_checks(G)) >= 5, named_checks(G)
    assert "gui-computes-nothing" in contract_claims(G)
    parsed, _ = triggers()
    # Three, not the four this read at first. A discharged trigger *leaves* the
    # file — §2's went when the parity check landed — so this floor moves down
    # as guardrails get built, and a floor nobody may lower would eventually be
    # met by leaving a stale trigger in place.
    assert len(parsed) >= 3 and any(t.fired for t in parsed)
    assert len(gate_paragraphs(REWORK)) >= 6


def test_the_state_line_reads_dates_from_the_file() -> None:
    # `.state.md` is compared byte-for-byte by `--check`; a line carrying
    # anything that moves with the clock fails the gate on a day nobody edited.
    line = trigger_health()
    assert "oldest re-check 2026." in line
    assert line == trigger_health()


# --- the checker can fail ---------------------------------------------------


def _doc(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "FIXTURE.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_a_renamed_check_is_caught(tmp_path: Path) -> None:
    gone = "tests/unit/test_cache_key.py::test_long_gone"
    doc = _doc(tmp_path, f"**Enforced by:** `{gone}`.\n")
    assert unresolved_tests([doc]) == [("FIXTURE.md", gone)]
    # A method on a class resolves; the AST walk is not top-level only.
    live = _doc(tmp_path, "`tests/unit/test_cache_key.py::TestIsolation`\n")
    assert not unresolved_tests([live])


def test_a_renamed_contract_is_caught(tmp_path: Path) -> None:
    doc = _doc(tmp_path, "**Enforced by:** `.importlinter`'s `gui-does-nothing` contract.\n")
    assert unresolved_contracts([doc]) == [("FIXTURE.md", "gui-does-nothing")]


@pytest.mark.parametrize(
    "body",
    [
        "**Trigger: FIRED** (audited 2026.01.01) — nobody wrote the item.",
        "**Trigger: FIRED** (audited 2026.01.01) → `docs/todo/no-such-item.md` — gone.",
        "**Trigger: FIRED** — no date at all.",
        "**Trigger: MAYBE** (re-checked 2026.01.01) — not a state.",
        "**Trigger:** FIRED (2026.01.01) — the state escaped the bold.",
    ],
)
def test_a_malformed_trigger_is_caught(tmp_path: Path, body: str) -> None:
    parsed, complaints = triggers(_doc(tmp_path, body + "\n"))
    assert complaints and not parsed


def test_the_construct_named_in_prose_is_not_read_as_a_declaration(tmp_path: Path) -> None:
    # AUTO-GUARDRAILS' "Adding one" section says a rule may carry a
    # **Trigger:** line instead of a check. That sentence is not a trigger.
    doc = _doc(tmp_path, "a rule with a **Trigger:** line instead of a check is acceptable\n")
    assert triggers(doc) == ([], [])


def test_a_gate_that_names_nothing_is_caught(tmp_path: Path) -> None:
    assert ungated(_doc(tmp_path, "**Gate:** soon, once somebody writes it.\n"))
    assert not ungated(_doc(tmp_path, "**Gate:** OPEN — the declarable-shape walk.\n"))
    assert not ungated(_doc(tmp_path, "**Gate:** `gui-computes-nothing` in `.importlinter`.\n"))
    # Mid-paragraph is the sentence naming the construct, not a rule's gate.
    assert not ungated(_doc(tmp_path, "A rule graduates when its **Gate:** line names one.\n"))
