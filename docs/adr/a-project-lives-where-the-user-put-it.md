---
title: A project lives where the user put it, and the library remembers
adr: 35
position: "02.05"
status: settled
decided: 2026-08-09
---

A project file's location is the user's, chosen when it is minted, and no
directory is the library: the library is the list of locations the app has
been shown, held as per-user state.

Why: the folder was a stand-in that said so. `library_root` answers with a
`projects/` under the launch directory, and
`todo/a-mint-lands-wherever-the-app-was-launched.md` pinned that as a default
"for now" on its own statement that it was not a ruling that a library is a
folder relative to the launch directory forever. This is what supersedes it,
and it supersedes more than the default: a scan can hold only what a folder
holds, so two folders would be two libraries, and pinning a project stays
per-user state a scanned folder has nowhere to put
(`todo/pinning-a-project-is-state-the-library-has-nowhere-to-put.md`). A list
has somewhere for both. The referent had already assumed one — its ✕ takes a
project out of the library with the folder untouched
([MOCKUP-MAP.md](../MOCKUP-MAP.md)), which under a scan cannot be done without
moving the file.

**The mint asks, and that is arithmetic rather than taste.**
[a-document-names-footage-only-through-a-tool](a-document-names-footage-only-through-a-tool.md)
stores a source's path relative to the project file's directory, so a document
with no location has nothing for its footage to be relative to. Deferring the
question means holding that param absolute until the first save and rewriting
it there — two representations of one field depending on whether the document
has landed yet, which is the second answer that ADR removes one layer up. The
picker is what keeps the schema's single representation reachable at every
point in a document's life.

Its cost is a modal on the one gesture the referent deliberately has none on,
which [a-position-is-asked-for-in-the-chain](a-position-is-asked-for-in-the-chain.md)
makes a revision of the surface rather than a cleanup. Taken deliberately and
landed in `mockup/mockup.py` in the same breath as this: the referent's NEW
PROJECT was drawn while a folder existed to land in for free, and it is that
folder this removes. The compensation is that nothing defaults anywhere, which
is what closes the stray mint the item above recorded twice in two days from a
clean tree — a default location is the only thing that can produce one.

Where the remembered list is stored is not decided here. v3 holds no per-user
state at all today, and the first thing that needs it decides its home; the
pinning item above is the other claimant and should land with it rather than
beside it.
