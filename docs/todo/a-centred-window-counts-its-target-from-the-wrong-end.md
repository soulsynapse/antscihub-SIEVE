---
title: A centred window counts its target from the wrong end
priority: normal
phase: 3
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_executor.py -q -k span_target && uv run pytest tests/unit/test_types.py tests/unit/test_executor.py -q"
opened: 2026-08-07
---

# A centred window counts its target from the wrong end

`FrameSpan.target` is `frames[-1]`, which was the whole truth while every window
trailed. 03.6 hands a tool declaring `lookahead_frames` a window whose last `k`
frames are *past* the frame it must answer for, so the target is
`window[len(window) - 1 - k]` and `target` is a frame the tool must not emit for.
The executor checks the index that comes back and refuses the mistake by name
(`test_a_lookahead_tool_that_answers_for_the_end_of_its_window_is_refused`), so
it is loud rather than silent — but it is a trap set for every centred tool that
will ever be written, and the accessor whose name says "this is your frame" is
the one that lies.

There is a second cost, and it is the one that decides how urgent this is. To
count back, a tool needs its own `k`, and the honest source of that number is
`node_lookahead_frames((spec, params))` — which prefers the *refinement* over the
bound. A tool declaring only `max_lookahead_frames` gets `NO_FRAMES` back from
`params.lookahead_frames()` and would count back zero, landing on `target` again.
`tests/unit/test_executor.py`'s windowed fixtures declare both, one number
written twice, which is the workaround rather than the contract.

The obvious fix is `FrameSpan` carrying which of its frames is the target, and
that is why this is an item rather than a line in 03.6: `core/types.py` is 01.1's
copy-verbatim anchor and the span is v2's, so widening it is a decision about
that file. Two shapes are worth weighing against each other — a target index on
the span, set by whoever built it, or a `FrameSpan.centred_on` constructor that
makes `target` mean the emitted frame for both window shapes — and the second
keeps every existing reader of `target` correct without knowing a window has two
sides.

04.8's centred detector is the first tool that meets this. It should not be the
thing that decides it.

Nor should this item decide the anchor's terms alone.
[a-frame-count-does-not-enforce-its-own-int.md](a-frame-count-does-not-enforce-its-own-int.md)
stops at the same wall over `FrameCount.__post_init__` and is phase 1, so it
drains first and is where "how far does 01.1's copy-verbatim survive" gets
answered. Read what it settled before weighing the two shapes above; if it
ruled that the anchor holds and guards live at the declaration boundaries, then
the `FrameSpan.centred_on` constructor is refused with it and what is left here
is a target index carried by whoever builds the span.

## The fallback did not fire, and the criterion is neutral between the shapes

That item landed the guard in `FrameCount.__post_init__`, so the anchor admits
what a change's own subject argues for and `FrameSpan.centred_on` is not refused
— both shapes above are live and this item weighs them on their merits. What it
may not do is add a constructor as a convenience beside other work; the change
has to be this item's subject.

The cases spell `span_target` and land in `tests/unit/test_executor.py`, which
is where either shape is observable: a windowed tool declaring
`lookahead_frames` reads the frame it must emit for off the span it was handed —
not by counting `k` back from the end — and is not the mistake
`test_a_lookahead_tool_that_answers_for_the_end_of_its_window_is_refused` names,
while a trailing tool's target is still its last frame. They cannot land in
`tests/unit/test_types.py`: that is 01.1's ported spec and the porting
discipline refuses rewriting one, which is why the file that owns `FrameSpan`
is the one file that may not carry the case for it. The second leg runs that
ported spec beside the executor's, because a target index on the span is the
branch that could land green while quietly moving what 01.1 froze.

The fixture that declares its lookahead twice — the workaround the body names —
is not in the criterion, because whether it collapses depends on which shape
wins: a span that carries its target leaves the tool nothing to count with, and
`node_lookahead_frames`' preference for the refinement stops being anything the
tool reads.
