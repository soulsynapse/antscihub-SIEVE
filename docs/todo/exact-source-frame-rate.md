---
title: The source's frame rate is exact, and float fps has one home
status: open
opened: 2026-08-04T22:09:46-07:00
priority: high
gated_on: nothing structurally
reads: [src/sieve/decode/reader.py, src/sieve/core/types.py, src/sieve/core/clip_window.py]
after: [four-numbers-four-types]
---

# The source's frame rate is exact, and float fps has one home

`MediaTime` landed 2026-08-04 with no producer, and this is why: the only frame
rate the system has is `VideoMetadata.fps: float`, read from `cv2.CAP_PROP_FPS`
in `decode/reader.py:_read_metadata`. A media time founded on it is a
`Fraction` wrapping a binary approximation, which is the drift the type was
introduced to refuse, spelled more expensively.

The failure is not cumulative and it is not small. Every media time is
eventually floored back onto the frame grid, and at 30000/1001 the float
product lands just under the integer: fifteen frames converted to seconds and
back is fourteen. First failure at frame 15, one whole frame, in the first
second of footage — the arithmetic is in `tests/unit/test_quantities.py` and
the argument is in `core/types.py`'s module docstring. Today that error is
reachable from `detect/tables.py`, whose `start_seconds` / `end_seconds` /
`duration_seconds` columns are `frame / fps` and are the CSV somebody takes
into R.

**The decision this item exists to make.** OpenCV cannot answer it:
`CAP_PROP_FPS` is a double and the container's rational is already gone by the
time it returns. Two ways out:

- **Probe with PyAV**, already a base dependency (`av>=13`, for the FFV1 crop
  writer). `stream.average_rate` is a `Fraction` straight from the container.
  Recommended. It reads metadata, not frames — every decoded pixel still comes
  from OpenCV's `VideoReader`, so pyproject's "this does not become a second
  decoder identity" comment stays true, and this item should say so where a
  later reader will meet it.
- **Recover it** with `Fraction(value).limit_denominator(...)`. Cheaper, and
  right for the NTSC family by luck rather than by construction: it is a guess
  that is silently wrong for any rate whose denominator exceeds the limit, and
  a guess that is usually right is the worst kind of number to found a
  published timestamp on.

Done looks like: `VideoMetadata.fps` is a `Fraction`, `timestamp_of` and
`duration_seconds` return `MediaTime`, `clip_window.default_window` computes
its ten seconds through `FrameCount.spanning` rather than
`round(seconds * fps)`, and the seconds columns in `detect/tables.py` are
founded on the exact rate. `fps <= 0` — a container that reports nothing —
stays the honest refusal it already is in both of `clip_window`'s functions.

**Not in scope, and not a deferral: the three filters' `fps` params stay
`float`.** `block_signal`, `motion_history` and `temporal_baseline` each carry
one, and a params field is hashed into `canonical_json`. Retyping it re-keys
every cached entry those filters ever produced, for no gain — the kernel wants
a number to multiply a window by, not a timebase. What the item *must* check is
that the conversion is a no-op in the other direction: the GUI writes
`params.fps` from the metadata, so `float(Fraction(30000, 1001))` has to be the
same double `float(cv2.CAP_PROP_FPS)` produces today, or the same re-key
happens by accident. One test, one assertion, and it is the only place these
two representations are allowed to meet.

The check that would fail if it regressed: a metadata-level version of the
frame-15 test — an exact 30000/1001 source, `timestamp_of(15)` converted back
through `FrameCount.spanning`, equal to `FrameCount(15)` — plus the params
round-trip above.
