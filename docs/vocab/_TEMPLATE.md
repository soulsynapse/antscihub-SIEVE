---
title: the word, lowercase
group: an existing shelf; a new one needs a reason
position: its order along that shelf
gloss: What the word names, at most 40 words. VOCAB.md quotes it verbatim, so it is what a reader sees before deciding to open this file. Names no code.
origin: emergent | decided
defined: YYYY-MM-DD
---

<!--
Copy this, name it for the word, delete these comments.
`uv run python -m checks.vocab` enforces the rest.

An entry gives a part of SIEVE a name. It is not an argument that the name was
the right one — `origin` says that in one field: `emergent` if the tree reached
for the word unprompted, `decided` if someone chose it.

The two sections rot at different rates, which is why they are separate. A
definition must survive a refactor, so it names no code. A concordance is
expected to move, so it is checked: `serve.Ordinals` moved to
`sieve/ordinals.py` and left the paragraph defining *position* reading false.
-->

The gloss, expanded — 150 words at most, and no code. What the word names, what
it is not, and the confusion it resolves; a confusion outlives the code that
caused it. Link a sibling rather than restating its gloss, or the claim gets
read three times and fixed in one.

No measurements, no UI strings, nothing true only this week. Numbers go in
`docs/findings/`, where a later one supersedes them.

## Where it lives

Files and symbols, backticked. The only section that may name code, and every
path and dotted name in it is checked, so a rename fails the commit here
instead of quietly lying. One term per file: a word defined inside another
word's entry cannot be linked, found, or corrected.

<!--
An unsettled term is a different genre. Add `status: unsettled` and `raised:`,
and write `## Senses` and `## Fork` instead: one bolded label per live sense
with the files holding it, then the fork and what it costs either way. The
point is not to pick — it is that the next person to write the word knows they
are picking a side. `surface.md` is the worked example.
-->
