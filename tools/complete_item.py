"""Complete an item: move its `docs/todo/` file into `docs/completed-todo/`.

Completion is a *move*, never a mark — this script is that rule as a
mechanism. Given a slug with a file in `docs/todo/`, it moves the file to
`docs/completed-todo/YYYY.MM.DD-<slug>.md` and swaps the item frontmatter for
the completion skeleton: title kept, file lists derived from the working tree.
Given a slug with no item file (a bug bundle, unplanned work), it scaffolds a
fresh entry instead.

**The frontmatter is the entry; a body is the exception.** Measured 2026-07-28
over the 80 entries then on disk: 9,305 lines of bodies, referenced from source
twice, against 34 references to `docs/findings/`. The index is built from
`title`/`date`/`commit`/`summary` alone, so everything under the closing `---`
was serving an audience of two.

Write a body only when a rejected alternative would otherwise be re-proposed.
A measurement goes to `docs/findings/`; why a module is shaped as it is goes in
that module's docstring.

The item text is not copied across and is not lost:
`git log --diff-filter=D -- docs/todo/<slug>.md` finds the deleting commit,
`git show <commit>^:docs/todo/<slug>.md` prints it.

The script deliberately does *not* rebuild the doc index — an entry whose
summary still says TODO must not render into `.index.md` as if it were
finished, and `tests/docs/test_todo_hygiene.py` fails the gate until the
markers are gone.

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
TODO_DIR = REPO_ROOT / "docs" / "todo"

CHECKLIST = """\
complete_item: wrote {path}

Still yours to do, in order:
  1. Fill `summary` — one sentence. It is the whole entry and the TODO marker
     fails the gate until it is gone.
  2. Leave the file at that unless a rejected alternative would otherwise be
     re-proposed; then uncomment `decisions:`/`rejected:` and say which.
     A body under the frontmatter is the exception, not the shape.
  3. If anything was *measured*, it goes to docs/findings/, not this entry.
  4. uv run nox -s checks
  5. uv run nox -s docs
  6. Commit, then `git rev-parse --short HEAD` into `commit:`, then push.
"""


def _item_title(text: str) -> str:
    """Return the `title:` from an item file's frontmatter, or `""`.

    The title is the only thing carried across. The body is not read: it stays
    in git (see the module docstring), and copying it here is what made every
    entry start at the item's length.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("title:"):
            return line.removeprefix("title:").strip()
    return ""


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


def render(
    title: str,
    added: list[str],
    changed: list[str],
    removed: list[str],
) -> str:
    """The whole entry: frontmatter, and nothing under it.

    `decisions` and `rejected` are commented out rather than scaffolded with
    markers. Neither is required by `doc_index.SPECS`, and a filled-in TODO
    marker is a stronger prompt than an empty section — the previous skeleton
    asked for a decision on every item, so every item grew one.
    """
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

# Uncomment only for a choice that would otherwise be re-argued.
# decisions:
#   - what:
#     why:
# rejected:
#   - what:
#     why:
---
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

    item_path = TODO_DIR / f"{slug}.md"
    item_title = ""
    if item_path.exists():
        item_title = _item_title(item_path.read_text(encoding="utf-8"))

    title = str(args.title) if args.title else item_title or slug.replace("-", " ").capitalize()
    added, changed, removed = changed_files(exclude=path)
    path.write_text(render(title, added, changed, removed), encoding="utf-8", newline="\n")
    if item_path.exists():
        item_path.unlink()
        print(f"complete_item: moved docs/todo/{slug}.md")
    print(CHECKLIST.format(path=path.relative_to(REPO_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
