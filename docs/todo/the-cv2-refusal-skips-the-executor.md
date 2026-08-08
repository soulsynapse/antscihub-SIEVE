---
title: The cv2 refusal skips the executor, and three of its sources answer to no row
priority: high
phase: 0
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_contract_lines_go_red.py -q -k opencv-containment__sieve_pipeline_imports_cv2"
opened: 2026-08-08
---

# The cv2 refusal skips the executor, and three of its sources answer to no row

`opencv-containment` refuses `cv2` to `core`, `bench`, `gui`, `cli` and — since
44608be — `session`. It does not refuse it to `sieve.pipeline`, and no other
contract does either: `headless` names the package against `PySide6`,
`pipeline-computes-nothing` against `sieve.core.ops`. Planting `import cv2`
under each package and running `lint-imports` on the real tree separates them in
one command — `sieve.session._probe_cv2` exits 1 naming the contract,
`sieve.pipeline._probe_cv2` leaves all eight KEPT.

The rationale the contract states is "no second module learning to drive
`VideoCapture` itself, which is how decoder identity stops being one string and
cache keys stop meaning anything". `pipeline` owns the cache keys and the one
executor. Whatever weight that argument has for the front ends and for the
document layer, it is heaviest here, so the gap wants closing rather than
justifying — but if the item concludes otherwise, the conclusion is the
deliverable and the criterion below is what has to change with it, not what gets
skipped.

The second half is one edit away and belongs in the same commit. `.importlinter`
opens by calling itself "the forbidden edge set of VISION.md's component table,
made checkable", and three of the contract's sources have no cv2 clause in their
row: `bench` since Phase 0, `session` since 44608be, and `pipeline` the day this
item lands. The table is the stated source and the config is a strict superset
of it, in a direction neither previous walk looked
(`findings/2026.08.08-vision-never-column-has-two-import-shaped-lines-no-contract-checks.md`,
dated section). Either the cells gain the clause — `bench`'s and `pipeline`'s
rows are silent about codecs entirely, `session`'s says "computing anything" —
or the header stops claiming an equality the file does not keep. Say which in
the commit; the header is the sentence the next walker takes as the rule.

Editing `docs/VISION.md` is editing the binding target, and the clauses here
record refusals the config already enforces rather than proposing new ones. If
the item finds itself arguing for a refusal the table does not imply, that is
Kendrick's, not the item's.

`done_when` is the generated case, which is why it is not green today: the case
is read out of `.importlinter`, so `-k` selects nothing until the source lands
and `pytest` exits 5. It covers the executor half only. The table half is prose
and the review checks it — the same asymmetry
`findings/loop/2026.08.07-a-universal-claim-over-an-inherited-list-is-supported-by-the-only-two-members-quoted.md`
names in its second section, stated here so the green is not read as covering
both.
