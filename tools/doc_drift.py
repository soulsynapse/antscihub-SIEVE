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

Every top-level doc declares what kind of thing it is, in its own first three
lines, so a reader can tell whether it is *supposed* to be true now without
consulting a list held somewhere else:

    ---
    status: current              # current | record
    reviewed: 4a4f3d6            # commit the claims were last checked at
    subjects: [src/sieve/, .importlinter]
    ---

Only `current` docs can drift, so only they are reported. `reviewed`/
`subjects` are what makes the report quantitative; a `current` doc without
them is listed as unassessable rather than as clean, because an unstamped doc
is exactly the one nobody has checked. `UNSTAMPED` names the files that
declare nothing and are not asked to.

Findings need no stamp — their existing `commit:` and `files:` fields are the
same information, so every non-superseded finding is checked for free.

    uv run python tools/doc_drift.py
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, cast

from doc_index import DOCS_ROOT, SPECS, FrontmatterError, collect, parse_frontmatter

REPO_ROOT = DOCS_ROOT.parent

#: The `status:` values a top-level doc may declare. `current` claims truth
#: about the code as it is now and is therefore the only kind that can go
#: stale. `record` is dated and superseded, never revisited — VISION,
#: REFINED-VISION, SIEVE-HANDOFF, the parity plan.
#:
#: This replaces a hardcoded two-name tuple of stamped docs, which was the
#: same failure the docs it governs are prone to: a list in one file naming
#: files that live somewhere else, updated by whoever remembers. The doc now
#: says what it is, in its own first three lines, where a reader sees it.
DOC_STATUS = ("current", "record")

#: Files in `docs/` that declare no status and are not asked to. Two reasons,
#: and both are "there is no claim here to go stale": `doc_index.py` writes
#: SETTLED.md and .state.md, which are current by construction or the gate is
#: already red; IDEAS.md and SCRATCH.md are workbenches that are drained
#: rather than maintained.
UNSTAMPED = ("SETTLED.md", ".state.md", "IDEAS.md", "SCRATCH.md")


def status_of(name: str) -> str:
    """The `status:` a top-level doc declares, or `""` if it has none."""
    try:
        fields = parse_frontmatter(DOCS_ROOT / name)
    except FrontmatterError:
        return ""
    return str(fields.get("status", "")).strip()


def current_docs() -> list[str]:
    """Top-level docs that claim truth about the code as it is now."""
    return sorted(
        path.name
        for path in DOCS_ROOT.glob("*.md")
        if path.name not in UNSTAMPED and status_of(path.name) == "current"
    )


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
    for entry in collect(spec):
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
    print("doc_drift: prose docs claiming current truth, by their stamps")
    for name in current_docs():
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
