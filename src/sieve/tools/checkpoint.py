"""A checkpointed node's `.npy`, standing back in the graph as the node it was.

The third source tool and the second half of
`adr/a-users-file-wires-in-like-any-other-input.md`'s "a file where a node
stood": `tools/footage.py` is that sentence for a video, this is it for a
checkpoint. Nothing was unwound to get here — the checkpoint side never had a
plan-time reader — so this is written as a source tool the first time rather
than migrated into one.

**It is not read through `decode/`, and that is the whole of why its key is
`picked_key`.** `adr/a-root-keys-by-its-reader.md` rules the flavour off the
reader and nothing else. A written crop is a video, opened by the same stack in
the same format the graph derives, so it folds the string its footage folds. A
checkpoint is whatever the node emitted — float32 block measurements as often as
pixels — and numpy opens it here, so `decoder_identity()` and a decode format
would key a `.npy` against a video decoder that never touched it. The
consequence is the difference from the crop half: a read-back root does *not*
fold the checkpointed node's key, and the subtree below it is keyed off the
written file instead. Wiring a checkpoint in is a re-key by construction, which
is correct — the file is a different ancestry from the graph that made it, and a
key that pretended otherwise would serve a stale `.npy` under a graph the
document has since edited.

**The file name is the product, and that is not a convenience.** A checkpoint's
identity is `cache_key.source_identity` of the file, which is a path, a size and
an mtime; a `.npy` named for its node alone says float32 and says nothing about
whether it is coherence or flow speed, so a root keyed off it would key two
products alike and a reader opening it could not check it against the claim it
was made for (`todo/a-checkpoint-does-not-record-which-product-it-holds.md`).
`storage/checkpoint_writer.py` writes `<node>.<emission>.npy` and records the
emission in the manifest beside it, so the product is in the identity this tool
keys on rather than one lookup away in a document that has moved on.

**What it emits is unconstrained, and what one value means is undeclarable.**
Both are refusals to claim. `pick` and `footage` state their dtypes because a
picture and a decoded frame are known shapes; a checkpoint stands where *any*
node stood, so a narrowing `emits` would refuse the graphs this tool exists to
serve, and a concrete `ElementKind` would be a confident wrong noun for every
checkpoint of a tool that redefines its elements. The file records dtype and
shape and does not record what one value is a value of — so nothing here says.
That propagates: a detector wired over a read-back signal has no noun to count
in, and `Dag.element_lost_at` names this node. Recovering it means the manifest
growing an element field and this tool growing the parameter that carries it,
which is work with no consumer until a count over a read-back result exists.
"""

from __future__ import annotations

from functools import lru_cache
from glob import glob
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    SourceFileError,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ChannelSpec, Frame, FrameIndex

#: How many stacks stay mapped. `pick._decoded`'s bound and its reason: a memmap
#: holds a file handle, and one per frame would be the interactive loop's budget
#: spent on opening a file that has not changed.
OPEN_STACKS = 8

#: What this tool is for, in the words of somebody choosing a file with it.
GUIDANCE = """\
Reads a checkpoint an earlier run wrote back into the pipeline, so the step that
produced it does not have to run again. Reach for it when the expensive half of
a graph is settled and you are tuning the cheap half — checkpoint the signal
once, then wire the `.npy` in where that step stood and tune the detector over
it.

`path` is the file, which is the one named in the manifest beside it, and
`first index` is the source frame its first row holds — the `start` of the span
that manifest records. Everything downstream then reads the same frame numbers
it read when the step was computed rather than stored.

What ends up in the cache key is the file itself, and not the key the step had
when it was computed: a checkpoint read back is a different ancestry from the
graph that wrote it, so wiring one in re-keys what is below it once. Replace the
file and everything downstream recomputes."""


class CheckpointFile:
    """Resolves the path, and reads the stack it found.

    `pick.PickedFile`'s shape and for its reason: one object answers both
    questions the graph asks about a source root — which file, and what is in it
    — so the resolution is written once and cannot come back with two answers.
    """

    #: numpy, not `decode/`, so this root keys `picked_key`
    #: (`adr/a-root-keys-by-its-reader.md`). The declaration the module header
    #: is about.
    decoded = False

    def file(self, params: CheckpointParams, /) -> Path:
        """The one file `params.path` names.

        Raises:
            SourceFileError: if the pattern matches no file or more than one, on
                `pick.PickedFile.file`'s terms.
        """
        found = sorted(path for path in map(Path, glob(params.path)) if path.is_file())
        if not found:
            raise SourceFileError(
                f"checkpoint: {params.path!r} names no file, so there is nothing for this step to "
                "read — a run over it cannot happen rather than running over an absence"
            )
        if len(found) > 1:
            listed = ", ".join(str(path) for path in found[:4])
            raise SourceFileError(
                f"checkpoint: {params.path!r} names {len(found)} files ({listed}"
                f"{', ...' if len(found) > 4 else ''}) — which of them a step reads is not "
                "something the filesystem's listing order gets to decide, so narrow the pattern "
                "to one"
            )
        return found[0]

    def read(self, params: CheckpointParams, index: FrameIndex, /, *, luma: bool) -> Frame:
        """This file's row for source frame `index`, in source numbering.

        `luma` is ignored, on `pick.PickedFile.read`'s terms: a root read with
        its own code keys `picked_key`, which folds no decode format, so an
        output that varied with one would be filed under an entry that cannot
        tell the two apart. A checkpoint has no colour question anyway — the
        stack is the values the node emitted.

        Raises:
            SourceFileError: if the path parameter names no file or several, if
                the file is not a stack of frames this tool can hand on, or if
                `index` is outside the stretch it holds. The last is a refusal
                rather than a fallback for `tools/footage.py`'s reason — there
                is no parent to decline back to once the file is the source —
                and it is a `SourceFileError` rather than a decode error because
                no decoder was ever asked: what failed is that the file the
                pattern resolved to cannot answer this run.
        """
        first = params.first_index
        path = self.file(params)
        stat = path.stat()
        stack, channels = _stack(path, stat.st_size, stat.st_mtime_ns)
        row = int(index) - first
        if row < 0 or row >= len(stack):
            raise SourceFileError(
                f"checkpoint: {path} holds source frames [{first}:{first + len(stack)}) and this "
                f"run asked for frame {int(index)} — a file that is the source has no parent to "
                "fall back to, so the span a document asks for has to be one the file covers"
            )
        return Frame(data=stack[row], index=index, channels=channels)


@lru_cache(maxsize=OPEN_STACKS)
def _stack(path: Path, size: int, mtime_ns: int) -> tuple[NDArray[Any], ChannelSpec]:
    """`path`'s frames and their layout, mapped once per version of the file.

    Keyed on the three facts `cache_key.source_identity` is keyed on, for
    `pick._decoded`'s reason: an entry that outlived an edit would serve the run
    the stack it was opened against instead of the one on disk.

    Memory-mapped rather than loaded, which is the read side of the writer's own
    trade: a checkpoint exists so that an hour of footage need not be recomputed,
    and reading it back into resident memory would put the run length back into
    the memory bound the writer took it out of.

    Rows are handed out as views rather than copied. Nothing in the graph may
    mutate a frame it was handed, so a copy per frame would be a
    frame-sized allocation bought to defend against something that is already a
    defect.

    Raises:
        SourceFileError: if the file will not open as an array, or holds
            something that is not a stack of single- or three-channel frames.
    """
    try:
        stack = np.load(path, mmap_mode="r")
    except ValueError as unreadable:
        raise SourceFileError(
            f"checkpoint: {path} is not a stack this step can read — it resolved and then would "
            f"not open as an array ({unreadable})"
        ) from unreadable
    if stack.ndim == 3:
        return stack, ChannelSpec.GRAY
    if stack.ndim == 4 and stack.shape[3] == 3:
        return stack, ChannelSpec.BGR
    raise SourceFileError(
        f"checkpoint: {path} is {stack.shape}, and a checkpoint is a stack of frames — "
        "(frames, rows, columns) for a single-channel result and (frames, rows, columns, 3) for "
        "a colour one, which are the two layouts a frame reaches this graph in"
    )


#: Shared by every node of this tool. See `CheckpointFile` on why one is enough.
SOURCE = CheckpointFile()


@register_tool(
    tool_id="checkpoint",
    version="1.0.0",
    summary="Read a checkpoint an earlier run wrote as this step's frames.",
    # `pick`'s reasoning, unchanged: nothing feeds this node, so the wildcard is
    # a statement about a position that does not exist. What keeps it off a
    # downstream offer is `source` rather than the predicate — an unstated
    # `accepts` is a declared universal (ADR 32), so the position asks whether it
    # has an upstream at all (`tool_registry.offered_tools`).
    accepts=ArraySpec(),
    # Unconstrained on purpose, and it is the one place this tool differs from
    # its two siblings. See the module header: a checkpoint stands where any
    # node stood, so every dtype on the shelf is one it may legitimately hold.
    emits=ArraySpec(),
    # One product: the stack. *Which* product of which node it holds is the
    # file, named by `storage/checkpoint_writer.py` and recorded in its
    # manifest — not a second emission for a node to select between.
    emissions=(Emission("checkpointed"),),
    source=SOURCE,
    # Undeclarable rather than PIXEL. The module header argues it; `ToolSpec`
    # admits it for a source tool and for no other kind.
    element=None,
    mode=Mode.STREAMING,
    guidance=GUIDANCE,
    primary_params=("path",),
    caption=(CaptionPart(param="path"),),
    param_stereotypes={
        "path": ParamStereotype.PATH,
        # `footage.first_index`'s reasoning: a number the wiring normally fills
        # in from a manifest rather than one a user reaches for, declared anyway
        # because a parameter the map skips is one nothing can populate.
        "first_index": ParamStereotype.SCALAR_RANGE,
    },
)
class CheckpointParams(ParamsBase):
    """Which file to read, and where its first row sits in the source."""

    #: Empty by default, for `PickParams.pattern`'s reason: a document may
    #: legitimately hold a source node nobody has chosen a file for yet, and it
    #: is the run that refuses rather than the document that cannot be written.
    path: str = Field(default="")
    #: The source frame this file's row 0 is, which is the `start` of the span
    #: its manifest records. Never negative: a checkpoint cannot begin before
    #: the footage its run answered for.
    first_index: int = Field(default=0, ge=0)
