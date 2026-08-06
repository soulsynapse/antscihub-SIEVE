"""Fill a completion entry's `commit:` with the hash of the commit that made it.

An entry is written before the commit that carries it exists, so
`tools/complete_item.py` writes `commit: "pending"` and step 7 of the work loop
asks for the hash by hand. It is the one step in the loop that *cannot* be done
at the time the rest of the entry is written, and measured over the entries on
disk it is the step most often skipped — `docs/completed-todo/` accumulated
`pending` rows in an index whose whole job is to point at the commit.

So the hash is written by the `post-commit` hook instead, from the one vantage
point where it is knowable and free. This is deliberately *not* a rewrite of
the commit that was just made: amending would change the hash the entry is
being stamped with, and `--amend` under a hook rewrites history a push may
already have shipped. The stamp is a second, additive commit — the same shape
the hand-stamping had.

Why a Python script behind a two-line shim rather than the hook in `sh`: the
value written is derived, and the frontmatter it lands in is YAML whose quoting
is load-bearing (an unquoted all-digit hash parses as an integer, and one with
a leading zero as octal). That is the case the repo's bulk-edit rule names, and
`sed` cannot be tested. `tests/docs/test_stamp_commit.py` can.

Terminating the recursion is the pending check itself: the stamp commit touches
`docs/completed-todo/` too, but nothing in it says `pending` any more, so the
hook it fires bails. `SIEVE_NO_STAMP` is belt to that braces.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import doc_index

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPLETED = "docs/completed-todo/"

#: `commit: "pending"` as `complete_item.render` writes it, tolerating either
#: quoting and any spacing. Anchored to the line so a `pending` inside a summary
#: is not a match.
PENDING = re.compile(r'^commit:[ \t]*(["\']?)pending\1[ \t]*$', re.MULTILINE)

#: The filenames `complete_item` mints. A hand-added file that does not match
#: is left alone rather than guessed at.
ENTRY_NAME = re.compile(r"^\d{4}\.\d{2}\.\d{2}-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.md$")

#: Operations that replay or synthesise commits. `post-commit` fires during
#: some of them (a conflict resolved by hand is a real `git commit`), and a
#: stamp added mid-replay lands on the wrong commit or stops the operation dead.
IN_PROGRESS = (
    "rebase-merge",
    "rebase-apply",
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout


def _lines(*args: str) -> list[str]:
    return [line for line in _git(*args).splitlines() if line.strip()]


def operation_in_progress() -> str | None:
    """Name the multi-commit git operation underway, or `None`.

    Asked through `rev-parse --git-path` rather than by joining onto `.git`,
    which is a *file* in a worktree and a bare path in a submodule.
    """
    for marker in IN_PROGRESS:
        path = _git("rev-parse", "--git-path", marker).strip()
        if path and (REPO_ROOT / path).exists():
            return marker
    return None


def pending_entries(rev: str = "HEAD") -> list[tuple[Path, str]]:
    """`(path, slug)` for every entry touched by `rev` whose `commit:` is pending.

    Scoped to the commit's own diff on purpose: an older entry left unstamped
    describes an older commit, and stamping it with this one would be a
    confident lie. It stays `pending`, which is honest, and a later commit that
    touches it picks it up.
    """
    names = _lines("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", rev)
    found: list[tuple[Path, str]] = []
    for name in names:
        if not name.startswith(COMPLETED):
            continue
        match = ENTRY_NAME.match(name.rsplit("/", 1)[-1])
        if match is None:
            continue
        path = REPO_ROOT / name
        if path.exists() and PENDING.search(path.read_text(encoding="utf-8")):
            found.append((path, str(match["slug"])))
    return found


def stamp(path: Path, short: str) -> bool:
    """Write `short` into `path`'s `commit:`. True if the file changed.

    The hash stays quoted. `0707005` unquoted is YAML octal for 232965, which
    is how the index came to carry integers where hashes belong.
    """
    text = path.read_text(encoding="utf-8")
    stamped, count = PENDING.subn(f'commit: "{short}"', text, count=1)
    if not count:
        return False
    path.write_text(stamped, encoding="utf-8", newline="\n")
    return True


def message(slugs: list[str]) -> str:
    """The subject line, in the shape the hand-written stamps already used.

    A scope names one item; several in one commit have no single owner, so the
    scope is dropped rather than picking the first alphabetically.
    """
    if len(slugs) == 1:
        return f"docs({slugs[0]}): stamp the entry with its commit"
    return f"docs: stamp {len(slugs)} entries with their commits"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be stamped; touch nothing",
    )
    args = parser.parse_args(argv)

    if os.environ.get("SIEVE_NO_STAMP"):
        return 0
    operation = operation_in_progress()
    if operation is not None:
        print(f"stamp_commit: {operation} in progress — not stamping")
        return 0

    entries = pending_entries()
    if not entries:
        return 0

    short = _git("rev-parse", "--short", "HEAD").strip()
    slugs = [slug for _, slug in entries]
    if args.dry_run:
        for slug in slugs:
            print(f"stamp_commit: would stamp {slug} with {short}")
        return 0

    for path, _ in entries:
        if stamp(path, short):
            print(f"stamp_commit: {path.relative_to(REPO_ROOT).as_posix()} -> {short}")

    # The manual stamps touched `.index.md` too: the index carries the hash in
    # a column, so leaving it behind commits a tree the staleness test fails on.
    if doc_index.main([]) != 0:
        print("stamp_commit: doc_index failed — entry stamped, nothing committed", file=sys.stderr)
        return 1

    paths = [path.relative_to(REPO_ROOT).as_posix() for path, _ in entries]
    paths += [gen.relative_to(REPO_ROOT).as_posix() for gen, _ in doc_index.build()]
    # `--only` so a commit staged for other reasons is not swept in; the index
    # files that did not change contribute nothing.
    subprocess.run(
        ["git", "commit", "--only", "--no-verify", "-m", message(slugs), "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        env={**os.environ, "SIEVE_NO_STAMP": "1"},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
