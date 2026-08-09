---
title: A document may name no footage
adr: 26
position: "02.04"
status: settled
decided: 2026-08-09
---

`Project.source` admits `None`: a document with no footage is a valid saved
project, and every reader that needs frames refuses it naming the file,
rather than the schema refusing the state.

Why: the under-construction state is real, and it is the walk the referent
settles — NEW PROJECT mints an empty project and the next act is adding
sources on the card the selection landed on
(`todo/the-library-mints-a-project-and-the-selected-card-opens-its-folder.md`,
where the blocker surfaced). The two ways to avoid admitting it both lie: a
pending row held only in the window vanishes on relaunch while the library
card counts a project the folder does not hold, and a footage dialog at mint
time is the modal the referent argues away and the project-from-folder flow
Phase 7 defers. The cost is borne at the readers — `source_path` and the
sites over it each owe a refusal naming the file — and the reproducible-unit
claim in `Project`'s docstring survives narrowed: reproducibility is a
property of a document that can run, and the refusal is what says this one
cannot yet.
