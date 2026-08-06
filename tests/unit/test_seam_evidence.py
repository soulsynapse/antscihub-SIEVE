"""The bucketing has to be a partition, or every percentage it prints is wrong.

`tools/seam_evidence.py` is not a gate and nothing fails when its numbers
drift. What it does do is put percentages into `docs/todo/` items that then
get read as measurements — the source-boundary extraction was ordered ahead of
the composite on the strength of 82/92% against 66% — so the two things worth
pinning are that every line lands in exactly one section and that a marker is
recognised in the shapes this repo actually writes.
"""

from __future__ import annotations

from pathlib import Path

from seam_evidence import PREAMBLE, collect, sections_of

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_a_line_belongs_to_the_marker_above_it() -> None:
    names = sections_of(
        "\n".join(
            [
                "import os",  # preamble
                "class C:",  # preamble
                "    # ---- construction ------------------",
                "    def __init__(self): ...",
                "# ---- module level",  # no trailing rule, still a marker
                "def helper(): ...",
            ]
        )
    )
    assert names == [
        PREAMBLE,
        PREAMBLE,
        "construction",  # the marker line belongs to the section it opens
        "construction",
        "module level",
        "module level",
    ]


def test_a_bare_rule_is_not_a_section() -> None:
    # Nothing to name means nothing to attribute lines to; a divider used as
    # visual whitespace must not silently split the section above it.
    assert sections_of("# ----------------\nx = 1") == [PREAMBLE, PREAMBLE]


def test_every_line_is_counted_once() -> None:
    # The failure this catches is blame and the file disagreeing on line count
    # after some flag change — which would not raise, it would just shift every
    # attribution down by one.
    path = REPO_ROOT / "src" / "sieve" / "gui" / "filter_tab.py"
    commits, ordered, per_section = collect(path)

    lines = len(path.read_text(encoding="utf-8").splitlines())
    assert sum(per_section.values()) == lines
    assert sum(c.lines for c in commits.values()) == lines
    assert set(ordered) == set(per_section)
    assert all(0 < c.top()[1] <= c.lines for c in commits.values())
