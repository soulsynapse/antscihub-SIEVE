"""Mint an item: write a `docs/todo/<slug>.md` with `opened` already stamped.

The counterpart to `complete_item.py`, and it exists for one reason: `opened`
has to be the moment the item was written, and the agent writing it does not
know the time. Every other field here is one the author fills in — this tool
only guarantees the one that cannot be typed accurately.

`opened` is the tiebreak inside a priority band (`doc_index.item_order`), so a
day-precision stamp is the same defect the completed entries had: twenty-four
items were minted on 2026-07-29 and their order was the alphabet.

`BODY` below is the *only* scaffold. `docs/todo/_TEMPLATE.md` explains the
fields; it is not a second thing to copy. While it was, the two disagreed and
neither noticed: this tool emitted two body headings that 0 of 49 items ever
carried and omitted `reads`, which 49 of 49 do.

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
  2. Fill `reads` — the files to open before the first edit.
  3. Uncomment `after:` / `serves:` if they apply.
  4. Write the body. An item whose steps cannot be listed up front is not
     written; `docs/todo/_TEMPLATE.md` says what belongs there, by status.
  5. uv run nox -s docs
"""

#: The one scaffold. `docs/todo/_TEMPLATE.md` annotates these fields and is not
#: a second copy to fill in by hand — the two drifted for exactly as long as
#: nothing compared them; `tests/docs/test_todo_hygiene.py` compares them now,
#: in both directions. Every key the generators read appears below, the
#: optional ones commented rather than omitted: an absent key is invisible, and
#: the author who never sees the question never answers it. That is the same
#: argument `priority: unassessed` is spelled out for.
BODY = """\
---
title: {title}
status: {status}
opened: {stamp}
priority: {priority}
gated_on: TODO — `nothing structurally`, or the trigger this waits on
# TODO — the files to open before the first edit, so starting is opening rather
# than searching. An item needing three documents read first is not scoped yet.
reads: []
# Optional, both machine-read. Uncomment what applies:
# after: [slug]   # items this must not be started before; checked for cycles
# serves: [A1]    # the docs/ASPIRATIONS.md capability this walks toward
---

TODO — the body, and the body is the item: what is wrong now in the present
tense with the file it lives in, what done looks like as an observable state,
and the check that would fail if it regressed. Free prose, scoped to fit one
context window. A deferred item also says *why not now* — the actual reason,
not "no time".
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
    # Shortening the path for display must not be able to fail after the file
    # is on disk: `relative_to` raises for anything outside the repo, and the
    # traceback would report a failure on work that succeeded.
    try:
        shown: Path = path.relative_to(REPO_ROOT)
    except ValueError:
        shown = path
    print(CHECKLIST.format(path=shown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
