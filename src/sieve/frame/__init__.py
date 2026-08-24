"""What a frame is, and what a stored frame is.

The layer everything else in the substrate is addressed in. Two questions live
here and nothing above answers either of them for itself: *which frame* — a
presentation timestamp in the stream's own timebase, with the rows that index it
derived from a table built by demuxing (ADR-0004) — and *which pixels of it, at
what sampling, in what format* (`form`).

Both are here rather than beside the decoder because neither is about decoding.
A table is built without decoding a single frame; a form is a description that
exists before any pixels do, and is what a store is keyed by, what a series says
it is about, and what a route is asked to produce. Putting them under the
decoder would make every consumer that never decodes anything import one.

Nothing in this package opens a decoder, holds a lock, starts a thread, or
imports Qt. `shape` and `table` read a container's headers and packets; `form`
touches no file at all.
"""

from __future__ import annotations

from sieve.frame.form import (
    APPROX,
    EXACT,
    Form,
    build,
    derive,
    grade,
    shortfall,
    source_form,
)
from sieve.frame.shape import Shape
from sieve.frame.table import FrameTable, rescale

__all__ = [
    "APPROX",
    "EXACT",
    "Form",
    "FrameTable",
    "Shape",
    "build",
    "derive",
    "grade",
    "rescale",
    "shortfall",
    "source_form",
]
