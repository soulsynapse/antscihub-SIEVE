"""What a source is, before anything has been decoded out of it.

Read from the container's headers: codec, dimensions, pixel format, the average
frame rate and the timebase those rates are expressed in. All of it is available
without decoding a frame, and all of it decides what happens next — which is why
it is a type rather than five values passed around separately.

Three consumers, each of which would otherwise re-derive it. A **route probe**
is cached per machine *and per source shape*, because which decoder wins a seek
depends on frame size and codec rather than on the file
(`docs/findings/2026.08.21-decode-stack-best-combinations.md`), so the cache key
is composed here and spelled one way. A **derived file** — a proxy, a cut — is
named from the shape it was made at, so two of them made at different sizes
cannot collide under one name. And a **cost class** is measured against the
frame period, which is a property of the source and not of the machine
(ADR-0007, ADR-0008).

`nb_frames` is deliberately not here. The container's own frame count is one of
the three different answers this footage gives to "how many frames" (ADR-0004),
and the only one of the three that is never right; whoever wants a count wants
`len(FrameTable)`, and asking through the table is what stops the wrong number
being convenient.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import av


@dataclass(frozen=True)
class Shape:
    """A source's header facts, with the arithmetic they imply."""

    codec: str
    width: int
    height: int
    pix_fmt: str
    average_rate: Fraction
    timebase: Fraction

    @classmethod
    def read(cls, path: Path) -> "Shape":
        """Open, read the video stream's headers, close. Decodes nothing."""
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            context = stream.codec_context
            return cls(
                codec=context.name,
                width=stream.width,
                height=stream.height,
                pix_fmt=str(context.pix_fmt),
                average_rate=Fraction(stream.average_rate),
                timebase=Fraction(stream.time_base),
            )

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def frame_period_ms(self) -> float:
        """How long one frame lasts, in milliseconds.

        The unit a cost class is measured in — a step whose field fits the
        period once its fetch and its drawing are taken out is budgeted, and one
        that does not is a commit step (ADR-0007, ADR-0008). It is a fact about
        the footage, so it is stated here and never configured.
        """
        return float(1000 / self.average_rate)

    def probe_key(self, node: str | None = None) -> str:
        """The key a machine-dependent probe verdict is filed under.

        Machine, codec and frame size, because those are what the answer
        actually depends on: the same probe re-run against a different file of
        the same shape on the same box would land the same way, and re-probing
        per file would pay several real seeks for a verdict already held.
        """
        return (f"{node or platform.node()}|{self.codec}"
                f"|{self.width}x{self.height}")

    def derived_stem(self, kind: str, width: int | None = None) -> str:
        """A name for a file derived from this source at a given width.

        The width is in the name because a proxy built at one display size and
        one built at another are different files answering different requests,
        and a shared name would let the second silently serve the first's
        callers.
        """
        return f"{kind}-{width or self.width}-{self.codec}"
