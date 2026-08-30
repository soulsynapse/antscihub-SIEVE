---
title: position
group: Substrate
position: 3
gloss: Which instant a frame is, apart from what it is — the source's own presentation timestamp, integer ticks in the stream's timebase. A name, never a count.
origin: emergent
defined: 2026-08-30
---

Which instant a frame is, apart from what it is: the source's own presentation
timestamp, integer ticks in the stream's timebase. A position is a name and
never a count, which is what lets it cross a file, a session or a tool boundary
and still mean one frame. See [form](form.md) for the other half of the store's
key, and [ordinal](ordinal.md) for the row it lands on in one listing, which is
the thing it is most often confused with and the only one of the two that can
be counted with.

## Where it lives

`store.py` is keyed by `(position, form)` and holds no rows at all.
`chunks.py` and `proxy.py` fetch by ordinal, because a chunk grid has to be
filed somewhere fixed, and `fill.py` sits between them doing the only
conversion.

ADR-0004 settled this identity and never named it; this file names it. Nothing
chose the word: `store.py`, `chunks.py`, `fill.py`, `serve.py`, `proxy.py` and
the transport's `gui/view/transport/geometry.py` were written apart and all say
position for the durable identity and ordinal for the row, including in the
docstrings that argue about the difference. The transport shows both at once,
the ordinal because a human counts frames and the pts because that is the
frame's actual name.

One collision worth knowing about: the `position` in a note's own frontmatter —
this one included — is its order along a shelf, and has nothing to do with a
frame.
