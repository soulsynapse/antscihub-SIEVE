"""A live doc that points somewhere must point at something.

The doc audit that produced AUTO-GUARDRAILS §6 found five false claims and
every one of them was prose; every machine-checked claim was correct. A
pointer is the cheapest prose claim to check, and it rots on a schedule the
repo sets for itself — `tools/complete_item.py` *moves* an item file on
completion, so every link into it dangles the moment the work finishes.

That is not a hypothetical: when this was written, thirteen of `TODO.md`'s
sixteen bug bullets pointed at `docs/todo/*.md` files that had already moved,
and four more links into `todo/ledger-producers.md` were dangling in
ASPIRATIONS, WORKING-BACKWARDS, and an open item.
"""

from __future__ import annotations

from pathlib import Path

from doc_refs import dangling, declared_absent, live_docs, looks_like_a_path, resolves


def test_no_live_doc_points_at_a_file_that_does_not_exist() -> None:
    missing = dangling(live_docs())
    assert not missing, "dangling paths:\n" + "\n".join(f"  {d} -> {c}" for d, c in missing)


def test_the_live_set_is_the_live_set() -> None:
    # If this ever returns only CLAUDE.md the suite above passes vacuously,
    # which is the failure mode a link checker dies of.
    names = {path.name for path in live_docs()}
    assert "CLAUDE.md" in names
    assert "ARCHITECTURE.md" in names
    assert len(names) > 20, names
    # Records name things that moved — that is what dated means — so they must
    # stay out or the report is unreadable.
    assert "REFINED-VISION.md" not in names
    assert "SIEVE-HANDOFF.md" not in names


def test_a_projected_module_is_not_a_dangling_link() -> None:
    # SCAFFOLD.md's Projected half is machine-checked to *not* exist, so an
    # item naming the module it will create is correct rather than broken —
    # but only while SCAFFOLD knows about it.
    absent = declared_absent()
    assert "storage/zarr_store.py" in absent
    assert resolves("storage/zarr_store.py", absent)
    assert not Path("src/sieve/storage/zarr_store.py").exists()
    assert not resolves("storage/never_proposed_by_anyone.py", absent)


def test_templates_and_globs_are_not_read_as_claims() -> None:
    assert not looks_like_a_path("docs/completed-todo/YYYY.MM.DD-<slug>.md")
    assert not looks_like_a_path("docs/*/.index.md")
    assert not looks_like_a_path("core/")  # a directory, usually a negation
    assert looks_like_a_path("src/sieve/core/types.py")
