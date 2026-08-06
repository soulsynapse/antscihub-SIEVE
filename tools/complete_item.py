"""Complete an item: move its `docs/todo/` file into `docs/completed-todo/`.

Completion is a *move*, never a mark — this script is that rule as a
mechanism. Given a slug with a file in `docs/todo/`, it moves the file to
`docs/completed-todo/YYYY.MM.DD-<slug>.md` and swaps the item frontmatter for
the completion skeleton: title kept, file lists derived from the working tree.
Given a slug with no item file (a bug bundle, unplanned work), `--new` says so
and it scaffolds a fresh entry instead. Declared rather than inferred: without
the flag a slug with no item file is a typo far more often than it is
unplanned work, and the silent fallback wrote a fresh entry while the real
item sat in `docs/todo/` untouched.

`--summary` and `--settled` fill the two fields the scaffold marks TODO, so
the entry is finished by the call that writes it. They are what makes `--new`
worth having: the alternative to a marker is not typing the answer, it is
opening a neighbouring entry to copy its shape, and the shape is this tool's
to know.

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
    uv run python tools/complete_item.py fix-scroll --new --title "Scroll fix"
    uv run python tools/complete_item.py fix-scroll --new \
        --summary "The scroll no longer jumps a page on the first wheel event." \
        --settled none
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPLETED = REPO_ROOT / "docs" / "completed-todo"
TODO_DIR = REPO_ROOT / "docs" / "todo"

#: The separator inside one `--settled` value. `|` rather than `:` because
#: every column of a real row contains a colon-space sooner or later, and
#: rather than a repeated triple of flags because the three columns are one
#: row and splitting them across flags loses which `where` belongs to which
#: `what` the moment there are two rows.
SETTLED_SEP = "|"

_SUMMARY_STEP = """\
Fill `summary` — one sentence. It is the whole entry and the TODO marker
fails the gate until it is gone."""
_SETTLED_STEP = """\
Answer `settled` — either the rows a later item must not re-decide, or the
word `none`. This is the only entry point to docs/SETTLED.md, so a decision
left out here is one somebody re-derives."""
_ALWAYS = (
    """\
Leave the file at that unless a rejected alternative would otherwise be
re-proposed; then uncomment `decisions:`/`rejected:` and say which. A body
under the frontmatter is the exception, not the shape.""",
    "If anything was *measured*, it goes to docs/findings/, not this entry.",
    "uv run nox -s checks",
    "uv run nox -s docs",
    """\
Commit, then push. `commit:` fills itself — the `post-commit` hook stamps it
and commits the stamp (`uv run nox -s hooks` if this clone has never
installed it; `commit: "pending"` surviving a commit is how you find out it
has not).""",
)


def checklist(path: str, *, has_summary: bool, has_settled: bool) -> str:
    """What is left after this call, numbered from what is actually left.

    A step for work the flags already did reads as a step skipped, and a list
    that is half skipped is one nobody reaches the end of.
    """
    steps = [
        *([] if has_summary else [_SUMMARY_STEP]),
        *([] if has_settled else [_SETTLED_STEP]),
        *_ALWAYS,
    ]
    numbered = "\n".join(
        textwrap.indent(f"{n}. {step}", "     ").replace("     ", "  ", 1)
        for n, step in enumerate(steps, start=1)
    )
    return f"complete_item: wrote {path}\n\nStill yours to do, in order:\n{numbered}\n"


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


def _repo_relative(path: Path) -> str:
    """`path` as git spells it, or `""` for anything outside the repo.

    Outside the repo is not an error here: the callers use this only to drop
    rows from a listing, and a path git can never name drops nothing.
    """
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return ""


def changed_files(*exclude: Path) -> tuple[list[str], list[str], list[str]]:
    """Added, changed, removed paths from the working tree + HEAD, sorted.

    Both staged-vs-HEAD and unstaged changes count — at completion time the
    work is typically uncommitted, which is exactly when the lists are cheap
    to derive and annoying to type.

    The item file is excluded as well as the entry. It is about to be deleted,
    and git status is read before the deletion, so an item minted in this same
    session lands in `files.added` as a path that never reached a commit —
    `2026.08.05-the-gate-ends-with-a-verdict.md` claims one. A record of files
    that were never there is rule 6 on the doc tree.
    """
    skip = {name for name in map(_repo_relative, exclude) if name}
    added: set[str] = set()
    changed: set[str] = set()
    removed: set[str] = set()
    for line in _git("status", "--porcelain=v1"):
        status, path = line[:2], line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path in skip:
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


#: Leading characters YAML reads as structure rather than text. A `where`
#: column is `` `src/sieve/x.py` `` and a `what` is a sentence, so the common
#: case needs no quoting and gets none; the uncommon one must not be allowed
#: to parse as a list or a mapping.
_NEEDS_QUOTING = re.compile(r"^[-?:,\[\]{}#&*!|>'\"%@`]|: |\t")


def _scalar(value: str) -> str:
    """One line of YAML, quoted only when leaving it bare would change it."""
    text = " ".join(value.split())
    if not text or _NEEDS_QUOTING.search(text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _folded(value: str, indent: str) -> str:
    """A `>` block scalar: prose that wraps without the wrap meaning anything.

    Every long field in these entries is written this way, and the reason is
    that the alternative is a single 400-character line that no diff of a
    later edit can be read.
    """
    return "\n".join(
        textwrap.wrap(
            " ".join(value.split()),
            width=76,
            initial_indent=indent,
            subsequent_indent=indent,
        )
    )


#: What the scaffold says where the author has not answered. `render` emits
#: these only for the fields no flag filled, and `tests/docs/test_todo_hygiene`
#: fails the gate on any that survive — which is the whole enforcement behind
#: `settled:` being answered rather than skipped.
_SUMMARY_MARKER = "  TODO — one sentence, past tense: what the repo can do now that it could not."
_SETTLED_MARKER = """\
  - what: TODO — the capability, in a few words
    where: TODO — `src/sieve/...`, backticked
    do_not_redecide: >
      TODO — the part that costs a day if it is re-derived, or delete these
      three lines and write `settled: none`."""


def render_settled(rows: list[tuple[str, str, str]] | None) -> str:
    """Everything after `settled:`, the newline included where there is one.

    `None` and `[]` are different answers and must not collapse: `[]` is the
    author saying `none`, which is a real answer, and `None` is nobody having
    been asked yet, which has to keep failing the gate.
    """
    if rows is None:
        return "\n" + _SETTLED_MARKER
    if not rows:
        return " none"
    return "\n" + "\n".join(
        f"  - what: {_scalar(what)}\n"
        f"    where: {_scalar(where)}\n"
        f"    do_not_redecide: >\n{_folded(why, '      ')}"
        for what, where, why in rows
    )


def render(
    title: str,
    added: list[str],
    changed: list[str],
    removed: list[str],
    summary: str | None = None,
    settled: list[tuple[str, str, str]] | None = None,
) -> str:
    """The whole entry: frontmatter, and nothing under it.

    `decisions` and `rejected` are commented out rather than scaffolded with
    markers. Neither is required by `doc_index.SPECS`, and a filled-in TODO
    marker is a stronger prompt than an empty section — the previous skeleton
    asked for a decision on every item, so every item grew one.

    `settled` goes the other way and *is* scaffolded with markers, because it
    is required and because the table it feeds died of being optional: rows
    were added in one burst and then not at all, while the building continued.
    The cost of the marker is that `none` must be typed; that is the point.
    An answer arriving as `--settled` rather than as an edit does not change
    that — `settled=None` still writes the marker, so the gate still refuses
    an entry nobody answered for.
    """
    # The completion moment, to the second and with its offset. Day precision
    # put twenty entries a day in one bucket and left the order inside it to
    # the filename, which is alphabetical and says nothing. Not the commit's
    # own timestamp: `commit:` is `pending` here and is filled in by the
    # `post-commit` hook once the commit exists, so deriving the order from it
    # would make the order depend on hashes surviving a history rewrite, which
    # this repo has already had one of.
    stamp = datetime.now().astimezone().replace(microsecond=0)
    return f"""\
---
title: {title}
date: {stamp.isoformat()}
commit: "pending"
tags: []

summary: >
{_SUMMARY_MARKER if summary is None else _folded(summary, "  ")}

# Rows a later item must not re-decide, or the word `none`. Generated into
# docs/SETTLED.md; this is the only thing that writes it. Answering `none` is
# the common case and is a real answer — leaving the marker is not.
settled:{render_settled(settled)}

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


def parse_settled(values: list[str]) -> list[tuple[str, str, str]] | None:
    """`--settled` values as rows, `[]` for `none`, `None` for unanswered.

    Raises:
        ValueError: on a row that is not three columns, or on `none` given
            alongside a row. Both are the author meaning something the file
            cannot say, and guessing which half to keep is how a settled row
            goes missing without anyone seeing it go.
    """
    if not values:
        return None
    if any(value.strip().lower() == "none" for value in values):
        if len(values) > 1:
            raise ValueError("--settled none cannot be combined with rows")
        return []
    rows: list[tuple[str, str, str]] = []
    for value in values:
        columns = [column.strip() for column in value.split(SETTLED_SEP)]
        if len(columns) != 3 or not all(columns):
            raise ValueError(
                f"--settled {value!r}: expected "
                f"what{SETTLED_SEP}where{SETTLED_SEP}do_not_redecide, all three non-empty"
            )
        rows.append((columns[0], columns[1], columns[2]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="short-kebab-name for the filename")
    parser.add_argument("--title", help="entry title; defaults to the slug, de-hyphenated")
    parser.add_argument(
        "--new",
        action="store_true",
        help="there is no docs/todo/ item for this slug; scaffold a fresh entry",
    )
    parser.add_argument("--summary", help="the one sentence; omit to be asked for it by marker")
    parser.add_argument(
        "--settled",
        action="append",
        default=[],
        metavar=f"WHAT{SETTLED_SEP}WHERE{SETTLED_SEP}DO_NOT_REDECIDE",
        help="a settled row, repeatable; or `none`. Omit to be asked for it by marker",
    )
    args = parser.parse_args(argv)

    slug = str(args.slug).strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        print(f"complete_item: {slug!r} is not a kebab-case slug", file=sys.stderr)
        return 1

    try:
        settled = parse_settled(list(args.settled))
    except ValueError as error:
        print(f"complete_item: {error}", file=sys.stderr)
        return 1

    path = COMPLETED / f"{date.today().strftime('%Y.%m.%d')}-{slug}.md"
    if path.exists():
        print(f"complete_item: {path} already exists — not overwriting", file=sys.stderr)
        return 1

    item_path = TODO_DIR / f"{slug}.md"
    if args.new and item_path.exists():
        print(
            f"complete_item: --new says there is no item, but docs/todo/{slug}.md exists",
            file=sys.stderr,
        )
        return 1
    if not args.new and not item_path.exists():
        # The flag has to be worth typing, and the only thing it can buy is
        # this refusal: a mistyped slug used to scaffold a second entry beside
        # the untouched item, and both files then looked deliberate.
        print(
            f"complete_item: no docs/todo/{slug}.md — pass --new if that is deliberate",
            file=sys.stderr,
        )
        return 1
    item_title = ""
    if item_path.exists():
        item_title = _item_title(item_path.read_text(encoding="utf-8"))

    title = str(args.title) if args.title else item_title or slug.replace("-", " ").capitalize()
    added, changed, removed = changed_files(path, item_path)
    summary = str(args.summary) if args.summary else None
    path.write_text(
        render(title, added, changed, removed, summary, settled), encoding="utf-8", newline="\n"
    )
    if item_path.exists():
        item_path.unlink()
        print(f"complete_item: moved docs/todo/{slug}.md")
    shown = _repo_relative(path) or str(path)
    print(checklist(shown, has_summary=summary is not None, has_settled=settled is not None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
