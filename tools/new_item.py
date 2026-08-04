"""Mint an item: write a `docs/todo/<slug>.md` with `opened` already stamped.

The counterpart to `complete_item.py`, and it exists for one reason: `opened`
has to be the moment the item was written, and the agent writing it does not
know the time. Every other field here is one the author fills in — this tool
only guarantees the one that cannot be typed accurately.

`opened` is the tiebreak inside a priority band (`doc_index.item_order`), so a
day-precision stamp is the same defect the completed entries had: twenty-four
items were minted on 2026-07-29 and their order was the alphabet.

    uv run python tools/new_item.py the-crop-is-a-filter --title "The crop is a filter"
    uv run python tools/new_item.py gpu-execution --status deferred --priority low
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TODO_DIR = REPO_ROOT / "docs" / "todo"

CHECKLIST = """\
new_item: wrote {path}

`opened` is stamped and `status`/`priority` are set. Still yours:
  1. Fill `gated_on` — for an open item usually `nothing structurally`; for a
     deferred one the trigger, as an event a later session can recognise.
  2. Write the body: what is wrong now, what "done" looks like, and the files
     it touches. An item whose steps cannot be listed up front is not written.
  3. Add `after: [slug]` for any item this one must not be started before.
  4. uv run nox -s docs
"""

BODY = """\
---
title: {title}
status: {status}
opened: {stamp}
priority: {priority}
gated_on: TODO — `nothing structurally`, or the trigger this waits on
---

## What is wrong now

TODO — the defect or the gap, in the present tense, with the file it lives in.

## What done looks like

TODO — the observable state, and the check that would fail if it regressed.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="short-kebab-name for the filename")
    parser.add_argument("--title", help="item title; defaults to the slug, de-hyphenated")
    parser.add_argument("--status", default="open", choices=("open", "deferred"))
    parser.add_argument(
        "--priority", default="unassessed", choices=("high", "normal", "low", "unassessed")
    )
    args = parser.parse_args(argv)

    slug = str(args.slug).strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        print(f"new_item: {slug!r} is not a kebab-case slug", file=sys.stderr)
        return 1

    path = TODO_DIR / f"{slug}.md"
    if path.exists():
        print(f"new_item: {path} already exists — not overwriting", file=sys.stderr)
        return 1

    text = BODY.format(
        title=str(args.title) if args.title else slug.replace("-", " ").capitalize(),
        status=args.status,
        stamp=datetime.now().astimezone().replace(microsecond=0).isoformat(),
        priority=args.priority,
    )
    path.write_text(text, encoding="utf-8", newline="\n")
    print(CHECKLIST.format(path=path.relative_to(REPO_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
