---
title: position
group: Substrate
position: 3
defined: 2026-08-30
---

Which instant a frame is, apart from what it is: the source's own presentation
timestamp, integer ticks in the stream's timebase. A position is a name and
never a count, which is what lets it cross a file, a session or a tool
boundary and still mean one frame — the other half of every key the substrate
holds a frame under, form being the half that says what. Its
partner *ordinal* is the row that position lands on inside one listing, and it
is only ever valid beside the table that produced it.

The pair is what the word buys. `Store` is keyed by position and has no rows
at all; `chunks.fetch` and `proxy.fetch` take an ordinal because a chunk grid
has to be filed somewhere fixed; `fill` sits between them and does the only
conversion, walking ordinals and putting frames away under
`self.positions[ordinal]`. `serve.Ordinals` is the table itself — `rank` maps
one way, `listed` the other — and it holds a snapshot deliberately, because a
grid that renumbered itself when a source grew would file the next chunk over
the last one. Distance is measured in rows there and never in ticks: at 90 kHz
over 23.976 fps a frame is 3753.75 ticks, so a pts difference compared against
a count of frames reads every ordinary step as a jump. The transport shows
both at once — `4,096 / 11,308   pts 15,372,288` — the ordinal because a
human counts frames, the pts because that is the frame's actual name.

Nothing chose this word either. `store.py`, `chunks.py`, `fill.py`, `serve.py`,
`proxy.py` and the transport's `geometry.py` were written apart and all say
position for the durable identity and ordinal for the row, including in the
docstrings that argue about the difference. ADR-0004 settled the identity and
never named it; this file names it. One collision worth knowing about: the
`position` in a note's own frontmatter — this one included — is its order
along a shelf and has nothing to do with a frame. See [form](form.md) for the
other half of the key, and [tier](tier.md), whose
stack is ordered by what it costs to answer for one of these.
