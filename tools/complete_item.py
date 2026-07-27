"""Scaffold a `docs/completed-todo/` entry for the item being finished.

The completion ceremony has a mechanical half (frontmatter skeleton, today's
date, the file lists the working tree already knows) and a thinking half
(summary, decisions, rejected alternatives). Transcript mining showed the
ceremony is paid for in generated tokens, not tool time — so this script emits
the mechanical half and prints the checklist for the rest, and deliberately
does *not* rebuild the doc index: an entry whose summary still says TODO must
not be rendered into `.index.md` as if it were finished.

    uv run python tools/complete_item.py the-motion-history-filter
    uv run python tools/complete_item.py fix-scroll --title "Scroll fix"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPLETED = REPO_ROOT / "docs" / "completed-todo"

CHECKLIST = """\
complete_item: wrote {path}

Still yours to do, in order:
  1. Fill `summary`, `decisions`, `rejected` — the TODO markers fail the gate.
  2. Delete the item's section from docs/TODO.md (moved, never marked done).
  3. If anything was *measured*, it goes to docs/findings/, not this entry.
  4. uv run nox -s checks
  5. uv run nox -s docs
  6. Commit, then `git rev-parse --short HEAD` into `commit:`, then push.
"""


def _git(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def changed_files(exclude: Path) -> tuple[list[str], list[str], list[str]]:
    """Added, changed, removed paths from the working tree + HEAD, sorted.

    Both staged-vs-HEAD and unstaged changes count — at completion time the
    work is typically uncommitted, which is exactly when the lists are cheap
    to derive and annoying to type.
    """
    added: set[str] = set()
    changed: set[str] = set()
    removed: set[str] = set()
    for line in _git("status", "--porcelain=v1"):
        status, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path == str(exclude.relative_to(REPO_ROOT)).replace("\\", "/"):
            continue
        if "D" in status:
            removed.add(path)
        elif status == "??" or "A" in status:
            added.add(path)
        else:
            changed.add(path)
    return sorted(added), sorted(changed), sorted(removed)


def _yaml_list(items: list[str], indent: str = "    ") -> str:
    if not items:
        return " []"
    return "\n" + "\n".join(f"{indent}- {item}" for item in items)


def render(title: str, added: list[str], changed: list[str], removed: list[str]) -> str:
    today = date.today()
    return f"""\
---
title: {title}
date: {today.isoformat()}
commit: pending
tags: []

summary: >
  TODO — one sentence, past tense: what the repo can do now that it could not.

files:
  added:{_yaml_list(added)}
  changed:{_yaml_list(changed)}
  removed:{_yaml_list(removed)}

decisions:
  - what: TODO — the choice
    why: TODO — the reason it stops being re-argued

# rejected:
#   - what:
#     why:
---

# {title}

TODO — what was checked by mutation, and what changed outside the item's
scope. Delete the body if neither applies.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="short-kebab-name for the filename")
    parser.add_argument("--title", help="entry title; defaults to the slug, de-hyphenated")
    args = parser.parse_args(argv)

    slug = str(args.slug).strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        print(f"complete_item: {slug!r} is not a kebab-case slug", file=sys.stderr)
        return 1

    path = COMPLETED / f"{date.today().strftime('%Y.%m.%d')}-{slug}.md"
    if path.exists():
        print(f"complete_item: {path} already exists — not overwriting", file=sys.stderr)
        return 1

    title = str(args.title) if args.title else slug.replace("-", " ").capitalize()
    added, changed, removed = changed_files(exclude=path)
    path.write_text(render(title, added, changed, removed), encoding="utf-8", newline="\n")
    print(CHECKLIST.format(path=path.relative_to(REPO_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
