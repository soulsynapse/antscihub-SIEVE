---
title: The decision as a sentence fragment
adr: 0
position: "01.01"
status: settled
decided: 2026-08-06
---

The decision itself, in one or two sentences — this paragraph is the
ARCHITECTURE.md index line, so it states what binds, not why.

Why: the rationale, kept short. What the obvious alternative was and what it
costs. Link the finding, contract, or v2 file that is the evidence rather
than restating it.

---

## How to use this file

Copy to `docs/adr/<slug>.md`, delete this section, fill it in. Then run
`uv run python scripts/doc_index.py`; do not edit `ARCHITECTURE.md` by hand —
`tests/docs/test_doc_index.py` fails when it is stale.

A title naming the thing it decides about — ``title: `core`'s membership is
closed`` — has to be quoted whole, or led with a word. YAML reserves an opening
backtick (and an opening quote), so an unquoted one is not a doc_index rule
being broken but a file that stopped being YAML, and the error says so in terms
of a character rather than of this field.

`adr:` is identity: highest existing number plus one, minted once, never
reused — the gate refuses a duplicate. `position:` is placement only: dotted
two-digit pairs whose first pair names a `_GROUPS.md` group and each further
pair indents one level. Rearranging the shelf edits positions freely;
identity never moves.

An ADR is minted when a decision outlives the text that made it — a completed
plan phase, a commit message — and the older home is cut to a link in the
same commit. A claim a contract or test already checks is cited, not minted.

To supersede: the successor is a new ADR; the old file keeps `adr:` and its
text, sets `status: superseded` and `superseded_by: <slug>`, and drops
`position` — surrendering the position is what removes it from the index.
