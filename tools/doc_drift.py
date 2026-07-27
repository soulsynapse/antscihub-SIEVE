"""Report which truth-claiming docs have had their subjects move under them.

The repo's binding surface is machine-checked (the doc indexes, the scaffold
tree, the budget table). Prose that *claims current truth* but cannot be
parsed — ARCHITECTURE.md's argument, a finding's verdict — can only rot
silently, and the v1 lesson is that scheduled re-reads of everything are how
documentation starts wagging the repo. So staleness announces itself instead:
a stamped doc names the commit it was last reviewed at and the paths it makes
claims about, and this script reports how far those paths have moved since.

This is a *report, not a gate* — it never fails. A drifted doc is a candidate
for one targeted revisit, not a broken build; making it a test would turn
every code change into a doc chore, which is the paralysis this design exists
to avoid.

Stamped docs carry frontmatter:

    ---
    reviewed: 4a4f3d6            # commit the claims were last checked at
    subjects: [src/sieve/, .importlinter]
    ---

Findings need no stamp — their existing `commit:` and `files:` fields are the
same information, so every non-superseded finding is checked for free.

    uv run python tools/doc_drift.py
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, cast

from doc_index import DOCS_ROOT, SPECS, collect, parse_frontmatter

REPO_ROOT = DOCS_ROOT.parent

#: Prose docs that claim current truth. Records of intent (VISION,
#: REFINED-VISION, SIEVE-HANDOFF, the parity plan) are deliberately absent:
#: they are dated and superseded, never revisited.
STAMPED = ("ARCHITECTURE.md", "AUTO-GUARDRAILS.md")

#: More commits than this touching a doc's subjects is worth a line even in
#: the quiet summary; below it, the doc is listed as current.
QUIET_BELOW = 1


def commits_since(rev: str, paths: list[str]) -> list[str]:
    """`git log --oneline rev..HEAD -- paths`, empty on any git failure."""
    result = subprocess.run(
        ["git", "log", "--oneline", f"{rev}..HEAD", "--", *paths],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [f"(git could not resolve {rev!r})"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def report_doc(name: str) -> list[str]:
    fields = parse_frontmatter(DOCS_ROOT / name)
    reviewed = str(fields.get("reviewed", "")).strip()
    raw_subjects = fields.get("subjects")
    subjects = (
        [str(s) for s in cast(list[Any], raw_subjects)] if isinstance(raw_subjects, list) else []
    )
    if not reviewed or not subjects:
        return [f"  {name}: no reviewed/subjects stamp — cannot assess"]
    moved = commits_since(reviewed, subjects)
    if len(moved) < QUIET_BELOW:
        return [f"  {name}: current (reviewed {reviewed})"]
    lines = [f"  {name}: {len(moved)} commits touched its subjects since {reviewed}"]
    lines += [f"    {line}" for line in moved[:5]]
    if len(moved) > 5:
        lines.append(f"    … and {len(moved) - 5} more")
    return lines


def report_findings() -> list[str]:
    spec = next(spec for spec in SPECS if spec.directory == "findings")
    lines: list[str] = []
    for entry in collect(DOCS_ROOT / "findings", spec.required):
        if entry.fields.get("status") == "superseded":
            continue
        commit = str(entry.fields.get("commit", "")).strip()
        raw_files = entry.fields.get("files")
        files = [str(f) for f in cast(list[Any], raw_files)] if isinstance(raw_files, list) else []
        if not commit or commit == "pending" or not files:
            continue
        moved = commits_since(commit, files)
        if len(moved) >= 3:
            lines.append(
                f"  {entry.path.name}: {len(moved)} commits touched its files "
                f"since {commit} — verdict may describe a system that moved"
            )
    return lines or ["  (none with 3+ commits of movement)"]


def main() -> int:
    print("doc_drift: prose docs, by their stamps")
    for name in STAMPED:
        for line in report_doc(name):
            print(line)
    print("doc_drift: findings whose measured files moved most")
    for line in report_findings():
        print(line)
    print("doc_drift: a listed doc wants one targeted revisit, not a rewrite;")
    print("doc_drift: re-stamp `reviewed:` after checking the claims still hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
