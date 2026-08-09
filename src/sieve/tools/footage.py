"""A video file standing in the graph as a node with no upstream.

`pick`'s sibling and the second source tool, for the case
`adr/a-users-file-wires-in-like-any-other-input.md` was actually forced by:
footage that is already cut. A written crop, a checkpointed stretch re-read, a
folder of files somebody exported from another tool — under that decision none
of these is a path beside the graph, a flag on the plan, or a substitution a
front end performs at plan time. Each is a node, wired where the step that would
have produced those frames stood, so a front end that reads the document is
served without learning that artifacts exist.

**It is read through `decode/`, and that is the whole of why its key is
`source_key` rather than `picked_key`.** `adr/a-root-keys-by-its-reader.md`
rules the flavour off the reader: this tool opens the file with the same reader
the footage is opened with, in the same format the graph derives, so the string
it folds is the string a run over that file *as its footage* folds. That is what
makes wiring a written crop in at a crop node's place move no key below it —
the equality `a-users-file-wires-in-like-any-other-input`'s key paragraph
states, holding by rule rather than by coincidence.

**`first_index` is the only arithmetic here, and it is the one thing no other
module may do.** A file cut from `[10, 16)` holds the run's frame 10 at its own
frame 0. Source numbering is what everything above a root speaks —
`executor._source_frame` refuses a frame filed under any other index, and the
store is keyed on it — so the translation happens here, once, on the way out of
the reader. A file that *is* the whole of what a run answers for leaves it at
zero, which is the folder case: no record, no offset, no arithmetic.

**A window past either end of the file is a decode error, not a fallback.** The
plan-time route this tool replaces declined a record that could not cover the
read range and ran the parent instead; there is no parent to fall back to once
the file is the source, exactly as there is none for a folder of already-cut files. That is
the trade `a-users-file-wires-in-like-any-other-input` takes — coverage stops
being a clause a resolver evaluates per run and becomes a property of the
document, checked when the edit is offered (`pipeline/crop_serving.py`).

**Readers are pooled, not opened per frame.** A `VideoReader` is a decode thread
pool, so one per frame is the interactive loop's whole budget spent on setup;
the pool below holds a few open and closes the ones it evicts. It is keyed on
what the file *is* rather than on where it is, for `pick._decoded`'s reason: an
entry that outlived an edit would serve the run the file it was opened against
instead of the one on disk.
"""

from __future__ import annotations

from collections import OrderedDict
from glob import glob
from pathlib import Path

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
from sieve.decode.reader import VideoDecodeError, VideoReader

#: What `decode/reader.py` produces, which is what this tool hands the graph.
#: Stated rather than left open for `pick`'s reason: a wildcard `emits` admits
#: against every `accepts` on the shelf and retires `dag.py`'s edge check for
#: every graph holding this node.
FOOTAGE_DTYPES = ("uint8",)
FOOTAGE_CHANNELS = (ChannelSpec.GRAY, ChannelSpec.BGR)

#: How many readers stay open. Two, because the shapes that exist are one file
#: per run and one file per replicate rendered in turn; a project fanned out
#: over twelve arenas evicts eleven times per sweep and pays a reader open for
#: each, which is a measurement to take before it is a number to raise.
POOL_SIZE = 2

#: What this tool is for, in the words of somebody choosing a file with it.
GUIDANCE = """\
Reads a video file as the frames a step of the pipeline produces, so a file that
is already cut wires in exactly where the step that would have cut it stood.
Reach for it when the footage you want is on disk already — a crop written out
earlier, a stretch someone exported for you, a folder of per-arena files.

`path` is the file. If it holds a piece of a longer source, `first index` is the
frame of that source its own frame 0 is; leave it at zero for a file that is the
whole of what you are working over. The run asks for frames in the source's
numbering either way, so everything downstream reads the same numbers whether
the file is the whole video or a window out of it.

What ends up in the cache key is the file itself and the format it is decoded
in, which is exactly what a run reading that file as its footage would key on —
so a crop wired in here computes nothing that was already computed against it."""


class FootageFile:
    """Resolves the path, and reads the file it found through the decoder.

    `pick.PickedFile`'s shape and for its reason: one object answers both
    questions the graph asks about a source root — which file, and what is in it
    — so the resolution is written once and cannot come back with two answers.

    Stateless in the sense that matters: the reader pool below is shared and is
    keyed on what a file is, so two concurrent renders over one file share a
    reader and neither can advance the other's position — `VideoReader.read`
    seeks per call.
    """

    #: Through `decode/`, so this root keys `source_key`
    #: (`adr/a-root-keys-by-its-reader.md`). The declaration the whole module
    #: header is about.
    decoded = True

    def file(self, params: FootageParams, /) -> Path:
        """The one file `params.path` names.

        A pattern rather than a literal name, matching `pick`: an absolute
        pattern is used as it stands and a relative one resolves against the
        process's directory. What a written crop's wiring puts here is an
        absolute path, because the document's own relative-to-the-project rule
        (`CropRecord.path`) has no reader inside a tool and a tool that learned
        it would be `pipeline` resolving a second time.

        Raises:
            SourceFileError: if the pattern matches no file or more than one,
                on `pick.PickedFile.file`'s terms.
        """
        found = sorted(path for path in map(Path, glob(params.path)) if path.is_file())
        if not found:
            raise SourceFileError(
                f"footage: {params.path!r} names no file, so there is nothing for this step to "
                "read — a run over it cannot happen rather than running over an absence"
            )
        if len(found) > 1:
            listed = ", ".join(str(path) for path in found[:4])
            raise SourceFileError(
                f"footage: {params.path!r} names {len(found)} files ({listed}"
                f"{', ...' if len(found) > 4 else ''}) — which of them a step reads is not "
                "something the filesystem's listing order gets to decide, so narrow the pattern "
                "to one"
            )
        return found[0]

    def read(self, params: FootageParams, index: FrameIndex, /, *, luma: bool) -> Frame:
        """This file's frame for source frame `index`, in source numbering.

        The frame's own index is rewritten rather than passed through: the store
        is keyed on the frame a run is answering for, and a node reporting its
        file's numbering would file frame 10's result under 0.

        Raises:
            SourceFileError: if the path parameter names no file or several.
            VideoDecodeError: if `index` is before this file begins, or past
                what it holds. The first is caught here rather than left to a
                negative index reaching a reader that treats it as an offset;
                the second is the reader's own message, which names the file's
                range and is the honest answer to a document asking for frames
                nothing on disk holds.
        """
        first = params.first_index
        if int(index) < first:
            raise VideoDecodeError(f"frame {int(index)} is before this file begins (frame {first})")
        path = self.file(params)
        stat = path.stat()
        reader = _POOL.reader(path, stat.st_size, stat.st_mtime_ns, luma=luma)
        frame = reader.read(int(index) - first)
        return Frame(data=frame.data, index=index, channels=frame.channels)


class _ReaderPool:
    """A few open `VideoReader`s, closed on eviction.

    Not `functools.lru_cache`: an evicted reader owns a decode thread pool and a
    container handle, and a cache that drops the reference without closing it
    leaks both until the interpreter exits — which under a GUI session is never.

    Not a context manager either, and that is the wart this class is. The
    executor has no lifecycle hook for a source tool, so the last readers a run
    opened stay open until something else evicts them. `close_all` exists for
    the caller that knows a run is over; nothing calls it in production yet.
    """

    def __init__(self, size: int = POOL_SIZE) -> None:
        self._open: OrderedDict[tuple[Path, int, int, bool], VideoReader] = OrderedDict()
        self._size = size

    def reader(self, path: Path, size: int, mtime_ns: int, *, luma: bool) -> VideoReader:
        """An open reader on `path`, opened in `luma` if one is not already.

        Keyed on the three facts `cache_key.source_identity` is keyed on plus
        the format, because a reader opened on the luma plane and one opened on
        colour are two readers over one file and handing back the wrong one is
        the wrong-pixels trap the codec finding measured.

        Raises:
            VideoDecodeError: if the container will not open.
        """
        key = (path, size, mtime_ns, luma)
        held = self._open.get(key)
        if held is not None:
            self._open.move_to_end(key)
            return held
        opened = VideoReader(path, luma=luma)
        self._open[key] = opened
        while len(self._open) > self._size:
            _, evicted = self._open.popitem(last=False)
            evicted.close()
        return opened

    def close_all(self) -> None:
        """Close every reader held. Idempotent."""
        while self._open:
            _, evicted = self._open.popitem()
            evicted.close()


#: Shared by every node of this tool in every run. See `_ReaderPool`.
_POOL = _ReaderPool()

#: Shared by every node of this tool. See `FootageFile` on why one is enough.
SOURCE = FootageFile()


@register_tool(
    tool_id="footage",
    version="1.0.0",
    summary="Read a video file already on disk as this step's frames.",
    # `pick`'s reasoning, unchanged: nothing feeds this node, so the wildcard is
    # a statement about a position that does not exist, and `ArraySpec.matches`
    # reads an empty tuple as never plausible so it is not offered downstream.
    accepts=ArraySpec(),
    emits=ArraySpec(dtypes=FOOTAGE_DTYPES, channels=FOOTAGE_CHANNELS),
    # One product: frames. Which stretch of which source they are is `path` and
    # `first_index`, not a second emission to select between.
    emissions=(Emission("footage"),),
    source=SOURCE,
    element=ElementKind.PIXEL,
    element_names=SOURCE_ELEMENT_NAMES,
    mode=Mode.STREAMING,
    guidance=GUIDANCE,
    primary_params=("path",),
    caption=(CaptionPart(param="path"),),
    param_stereotypes={
        "path": ParamStereotype.PATH,
        # A number the wiring normally fills in from a record rather than one a
        # user reaches for, and it is declared anyway: a parameter the map skips
        # is one nothing can populate, and a node re-pointed at a different
        # window of the same source is exactly the edit somebody makes by hand.
        "first_index": ParamStereotype.SCALAR_RANGE,
    },
)
class FootageParams(ParamsBase):
    """Which file to read, and where its frame 0 sits in the source."""

    #: Empty by default, for `PickParams.pattern`'s reason: a document may
    #: legitimately hold a source node nobody has chosen a file for yet, and it
    #: is the run that refuses rather than the document that cannot be written.
    path: str = Field(default="")
    #: The source frame this file's frame 0 is. Zero for a file that is not a
    #: window out of anything, which is every case with no `CropRecord` behind
    #: it. Never negative: a file cannot begin before the footage it was cut
    #: from.
    first_index: int = Field(default=0, ge=0)
