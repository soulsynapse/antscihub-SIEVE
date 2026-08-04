"""Every path a live doc names must still exist.

The audit that produced AUTO-GUARDRAILS §6 found five false claims in the doc
tree and every one of them was in prose, while every machine-checked claim was
correct. This is the cheapest missing member of that family: a document that
points somewhere is checkable without understanding a word of it.

It is not hypothetical. When this was written, `docs/TODO.md` held sixteen bug
bullets and thirteen of them pointed at `docs/todo/*.md` files that had already
moved to `docs/completed-todo/` — a reader following any of them found nothing
and had no way to tell whether the work was done or the file was lost.

**What is checked, and what deliberately is not.** Only the *live* surface:
`CLAUDE.md`, the top-level docs declaring `status: current`, and `docs/todo/`.
A `record` names things that moved — that is what being dated means, and
flagging it would make the report unreadable. A `working` doc is a workbench.
`docs/completed-todo/` and `docs/findings/` are dated the same way; their
frontmatter `files:` lists name deleted paths on purpose, and `doc_drift.py`
already watches them from the other end.

Paths only. A backticked `Dag.order` is a claim too, but the only cheap way
to check one is a substring search over `src/`, which cannot tell a renamed
method from one this repo never defined — a Qt override, a numpy call. That
version was written, reported nothing on its first and only run, and was cut:
a check that cannot fail is not a check.

    uv run python tools/doc_refs.py            # report
    uv run python tools/doc_refs.py --check    # exit 1 on a dangling path
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, cast

from doc_drift import UNSTAMPED, status_of
from doc_index import DOCS_ROOT, parse_frontmatter

REPO_ROOT = DOCS_ROOT.parent

#: A backticked token is a path claim if it has a separator and one of these
#: endings, or is one of the extensionless config files at the root. Anything
#: looser catches prose (`a - b`), and anything tighter misses directories.
PATH_SUFFIXES = (".py", ".md", ".toml", ".yml", ".yaml", ".json", ".lock", ".qmd", ".cfg")
ROOT_FILES = (".importlinter", ".gitignore")

#: Autolinks and image links share this shape; `path_claims` filters by scheme.
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

BACKTICKED = re.compile(r"`([^`\n]+)`")


def body_of(path: Path) -> str:
    """The file below its frontmatter, or the whole file if it has none.

    Frontmatter is skipped because `files:` lists in dated entries name paths
    that were *removed*, and a `removed:` entry pointing at a file that still
    exists would be the bug, not the other way round.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :])
    return text


def live_docs() -> list[Path]:
    docs = [REPO_ROOT / "CLAUDE.md"]
    docs += [
        path
        for path in sorted(DOCS_ROOT.glob("*.md"))
        if path.name not in UNSTAMPED and status_of(path.name) == "current"
    ]
    docs += [p for p in sorted((DOCS_ROOT / "todo").glob("*.md")) if not p.name.startswith("_")]
    return docs


#: A token carrying one of these is a template or a glob, not a claim:
#: `docs/completed-todo/YYYY.MM.DD-<slug>.md`, `docs/*/.index.md`.
PLACEHOLDER = ("<", ">", "*", "YYYY", "{", "}")


def looks_like_a_path(token: str) -> bool:
    """Whether a backticked token is asserting that a *file* exists.

    Directories are excluded on purpose. Most directory mentions in this tree
    are negative or forward-looking — "there is no `src/sieve/docs/`",
    "`workers/` still does not exist", the whole Projected half of
    SCAFFOLD.md — and a checker that cannot read a negation would report all
    of them. A file path is almost always an actual pointer.
    """
    token = token.strip()
    if token in ROOT_FILES:
        return True
    if not token or " " in token or any(mark in token for mark in PLACEHOLDER):
        return False
    return ("/" in token or "\\" in token) and token.endswith(PATH_SUFFIXES)


def path_claims(path: Path) -> list[str]:
    """Repo-relative paths this document asserts exist.

    Three sources: markdown link targets, backticked path-shaped tokens, and
    a todo item's `reads:` list — which is the one a session acts on first,
    since it is literally the instruction for what to open.
    """
    body = body_of(path)
    claims: list[str] = []

    for target in LINK.findall(body):
        target = str(target).split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (path.parent / target).resolve()
        try:
            claims.append(resolved.relative_to(REPO_ROOT).as_posix())
        except ValueError:
            claims.append(target)

    for token in BACKTICKED.findall(body):
        token = str(token).strip().rstrip(".,;:")
        if looks_like_a_path(token):
            claims.append(token.replace("\\", "/"))

    fields = parse_frontmatter(path) if body != path.read_text(encoding="utf-8") else {}
    raw_reads = fields.get("reads")
    if isinstance(raw_reads, list):
        claims += [str(item).strip() for item in cast(Sequence[Any], raw_reads)]

    return claims


#: Prefixes a claim is tried under, in order. The house style writes a module
#: as `core/filter_base.py`, not `src/sieve/core/filter_base.py` — ARCHITECTURE
#: and CLAUDE.md are written that way throughout — so the package root is a
#: legitimate second base rather than a leniency.
BASES = ("", "src/sieve")


def declared_absent() -> set[str]:
    """Paths `docs/SCAFFOLD.md` says do not exist, under Projected or Rejected.

    A doc naming an unbuilt module is not always wrong — an item describing
    the module it will create is the normal shape, and SCAFFOLD's Projected
    half exists to hold exactly those, machine-checked to stay unbuilt. So
    that file is the authority for both halves of the question, and a name
    that reaches this checker without appearing there is the thing worth
    reporting: an item proposing a module the placement doc has never heard
    of.
    """
    text = (DOCS_ROOT / "SCAFFOLD.md").read_text(encoding="utf-8")
    after = text.split("## Projected", 1)[-1]
    names: set[str] = set()
    for line in after.splitlines():
        token = line.split("#", 1)[0].strip()
        if token.endswith(PATH_SUFFIXES):
            names.add(token)
            names.add(token.removeprefix("src/sieve/"))
    for token in BACKTICKED.findall(after):
        token = str(token).strip()
        if looks_like_a_path(token):
            names.add(token)
            names.add(token.removeprefix("src/sieve/"))
    return names


def resolves(claim: str, absent: set[str]) -> bool:
    # `../` leaves the repository — the v1 checkout, which no session and no
    # CI run has. Unverifiable is not the same as wrong.
    if claim.startswith("../") or claim in absent:
        return True
    return any((REPO_ROOT / base / claim).exists() for base in BASES)


def dangling(docs: Iterable[Path]) -> list[tuple[str, str]]:
    absent = declared_absent()
    missing: list[tuple[str, str]] = []
    for doc in docs:
        for claim in path_claims(doc):
            if not resolves(claim, absent):
                missing.append((doc.relative_to(REPO_ROOT).as_posix(), claim))
    return missing


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 on a dangling path")
    args = parser.parse_args(argv)

    docs = live_docs()
    missing = dangling(docs)
    print(f"doc_refs: {len(docs)} live documents")
    for doc, claim in missing:
        print(f"  DANGLING {doc} -> {claim}")
    if not missing:
        print("  every path resolves")

    return 1 if (args.check and missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
