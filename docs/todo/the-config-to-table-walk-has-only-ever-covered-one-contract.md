---
title: The config-to-table walk has only ever covered one contract, and three sources answer to no cell
priority: high
phase: 0
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/docs/test_vision_table.py -q -k config_source_answers_to_a_row"
opened: 2026-08-08
---

# The config-to-table walk has only ever covered one contract, and three sources answer to no cell

`.importlinter` opens by calling itself "the forbidden edge set of VISION.md's
component table, made checkable". That is a claim over the whole file, and every
walk that has tested it walked `opencv-containment` and stopped — 44608be's and
cbb0011's both. Three source lines under the other contracts do not answer to a
cell: `headless` names `sieve.storage`, whose row is "a second output format
before someone asks", and `sieve.tools`, whose row is "a second file per tool;
reaching the runtime", neither of which mentions Qt; and `core-purity` names
`sieve.mutual`, which has no row in the table at all, while the `layers`
contract gives it a layer of its own and a paragraph saying why it is not a
corner of `core`. The other five contracts do agree
(`findings/2026.08.08-vision-never-column-has-two-import-shaped-lines-no-contract-checks.md`,
fourth section, which lists the check for each).

Two halves, and the second is the reason this is `high` rather than a third
round of the same edit. The cells are one commit — the Qt clause into
`storage` and `tools`, and a decision about `mutual`, which is not a missing
clause but a missing row and so is the one place here where the fix might be
Kendrick's rather than the item's: a package with a layer, a rationale and five
refusals, absent from the document that says it enumerates the components. Say
in the commit which way that went, and if the answer is that `mutual`
deliberately has no row, the header sentence is what has to change instead.

The half that stops the recurrence is a test. This is the fourth time a run has
written a universal over this pair of documents from the members it happened to
have open
(`findings/loop/2026.08.07-a-universal-claim-over-an-inherited-list-is-supported-by-the-only-two-members-quoted.md`),
and the correction has each time been another hand-walk that will go stale the
next time a `source_modules` entry lands. The config-to-table direction is the
tractable one: `forbidden_modules` are literal module names, so what a test
needs is a written-down mapping from a module to the phrase a cell uses for it
— `PySide6` to "Qt", `sieve.core.ops` to "`ops/`" — which is precisely the
classification
`findings/2026.08.08-vision-never-column-has-two-import-shaped-lines-no-contract-checks.md`'s
`open_questions` says the table does not currently hold anywhere a parser can
reach. Putting that mapping in the test file rather than in the table is the
cheap version and probably the right one; a mapping that has to gain an entry
before a new forbidden module can land is the gate this wants.

The table-to-config direction is the harder half and is not in scope — an ADR
gate and an import-shaped never read the same in prose, and separating them is
what both walks got wrong. Closing one direction while the other stays prose is
worth stating in the commit so the next reader does not take the green as
covering both.

`done_when` names a file that does not exist, so it exits 4 today. If the item
concludes the walk should stay by hand, the conclusion is the deliverable and
the criterion is what has to change with it, not what gets skipped.
