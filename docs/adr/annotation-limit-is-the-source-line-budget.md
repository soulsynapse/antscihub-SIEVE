---
title: The annotation limit is the source line's budget, applied at edit time
adr: 16
position: "03.03"
status: settled
decided: 2026-08-06
---

The annotation limit is the docstring line's own budget — ruff's 100 columns
less the opening `"""`, 97 — and it binds when a line is written or edited
in v3, never at the moment of port.

Why: 72 was never derived from anything. It sat one character above the
median first line of the population it governs — 46 of v2's 124 module
docstrings over, 42 of those between 73 and 78 — and the tree-column claim
behind it was already false of SCAFFOLD.md as rendered. 97 states its origin,
admits every ported summary (the longest is 82), and still refuses the thing
a limit on a derived cell is for: a paragraph. The one-thing-per-module gate
never lived in the character count; it lives in `BANNED_IN_ANNOTATION` and in
review. First-*sentence* extraction was measured and rejected — it changes
nothing for 117 of the 124 and inflates the five wrapped fragments to 112–229
characters, so it makes the collision strictly harder. Port-time enforcement
is excluded because "identical modulo import paths" is a claim a diff can
check, and any per-file exception replaces it with human judgment on 46
files ([declared-means-verified.md](declared-means-verified.md), applied to
the port itself). A ported fragment therefore lands as the fragment it is;
rewriting it afterwards is an ordinary edit to a v3 file, made by an item
that says why, with the v2 blob still in git as what it diverged from.
Census and measurements:
[the finding](../findings/2026.08.06-the-scaffold-annotation-does-not-fit-a-ported-module.md).
