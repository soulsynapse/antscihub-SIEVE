"""One stream taken away from another, on two named ports.

VISION's lead scenario ends here: a step generates a background, colour
thresholding runs beside it, and both reach one subtraction that ingests them.
Every other tool on the shelf reads the step above it and has no choice to
express; this one is fed twice and the wiring is the whole of what it is told.

**The ports are arithmetic and not scenery.** `minuend` and `subtrahend` name
the two positions of a subtraction and nothing else. A pair called `plate` and
`background` would put a scene description in a signature — a claim about what
the footage depicts, made by a tool that has only ever seen two float arrays —
and `adr/a-picked-files-meaning-is-the-port-it-wires-to.md` puts that claim on
the edge the user drew instead. So this tool is not where the semantic axis gets
decided (`todo/which-axis-carries-a-meaning-like-generated-background.md`); a
user wiring their colleague's background into `subtrahend` has stated that it is
the thing being removed, and the tool is what honours it.

**Signed by default, which is the setting that keeps the two ports apart.**
`background_ema` emits `|frame - background|` and is right to: it owns both
operands, produces them from one model, and there is no wiring to preserve. Here
the order is a decision somebody made with a mouse, and the default discards
nothing they chose — an animal darker than its background and one lighter than it
are opposite signs, and which of those is in the footage is a fact the user can
now see rather than one the tool averages away. `MAGNITUDE` is that discard asked
for on purpose, which is what a detector reading departure in either direction
wants; it is one parameter and not a second emission, for `normalize.mode`'s
reason — both settings are the node's one product.

**Float32 out, whatever came in.** A signed difference of two uint8 frames is
not a uint8 frame, and the alternative to widening is a narrowing that discards
exactly the half of the answer the sign was kept for.

**The two geometries are compared rather than broadcast.** Two ports can be fed
from anywhere in the graph, so a block grid and a full frame can meet here in a
way no single-input tool could arrange; numpy's broadcasting would take a frame
against one column of another and return a full-size picture. The executor
guarantees the two ports arrive at one frame *index*
(`pipeline/executor.py`) and nothing guarantees one shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

import numpy as np

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import Frame, FrameSpan

#: The port the difference is taken *from*.
MINUEND = "minuend"
#: The port taken *away*, which is where a background wires in.
SUBTRAHEND = "subtrahend"

#: What either port may be fed. The same set on both, because the pairing is
#: what this tool is about and a tool that admitted a dtype on one side only
#: would refuse the crossing the ports exist to make possible.
SUPPORTED_DTYPES = ("uint8", "uint16", "float32", "float64")

#: What this tool is for, in the words of somebody tuning it.
GUIDANCE = """\
Takes one of its two inputs away from the other, pixel by pixel or cell by cell.
The step wired into `minuend` is what you are looking at; the step wired into
`subtrahend` is what you want gone — a background, generated here or made
somewhere else and picked as a file.

Which input is which is the wiring, and it is yours to state. Nothing about a
file says it is a background; the port you drop it on does.

`signed` keeps the direction: values above what you subtracted come out positive
and values below come out negative, so an animal darker than its background stays
visibly darker. `magnitude` throws that away and reports only how far apart the
two are, which is what a detector wants when a departure in either direction
counts equally.

Both inputs have to be the same shape. Feeding it a full frame on one port and a
grid of block measurements on the other is refused rather than stretched to
fit."""


class SubtractMode(StrEnum):
    """Whether the direction of the difference survives."""

    #: `minuend - subtrahend`. Keeps the polarity the wiring chose.
    SIGNED = "signed"
    #: `|minuend - subtrahend|`. `background_ema`'s foreground, for the case
    #: where the two operands arrived on two edges instead of one model.
    MAGNITUDE = "magnitude"


def run(params: SubtractParams, window: Mapping[str, FrameSpan], state: None, /) -> Frame:
    """The difference of the two ports' target frames.

    Read by name from the mapping, never by position: the executor assembles it
    from `Dag.inputs` and nothing about that order is this tool's to rely on.

    Raises:
        ValueError: if the two ports carry different shapes. See the module
            docstring — the alternative is a broadcast, not a crash.
    """
    del state
    minuend = window[MINUEND].target
    subtrahend = window[SUBTRAHEND].target
    if minuend.data.shape != subtrahend.data.shape:
        raise ValueError(
            f"subtract was fed a {minuend.data.shape} frame on {MINUEND} and a "
            f"{subtrahend.data.shape} one on {SUBTRAHEND} at index {minuend.index}; "
            "one subtraction is one geometry"
        )
    out = np.subtract(np.asarray(minuend.data, np.float32), np.asarray(subtrahend.data, np.float32))
    if params.mode is SubtractMode.MAGNITUDE:
        np.abs(out, out=out)
    return Frame(data=out, index=minuend.index, channels=minuend.channels)


@register_tool(
    tool_id="subtract",
    version="1.0.0",
    summary="One input taken away from another, on two named ports.",
    accepts={
        MINUEND: ArraySpec(dtypes=SUPPORTED_DTYPES),
        SUBTRAHEND: ArraySpec(dtypes=SUPPORTED_DTYPES),
    },
    # Channels unstated on both sides: the difference is elementwise and the
    # layout carries through, so whatever pair of matching geometries arrived
    # leaves in the same shape.
    emits=ArraySpec(dtypes=("float32",)),
    # One product under both settings, which is why `mode` is a parameter and
    # this list has one entry — a save screen offering "signed" and "magnitude"
    # as two keepable outputs would be offering one output twice.
    emissions=(Emission("difference"),),
    run=run,
    # Elementwise between two streams the graph already agreed on the shape of:
    # whatever one value described on either side, the difference describes.
    element=ElementRelation.PRESERVED,
    mode=Mode.STREAMING,
    guidance=GUIDANCE,
    primary_params=("mode",),
    caption=(CaptionPart(param="mode"),),
    param_stereotypes={"mode": ParamStereotype.ENUM},
)
class SubtractParams(ParamsBase):
    """Whether the direction of the difference survives."""

    #: Defaults to `SIGNED`, which is the setting under which the two ports are
    #: not interchangeable — see the module docstring on why the tool that owns
    #: both its operands defaults the other way.
    mode: SubtractMode = SubtractMode.SIGNED
