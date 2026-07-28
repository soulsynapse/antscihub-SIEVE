"""Every top-level doc says whether it is supposed to be true now.

`reviewed:`/`subjects:` answers *how far has this drifted*. It does not answer
the prior question — *is this document even claiming current truth* — and that
one was held in CLAUDE.md's prose, in a doc the reader of a stale file may not
have open. A record then reads as an assertion about the code, which is how
`docs/REFINED-VISION.md` gets quoted as a specification three months after it
was superseded.

So the answer moves into the file's own first three lines. `current` is the
only kind that can go stale and the only kind `tools/doc_drift.py` reports;
`record` is dated and never revisited. Files with no claim to make at all —
the generated pair, and the two workbenches — are named in `UNSTAMPED`.
"""

from __future__ import annotations

from doc_drift import DOC_STATUS, UNSTAMPED, current_docs, status_of
from doc_index import DOCS_ROOT


def _top_level() -> list[str]:
    return sorted(p.name for p in DOCS_ROOT.glob("*.md") if p.name not in UNSTAMPED)


def test_every_top_level_doc_declares_a_status() -> None:
    # Without this, adding a doc adds one that drift silently never reports —
    # the failure mode is invisible, which is why it needs a gate rather than
    # the report `doc_drift` otherwise is.
    undeclared = [name for name in _top_level() if not status_of(name)]
    assert not undeclared, "docs/*.md with no `status:` in frontmatter: " + ", ".join(undeclared)


def test_every_status_is_in_the_vocabulary() -> None:
    bad = [(name, status_of(name)) for name in _top_level() if status_of(name) not in DOC_STATUS]
    assert not bad, f"status must be one of {DOC_STATUS}: {bad}"


def test_the_dated_records_are_marked_as_records() -> None:
    # CLAUDE.md names these four as superseded-never-edited. They are the
    # documents most likely to be read as current, being the longest and the
    # most specification-shaped.
    records = {"VISION.md", "REFINED-VISION.md", "SIEVE-HANDOFF.md", "filter-tab-parity-plan.md"}
    mislabelled = {name for name in records if status_of(name) != "record"}
    assert not mislabelled, f"dated records not marked `status: record`: {sorted(mislabelled)}"
    assert not (records & set(current_docs())), "a record is being drift-reported as current"
