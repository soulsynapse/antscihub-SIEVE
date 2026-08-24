"""What every route promises, and the one number that decides how it answers.

A route is the narrowest useful thing: **give me the image at this row, give me
the image at the nearest keyframe at or before this row, and tell me where you
are parked.** Three methods and a form. Everything above the decoder is written
against this and nothing else, which is what makes a fill order, a tier choice
or an eviction rule checkable without a video file existing
(`sieve.decode.fake`).

**A route delivers the source form and no other.** The whole frame, at source
sampling, in one pixel format — and then `sieve.frame.form.derive` produces
whatever was actually wanted. Cropping or scaling inside the route would tie one
decode to one consumer, and the reason to hold a frame at all is that several
consumers want different pictures of the same instant.

The pixel format is the exception, and it is not an inconsistency. Luma is a
strided view of a plane the decoder already wrote; colour is a swscale pass with
setup billed per call
(`docs/findings/2026.08.21-pyav-to-ndarray-pays-sws-setup-per-call.md`). One is
free at decode time and unrecoverable afterwards — nothing reconstructs chroma
from grey — so it is chosen when the route is built and named in the form the
route reports. Dropping colour later is cheap and stays `form`'s business.

**Absent is an answer.** A row present in the frame table can still yield no
image: this tree's footage was cut mid-GOP and its leading packets decode to
nothing, which is the half of ADR-0004's three-different-counts that a
demux-only pass cannot see. `at` returns `None` there rather than the next image
along, because the next image along is a different frame and a caller that gets
one silently files it under the timestamp it asked for.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from sieve.frame.form import Form

#: How far ahead a route steps rather than seeks. Measured as the crossover on
#: the uncut source — a seek costs about a GOP replayed and a stepped frame
#: costs one decode, so the two meet around here
#: (`experiments/decode-experiments/results/02-random-access-*.json`). It is one
#: machine's crossover on one file shape and is therefore a default rather than
#: a fact: a route takes its own, and probing it belongs with the seek race the
#: moment anything is felt to be wrong with it.
STEP_WITHIN = 60


class Route(Protocol):
    """One open decoder on one file, addressed in rows."""

    #: What `at` and `keyframe_at` return: the whole frame, at source sampling,
    #: in this route's pixel format. Every other form derives from it.
    form: Form

    #: The row the decoder is parked on, or -1 before anything is decoded.
    #: Read by a caller deciding whether a request is a step or a jump; a route
    #: never asks anyone where it should be.
    pos: int

    def at(self, row: int) -> tuple[np.ndarray, str] | None:
        """The image at exactly this row, or `None` if it has none.

        The label says how the answer was reached — stepped, seeked, which side
        of a hybrid — and exists for the ledger rather than for logic. Nothing
        branches on it.
        """
        ...

    def keyframe_at(self, row: int) -> tuple[np.ndarray, int, str] | None:
        """One decode at the keyframe at or before `row`, and where it landed.

        No roll-forward: this is the cheap answer a scrub takes while the exact
        one is still arriving. `landed` is a real row and usually sits at or
        before what was asked — except at the head of a cut file, where the
        keyframe before the request decodes to nothing and the first real image
        is *after* it. A caller that assumed the first case gets the second
        eventually.
        """
        ...

    def close(self) -> None:
        ...
