---
title: The source identity has no consumer and no case
priority: normal
phase: 3
status: open
gated_on: nothing
opened: 2026-08-07
---

# The source identity has no consumer and no case

`cache_key.source_identity` landed with 03.4 because it is the thing
`source_key`'s first argument is built from, and nothing in the tree calls it
and no test covers it. It is three cheap facts about a file — path, size,
mtime — standing in for a content hash, and each of the two ways it can be
wrong is argued in its docstring rather than asserted anywhere: a file edited
in place preserving size and mtime is served stale, and footage copied to
another machine recomputes.

Its consumers arrive: the plan and the executor (03.5, 03.6) build a root key
from it, and `CropRecord.cut_from` is "the parent source's identity at write
time", which is this string. What the item is for is that a run-time file fact
is exactly the kind of thing that goes untested until it is wrong on somebody's
cluster — the mtime is nanoseconds here and seconds on some filesystems, and
`Path.resolve` on Windows returns a spelling that a UNC-mounted copy of the
same footage does not share.

Done when the first consumer lands with cases that pin what the three facts
are, so that a change to the spelling is a test failure rather than a cache
that turns over silently.
