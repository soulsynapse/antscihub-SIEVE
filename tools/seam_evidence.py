"""Where inside one file did each commit's surviving lines land.

CLAUDE.md's co-change check is pairwise between *files*: it asks whether two
modules that already exist change together, and it answers whether a seam that
was already cut held. It has nothing to say about a file that has never been
split, which is the case every time the question is actually live.
`docs/todo/filter-tab-many-secrets.md` says so in as many words -- "there is
one file and no candidate split already exists to measure".

The substitute is blame bucketed by the file's own `# ---- ` section markers.
A section whose lines were put there by commits that touched almost nothing
else in the file is a place where history has already been behaving as if the
seam existed. That reading is what reordered
`docs/todo/filter-tab-is-eleven-jobs.md` on 2026-08-05: the source boundary at
85-92% went to the top of the list and the composite at 66% was struck, and
both numbers came out of doing this by hand.

**What the number is, exactly.** For one commit: of its lines still present in
the working-tree file, the fraction sitting in whichever single section holds
most of them. High means confined. It is not "how much of the section this
commit wrote" -- that is the second table.

**Three things it cannot see, all of which the reader has to supply.**

1. Blame is of the file as it is now, and so are the section boundaries. A
   commit that predates a marker is bucketed by today's outline, not the one
   it was written against. That is the useful direction (where does its work
   live now) but it is not a claim about intent at the time.
2. Only surviving lines exist here. A commit whose work was later rewritten
   shrinks toward zero and drops out; the report prints what it dropped.
3. An initial assembly commit and a rollback both land everywhere at once and
   score near the file's own section distribution. They are not evidence of
   anything and must be discounted by hand -- which is why the date and the
   share-of-file column are printed next to every row.

Deliberately not a gate, and not wired into nox. There is no threshold at
which a number here is a defect: it is one input to a judgement about where to
cut a file, and `filter-tab-is-eleven-jobs`' seam test -- name the signals that
cross -- is the one that can actually say no.

    uv run python tools/seam_evidence.py src/sieve/gui/filter_tab.py

Prints a markdown block to paste into the `docs/todo/` item making the
argument. Paste the whole thing, including the provenance line; a percentage
with no file, no date, and no command behind it is the kind of number this
repo makes a point of not writing down.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The trailing rule of dashes is optional: what makes a marker is `# ---` and
# a name, which is the shape every section in `src/sieve/` is written in. The
# name must start with something that is not a dash, or a bare `# --------`
# divider matches with a name of "-" and splits the section above it in two.
SECTION_RE = re.compile(r"^\s*#\s*-{3,}\s*([^\s-].*?)\s*-*\s*$")

PREAMBLE = "(above the first marker)"


@dataclass
class Commit:
    sha: str
    summary: str
    date: str
    sections: Counter[str] = field(default_factory=Counter[str])

    @property
    def lines(self) -> int:
        return sum(self.sections.values())

    def top(self) -> tuple[str, int]:
        # `most_common` breaks ties by insertion order, which is file order
        # here -- an arbitrary but stable choice for a commit split evenly.
        (name, count), *_ = self.sections.most_common(1)
        return name, count


def sections_of(text: str) -> list[str]:
    """One section name per line of the file, in line order."""
    current = PREAMBLE
    names: list[str] = []
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if match:
            current = match.group(1)
        names.append(current)
    return names


def blame(path: Path) -> list[tuple[str, str, str]]:
    """One `(sha, summary, date)` per line of the working-tree file.

    No `-M`/`-C`. Movement detection would credit a line to the commit that
    first wrote it elsewhere, and the question here is which commit put it
    *in this section*, which is exactly what a move is.
    """
    out = subprocess.run(
        ["git", "blame", "--line-porcelain", "--", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    ).stdout

    lines: list[tuple[str, str, str]] = []
    sha = summary = date = ""
    header = re.compile(r"^([0-9a-f]{40}) \d+ \d+")
    for raw in out.splitlines():
        if header.match(raw):
            sha = raw[:40]
        elif raw.startswith("summary "):
            summary = raw.removeprefix("summary ").strip()
        elif raw.startswith("author-time "):
            date = raw.removeprefix("author-time ").strip()
        elif raw.startswith("\t"):
            lines.append((sha, summary, date))
    return lines


def iso_day(author_time: str) -> str:
    try:
        stamp = int(author_time)
    except ValueError:
        return "--"
    return datetime.fromtimestamp(stamp, UTC).date().isoformat()


def collect(path: Path) -> tuple[dict[str, Commit], list[str], Counter[str]]:
    text = path.read_text(encoding="utf-8")
    names = sections_of(text)
    blamed = blame(path)
    if len(blamed) != len(names):
        raise SystemExit(
            f"seam_evidence: blame returned {len(blamed)} lines for a "
            f"{len(names)}-line file -- is the working tree mid-merge?"
        )

    commits: dict[str, Commit] = {}
    per_section: Counter[str] = Counter()
    for name, (sha, summary, date) in zip(names, blamed, strict=True):
        commit = commits.setdefault(sha, Commit(sha, summary, iso_day(date)))
        commit.sections[name] += 1
        per_section[name] += 1

    # Section order is file order; a section every commit rewrote still has to
    # appear in the second table where the reader expects it.
    ordered = list(dict.fromkeys(names))
    return commits, ordered, per_section


def truncate(text: str, width: int) -> str:
    # ASCII only: this is printed to a Windows console under cp1252 and then
    # copied out of it, and a mojibake ellipsis would ride into the item.
    return text if len(text) <= width else text[: width - 3] + "..."


def report(path: Path, min_lines: int, confined: float) -> str:
    commits, ordered, per_section = collect(path)
    total = sum(per_section.values())
    rel = path.relative_to(REPO_ROOT).as_posix() if path.is_absolute() else path.as_posix()

    ranked = sorted(commits.values(), key=lambda c: (-c.lines, c.date))
    shown = [c for c in ranked if c.lines >= min_lines]
    dropped = [c for c in ranked if c.lines < min_lines]

    out: list[str] = []
    if ordered == [PREAMBLE]:
        # Every share is 100% of one bucket. Saying so beats printing a table
        # of hundreds that reads like concentration.
        out.append(
            f"`{rel}` has no `# ---- ` section markers, so there is one bucket "
            f"and every share below is 100% by construction. Nothing here is "
            f"evidence about a seam until the file states its own sections."
        )
        out.append("")
    out.append(
        f"**Blame by section** -- `{rel}`, {total} lines, "
        f"{len(ordered)} section{'' if len(ordered) == 1 else 's'}, "
        f"{len(commits)} commits with a surviving line. "
        f"`uv run python tools/seam_evidence.py {rel}`. Per commit: lines still "
        f"in the file, and the share of them inside whichever one section holds "
        f"most. Blame and the section boundaries are both of the file as it is "
        f"now, so a commit older than a marker is bucketed by today's outline."
    )
    out.append("")
    out.append("| commit | date | lines | % of file | largest section | share |")
    out.append("|---|---|---:|---:|---|---:|")
    for commit in shown:
        name, count = commit.top()
        out.append(
            f"| {truncate(commit.summary, 56)} | {commit.date} | {commit.lines} "
            f"| {commit.lines / total:.0%} | {truncate(name, 42)} "
            f"| {count / commit.lines:.0%} |"
        )
    if dropped:
        out.append("")
        out.append(
            f"{len(dropped)} commits under {min_lines} surviving lines "
            f"({sum(c.lines for c in dropped)} lines, "
            f"{sum(c.lines for c in dropped) / total:.0%} of the file) are not "
            f"listed: a share out of three lines is not a measurement."
        )

    out.append("")
    out.append(
        f"**Read the other way** -- per section, the commits that put "
        f"{confined:.0%} or more of their surviving lines inside it. A section "
        f"with several is one history has been treating as separable; a section "
        f"whose lines all arrived from commits that were doing something else "
        f"is not."
    )
    out.append("")
    out.append("| section | lines | commits | confined commits |")
    out.append("|---|---:|---:|---|")
    for name in ordered:
        touching = [c for c in ranked if c.sections[name]]
        inside = [
            c for c in touching if c.lines >= min_lines and c.sections[name] / c.lines >= confined
        ]
        listed = (
            ", ".join(
                f"{truncate(c.summary, 40)} ({c.sections[name] / c.lines:.0%})"
                for c in sorted(inside, key=lambda c: -c.sections[name])
            )
            or "--"
        )
        out.append(f"| {truncate(name, 42)} | {per_section[name]} | {len(touching)} | {listed} |")

    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="the file to bucket")
    parser.add_argument(
        "--min-lines",
        type=int,
        default=8,
        help="omit commits with fewer surviving lines than this (default: 8)",
    )
    parser.add_argument(
        "--confined",
        type=float,
        default=0.8,
        help="share at which a commit counts as confined to one section (default: 0.8)",
    )
    args = parser.parse_args(argv)

    path: Path = args.path if args.path.is_absolute() else REPO_ROOT / args.path
    if not path.is_file():
        raise SystemExit(f"seam_evidence: no such file: {args.path}")

    print(report(path, args.min_lines, args.confined))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
