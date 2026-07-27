"""TODO.md's bug list and the completed-todo folder stay honest.

Two cheap drifts these pin down. The bug list's own instruction says to tag
each entry with when it was noticed, and untagged entries accumulated anyway —
a date is what later distinguishes "regression from last week" from "known
since the rewrite". And `tools/complete_item.py` scaffolds entries with
`TODO —` markers; an entry that still carries one was filed, not finished,
and must not sit in the index looking done (rule 6).
"""

from __future__ import annotations

import re
from pathlib import Path

from doc_index import DOCS_ROOT, SKIP_PREFIXES, bug_bullets

NOTICED = re.compile(r"\(noticed (<=)?\d{4}\.\d{2}\.\d{2}( [0-9:]+)?\)")


def test_every_bug_bullet_says_when_it_was_noticed() -> None:
    todo = (DOCS_ROOT / "TODO.md").read_text(encoding="utf-8").splitlines()
    bullets = bug_bullets(todo)
    assert bullets, "the bug-section parser found nothing — did the heading move?"
    untagged = [line for line in bullets if not NOTICED.search(line)]
    assert not untagged, "bug entries without a '(noticed YYYY.MM.DD)' tag:\n" + "\n".join(untagged)


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
