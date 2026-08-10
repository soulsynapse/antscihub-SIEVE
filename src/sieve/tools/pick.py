"""A file the user chose, standing in the graph as a node with no upstream.

The first source tool (`adr/a-users-file-wires-in-like-any-other-input.md`), and
the case it is for is VISION's picker: a background made outside the project, by
a colleague in another tool, standing where the step that generates one stood.
Under this decision that is not a new kind of edge and not a parameter on the
consumer — it is a node, so adding a file is adding a node and choosing among
sources is moving an edge.

**One picture, broadcast.** The file resolves to a still, and the same frame is
handed to every frame of the run under the index the run is answering for. That
is the ADR's "a source that is one value for the whole run broadcasts it across
the span, so a static input needs no window shape the per-frame machinery does
not already have" — and it is also what keeps this tool clear of the question the
ADR leaves open, which is what a frame index means when two inputs are videos of
different lengths. A picker over footage inherits that question and this one does
not have it.

**What it declares it emits is what a decoded frame is**, and stating it is
deliberate rather than convenient. `StreamSpec.admits` is permissive by
construction: a wildcard on either side admits, so an unconstrained `emits` here
would pass against every `accepts` on the shelf and retire `dag.py`'s edge check
for every graph containing this node. `crop` and `span` are not the precedent
they look like — both are wildcards on *both* sides of a pass-through, so their
unstated pair is a statement of preservation and the check still runs against the
real upstream. A source tool has no upstream to preserve from, which is also why
the wildcard on *this* tool's `accepts` costs nothing: an offer asks whether the
position has an input before it asks what fits there.

What its frames *mean* — that this one is a background rather than a plate — is
not a question a stream type asks, and this tool does not answer it on any other
axis either. It cannot: `adr/an-outputs-kind-is-the-picture-it-makes.md` rules
that no `ElementKind` member is added for a tool, and the offering ruling on
`todo/the-offering-predicate-is-not-the-edge-legality-check.md` refuses
Emission-name keying in favour of derivation. The meaning is the position the
node is wired into, and the user is the one who says which — a file they brought
resolves the same as any other picture, so there is nothing to derive it from
(`todo/which-axis-carries-a-meaning-like-generated-background.md`). That gesture
waits on a node with more than one input to point at. This tool declares the one
product it has and nothing selects between products it does not have.

**Where the pattern is anchored.** As written: an absolute pattern is used as it
stands, a relative one against the process's directory. That is what a file
picker hands over and it is deliberately not the project directory — a picked
file relative to the project is a portable identity question, and the identity an
external input carries is ruled and lands with the schema field that holds it
(`todo/whether-an-external-input-carries-a-portable-identity.md`). What is fixed
here is only the half the ADR settles: the *rule* never enters a key, only the
file the rule found (`pipeline/cache_key.picked_key`).

Resolution happens per frame rather than once, and the cost is a glob and a stat
against a decode this module caches. If it ever shows up in the loop budget the
answer is not a cache here — a stale one would hide a file the user just dropped
into the folder, which VISION's folder scenario asks to be seen — it is the plan
resolving once, which is where `resolve_source.picked_identities` already does it
for the keys.
"""

from __future__ import annotations

from functools import lru_cache
from glob import glob
from pathlib import Path
from typing import Any

import cv2
from numpy.typing import NDArray
from pydantic import Field

from sieve.core.tool_base import (
    SOURCE_ELEMENT_NAMES,
    ArraySpec,
    CaptionPart,
    ElementKind,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    SourceFileError,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ChannelSpec, Frame, FrameIndex

#: What a decoded frame carries, which is what this tool hands the graph: the
#: two layouts `decode/reader.py` produces, at the one depth an image file
#: reaches them in. Both tuples are stated for the module docstring's reason.
PICKED_DTYPES = ("uint8",)
PICKED_CHANNELS = (ChannelSpec.GRAY, ChannelSpec.BGR)

#: What this tool is for, in the words of somebody choosing a file with it.
GUIDANCE = """\
Puts a picture from outside the project into the pipeline as a step of its own,
so anything downstream reads it exactly as it would read a step that computed
one. Reach for it when the thing you want to subtract, mask with, or compare
against was made somewhere else — by a colleague, in another tool, or by an
earlier run you kept.

`pattern` is the file, and it may be a general match like `*_bg.png` rather than
one name. The match has to land on exactly one file: none means the run cannot
happen and several means the answer would be whichever the filesystem listed
first, which is not something a project should depend on. What ends up in the
cache key is the file the match found and never the match itself, so
reorganising the folder underneath a project does not invalidate anything, and
pointing two projects at one file makes them agree about it.

The picture is broadcast — every frame of the run is handed the same one. Swap
the file and everything downstream recomputes; that is the point, and it is what
makes an A/B of two backgrounds a change of one parameter."""


class PickedFile:
    """Resolves the pattern, and reads the file it found.

    A class rather than two module functions because `ToolSpec.source` points at
    one thing that answers both questions — the executor wants frames and the key
    walk wants the file's identity, and a pattern resolved twice by two callers
    is two answers on the day it starts matching something new.

    Stateless: the instance below is shared by every node of this tool in every
    run, which is safe in the way `ToolSpec.state_factory` exists to guarantee it
    is *not* for run state. There is nothing here that a second concurrent
    preview could advance — the file is read again or found in a cache keyed on
    what the file is, and two runs handed the same array are handed the same
    picture.
    """

    #: Own code, not `decode/`: `cv2.imread` below. So this root keys
    #: `picked_key` (`adr/a-root-keys-by-its-reader.md`).
    decoded = False

    def file(self, params: PickParams, /) -> Path:
        """The one file `params.pattern` names.

        Raises:
            SourceFileError: if the pattern matches no file or more than one.
                Both are refused rather than resolved — see this module's
                header and `SourceFileError`.
        """
        found = sorted(path for path in map(Path, glob(params.pattern)) if path.is_file())
        if not found:
            raise SourceFileError(
                f"pick: {params.pattern!r} names no file, so there is nothing for this step to "
                "read — a run over it cannot happen rather than running over an absence"
            )
        if len(found) > 1:
            listed = ", ".join(str(path) for path in found[:4])
            raise SourceFileError(
                f"pick: {params.pattern!r} names {len(found)} files ({listed}"
                f"{', ...' if len(found) > 4 else ''}) — which of them a step reads is not "
                "something the filesystem's listing order gets to decide, so narrow the pattern "
                "to one"
            )
        return found[0]

    def read(self, params: PickParams, index: FrameIndex, /, *, luma: bool) -> Frame:
        """The picked picture, filed under the frame the run is answering for.

        `luma` is ignored, and that is the contract rather than an oversight: a
        root read with its own code keys `picked_key`, which folds no decode
        format, so a picture converted for a luma session would be filed under
        the entry a colour session reads back (`ToolSource.read`). What the file
        holds is what this hands over, and an edge that cannot take it is
        refused by `dag.py` before a frame is read.

        Raises:
            SourceFileError: if the pattern does not resolve, or the file it
                resolved to is not a picture this tool can hand on as what it
                declared it emits.
        """
        path = self.file(params)
        stat = path.stat()
        data, channels = _decoded(path, stat.st_size, stat.st_mtime_ns)
        return Frame(data=data, index=index, channels=channels)


@lru_cache(maxsize=8)
def _decoded(path: Path, size: int, mtime_ns: int) -> tuple[NDArray[Any], ChannelSpec]:
    """`path`'s pixels and their layout, decoded once per version of the file.

    Keyed on the same three facts `cache_key.source_identity` is, and for the
    overlapping reason: they are what changes when the file changes, cheaply. An
    entry that outlived an edit would hand a run the picture it was keyed
    against instead of the one on disk.

    The array is handed out rather than copied. Nothing in the graph may mutate
    a frame it was handed — the executor already gives one decoded frame to
    every root of a graph and to the result beside them — so a copy per frame
    would be a background-sized allocation bought to defend against something
    that is already a defect.

    Raises:
        SourceFileError: if the file will not decode, or decodes to something
            other than the dtype and layouts this tool declares.
    """
    data = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if data is None:
        raise SourceFileError(
            f"pick: {path} is not a picture this step can read — it resolved and then would not "
            "decode"
        )
    if data.ndim == 3 and data.shape[2] == 4:
        # Alpha is dropped rather than refused: a background exported with a
        # transparency channel is the ordinary product of the tools that make
        # one, and what the graph below reads is the colour.
        data = data[:, :, :3]
    if data.dtype.name not in PICKED_DTYPES:
        raise SourceFileError(
            f"pick: {path} holds {data.dtype} and this step emits {'/'.join(PICKED_DTYPES)} — a "
            "declaration that bent to fit the file would be a claim every graph downstream of it "
            "was checked against and none of them holds"
        )
    if data.ndim == 2:
        return data, ChannelSpec.GRAY
    if data.ndim == 3 and data.shape[2] == 3:
        return data, ChannelSpec.BGR
    raise SourceFileError(
        f"pick: {path} is {data.shape}, which is neither a single-channel picture nor a "
        "three-channel one — those are the two layouts a decoded frame reaches this graph in"
    )


#: Shared by every node of this tool. See `PickedFile` on why one is enough.
SOURCE = PickedFile()


@register_tool(
    tool_id="pick",
    version="1.0.0",
    summary="Read a picture chosen outside the project and broadcast it.",
    # Nothing feeds this node — it is a root by construction, and a root's input
    # is the one edge `dag._edge_faults` never checks. The wildcard is therefore
    # a statement about a position that does not exist rather than the claim of
    # ignorance the same value on `emits` would be. It reads as a declared
    # universal everywhere else (ADR 32), so what keeps this tool off a
    # downstream offer is `source`, which is the declaration that says there is
    # no input position to speak of (`tool_registry.offered_tools`).
    accepts=ArraySpec(),
    emits=ArraySpec(dtypes=PICKED_DTYPES, channels=PICKED_CHANNELS),
    # One product. What the picture *means* — a background, a mask, a plate — is
    # the position's to say and never a second emission here (ADR 29, and the
    # offering ruling that answers by derivation).
    emissions=(Emission("picked"),),
    source=SOURCE,
    # The values are the file's own pixels, which is what a decoded frame's
    # values are; `PRESERVED` is not available to a node with nothing upstream
    # to preserve from.
    element=ElementKind.PIXEL,
    element_names=SOURCE_ELEMENT_NAMES,
    mode=Mode.STREAMING,
    guidance=GUIDANCE,
    primary_params=("pattern",),
    caption=(CaptionPart(param="pattern"),),
    param_stereotypes={"pattern": ParamStereotype.PATH},
)
class PickParams(ParamsBase):
    """Which file to read."""

    #: Empty by default, and that is a state a document may legitimately hold:
    #: VISION's new project opens on a source picker with nothing chosen. It is
    #: the run that refuses, naming the pattern, rather than the document that
    #: cannot be written.
    pattern: str = Field(default="")
