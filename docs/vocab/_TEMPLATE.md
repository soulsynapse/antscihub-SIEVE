---
title: the word, lowercase
group: an existing shelf; a new one needs a reason
position: its order along that shelf
gloss: What the word names, at most 40 words. Harvested verbatim into VOCAB.md, so it is what a reader sees before deciding to open this file. Names no code.
origin: emergent | decided
defined: YYYY-MM-DD
---

<!--
Copy this file, name it for the word, delete these comments.
`uv run python -m checks.vocab` is what enforces the rest.

An entry exists to make a name usable by someone else. It is not an argument
that the word was the right choice: that is what `origin` says, in one field.
`emergent` means the tree reached for the word unprompted and this file
records it; `decided` means someone chose it.

The layers below rot at different rates, which is the whole reason they are
separate. The definition has to survive a refactor, so it names no code. The
concordance is expected to move, so it is checked. A citation in the
definition is the failure this shape exists to prevent — `serve.Ordinals`
moved to `sieve/ordinals.py` and left the paragraph defining *position*
reading false.
-->

The gloss, expanded to at most 150 words total. What the word names, what it
is not, and the confusion it resolves — a confusion outlives the code that
caused it, which is why it belongs here and not below. Link a sibling term
rather than restating its gloss; the index prints both, and a claim made in
three files is read three times and fixed in one.

Don't write down a measurement, a UI string, or anything else that is true
this week. A finding under `docs/findings/` is where a number goes, because a
later one can supersede it there.

## Where it lives

The files and symbols, backticked. This is the only section that may name
code, and every path and dotted name in it is checked, so a rename fails the
commit here instead of quietly lying. One term per file: a word defined inside
another word's entry cannot be linked, found, or corrected.

<!--
An unsettled term is a different genre and the check knows it. Add
`status: unsettled` and `raised:`, and write `## Senses` and `## Fork`
instead of `## Where it lives`: one bolded label per live sense with the
files that hold it, then what the fork is and what it would cost either way.
The point is not to pick — it is that the next person to write the word knows
they are picking a side. `surface.md` is the worked example.
-->
