---
title: The source identity has no consumer and no case
priority: normal
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_key.py -q -k source_identity"
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

## The consumers landed, and the cases are owed where the function is

03.5, 03.6 and Phase 5 all arrived, so the condition above is met on the
consumer side and what is left is the cases. They spell `source_identity` and
land in `tests/unit/test_cache_key.py`, beside `source_key`, which is where the
function is: a case reached through a consumer would prove the consumer's use
and leave the three facts as free to move as they are now, and it is the
spelling and not the plumbing that turns a cache over.

What the criterion is for is that each of the three facts moves the string and
nothing else does — a touched mtime, a file that grew, the same bytes at
another path — and that the declared `OSError` for absent footage is raised
rather than a key for a run that cannot happen being built. The two failure
directions in the docstring are argued and not asserted, and they stay that
way: neither an in-place edit preserving size and mtime nor a copy to another
machine is a behaviour a test can require, and pinning what the string is made
of is what makes them visible if either is ever traded away.

Not gated on the resolution of
[whether-an-external-input-carries-a-portable-identity.md](whether-an-external-input-carries-a-portable-identity.md).
That item may replace what the three facts are; this one pins that a change to
them is loud, which is the thing that has to be true first for the replacement
to be a decision rather than a drift.
