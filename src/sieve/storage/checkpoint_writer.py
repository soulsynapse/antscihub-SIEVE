"""A checkpointed node's whole span at rest: one `.npy`, plus a manifest.

This is the second thing SIEVE writes that outlives the process, and it is the
one v2 declared and never built — `Project.checkpoints` was validated there and
nothing ever consumed it. `adr/declared-means-verified.md` is why it is built
here rather than cut: a field the schema carries and no machinery reads is the
shape v3 does not keep.

**The format is a stack of frames in a file numpy opens, and nothing else.** One
`.npy` per checkpointed node per replicate, shaped `(frames, *frame shape)`, plus
a `manifest.yaml` naming each file's node, its cache key, and the source span it
covers. Nobody has to argue for a library to read it, it diffs as a file
comparison rather than as a claim, and the alternative — zarr, a result-store API
— is held in `PLAN.md`'s revival table against a measured need: a result too
large or too random-access for a file per checkpoint. That trigger is real and
this writer is where it will be felt, because a `.npy` is one array with one
header and there is no way to append to it after the fact.

**Written frame by frame into a memory-mapped file, deliberately.** The frame
count is `span.frame_count` and the shape comes from the first frame, so the
whole array can be sized before the second frame exists — which means a
checkpoint over an hour of footage costs one frame of resident memory rather than
the whole result. Holding the span and calling `np.save` at the end would be
shorter and would make the memory bound the *run length*, which is the one thing
a checkpoint exists to make survivable.

**A part file, for `materialize.py`'s reason.** A `.npy` whose header says a
thousand frames and whose tail is the zeros `open_memmap` created is a file that
reads back perfectly and is wrong, so nothing is renamed into place until every
frame of the span has arrived. A run that fails, is cancelled, or ends short
leaves the destination name either absent or holding the previous good file.

**The folder is keyed by `replicate_id` and the display name lives in the
manifest.** A slug would be readable and would collide the moment two replicates
are named the same, which is the one failure that overwrites a result rather than
reporting one; the id is unique by construction because `Project` refuses a
duplicate. `materialize.py` can afford the opposite trade because a crop record
carries geometry that distinguishes two files of one name, and a checkpoint has
no such field.

**The key is in the manifest and never in a path.** A checkpoint changes where a
result lives and never what it is (`cache_key.py`), so the file has to be
findable without one — and recording the key beside it is what lets a reader
later ask whether the file still describes what the project would now compute.

**The product is in the path, and it is the one fact that has to be.** A node of
`block_signal` can emit any of four measurements and the file is what a reviewer
opens; a `.npy` of float32 named for its node alone could be coherence or flow
speed, recoverable only by looking up a parameter in a document that has since
moved on. It is in the name rather than only in the manifest because the name is
what `cache_key.source_identity` sees: `tools/checkpoint.py` reads a checkpoint
back as a source root keyed off its file, so a name that skipped the product
would key two products of one node alike. Handed in rather than derived — this
module takes frames and knows nothing about tools.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import yaml
from numpy.lib.format import open_memmap
from numpy.typing import NDArray

from sieve.core.pipeline_model import NODE_ID_PATTERN, Replicate, Sink, SourceSpan
from sieve.core.types import Frame

#: The `Sink.format` a checkpoint is recorded under, spelt as a sink format is
#: spelt. Resolved by name like a `tool_id`, which is why it is a constant here
#: and not an enum in `core` (`Sink.format`).
CHECKPOINT_FORMAT = "npy"

#: Where checkpoints live: `<video stem>.checkpoints/` beside the project file,
#: matching `materialize.CROPS_SUFFIX`'s convention so a project folder holds one
#: child folder per kind of thing written rather than one per run.
CHECKPOINTS_SUFFIX = ".checkpoints"

MANIFEST_NAME = "manifest.yaml"

#: Bumped when a written manifest stops being readable by this code unchanged.
#: Separate from `SCHEMA_VERSION`: a project document and a run's output are
#: versioned by different things, and tying them would make every schema edit
#: invalidate folders of correct results.
MANIFEST_VERSION = 1

#: The folder a project with no fan-out writes into. A name rather than the
#: checkpoint folder itself, so that adding the first replicate to a project
#: moves results into a sibling rather than leaving them mixed with it.
BASELINE_DIR = "baseline"


class CheckpointWriteError(RuntimeError):
    """A checkpoint could not be written, or was not written whole."""


@dataclass(frozen=True, slots=True)
class Kept:
    """What the caller says about one checkpointed node, per replicate.

    One value rather than two parallel mappings, so a node cannot be in the key
    list and out of the product list — the two are asked of the same node at the
    same moment and a writer reconciling them would be reconciling a caller's
    bookkeeping.
    """

    #: This node's cache key for this replicate, or `None` where the node may
    #: not be keyed at all (`cache_key.NotCacheableError`).
    key: str | None
    #: Which of the tool's products the run computed —
    #: `tool_base.selected_emission`. Not derived here: this module takes
    #: outputs and knows nothing about tools.
    emission: str


def checkpoints_dir(video: Path, project_dir: Path) -> Path:
    """The folder checkpoints of `video` belong in. Need not exist."""
    return project_dir / checkpoints_name(video)


def checkpoints_name(video: Path) -> str:
    """`checkpoints_dir`'s last component, which is also what a `Sink` records.

    A name rather than a relative path because the folder is a child of the
    project directory by construction — so there is nothing to compute against a
    base, and no drive boundary for a relative path to fail to cross.
    """
    return f"{video.stem}{CHECKPOINTS_SUFFIX}"


def replicate_dir(base: Path, replicate: Replicate | None) -> Path:
    """Where one replicate's files go under the checkpoint folder."""
    return base / (BASELINE_DIR if replicate is None else replicate.replicate_id)


class CheckpointWriter:
    """One replicate's checkpointed nodes, filled frame by frame and then closed.

    The lifecycle is the whole contract: `record` once per frame of the span in
    order, then `close` for the sink records, and `abandon` — idempotent, and a
    no-op after `close` — for every path that does not get there. A caller that
    stops early has written nothing, which is the point.
    """

    def __init__(
        self,
        video: Path,
        *,
        project_dir: Path,
        kept: Mapping[str, Kept],
        span: SourceSpan,
        replicate: Replicate | None = None,
    ) -> None:
        """Prepare to write, without touching the filesystem yet.

        Args:
            video: The footage the project is about. Names the folder only.
            project_dir: What the recorded sink paths are relative to.
            kept: Checkpointed `node_id` to that node's key and product. The
                mapping's key set *is* the checkpoint list — order is preserved
                into the manifest.
            span: The source frames the run answers for, which is `plan.span`
                and not what the caller asked for: a selecting node narrows it,
                and a file sized on the wider range would end in zeros.
            replicate: Whose run this is, or `None` for the baseline.

        Raises:
            CheckpointWriteError: if `kept` is empty — a writer with nothing to
                write would create an empty folder and report success — or if a
                node id cannot be a file name.
        """
        if not kept:
            raise CheckpointWriteError("a checkpoint writer was built with no checkpointed nodes")
        # The schema's rule checked a second time rather than a second rule: a
        # document is refused at load for an id that cannot be a file name, and
        # ids also reach here from callers that assembled a mapping instead of
        # loading one. A regex match per checkpointed node, once per run.
        for node_id in kept:
            if not NODE_ID_PATTERN.match(node_id):
                raise CheckpointWriteError(
                    f"node id {node_id!r} is checkpointed but cannot be a file name; ids reaching "
                    "the filesystem must be alphanumerics, dots, dashes and underscores"
                )
        self._name = checkpoints_name(video)
        self._directory = replicate_dir(project_dir / self._name, replicate)
        self._kept = dict(kept)
        self._span = span
        self._replicate = replicate
        self._arrays: dict[str, NDArray[Any]] = {}
        self._layout: dict[str, tuple[str, tuple[int, ...]]] = {}
        self._next = span.start
        self._closed = False

    def record(self, index: int, outputs: Mapping[str, Frame]) -> None:
        """File every checkpointed node's output for source frame `index`.

        In order and without gaps, which is what the executor yields and what a
        pre-sized array requires: a row skipped would stay the zeros it was
        created as, and nothing downstream could tell that from a black frame.

        Args:
            index: The source frame these outputs answer for.
            outputs: `FrameResult.outputs` — every node's output for that frame.

        Raises:
            CheckpointWriteError: if `index` is not the next frame of the span,
                if a checkpointed node produced no output, or if a frame's shape
                or element type disagrees with the file already opened for it.
        """
        if self._closed:
            raise CheckpointWriteError(f"{self._directory} was closed; frame {index} came after it")
        if index != self._next:
            raise CheckpointWriteError(
                f"checkpoints are filled in order: frame {self._next} was expected "
                f"and frame {index} arrived"
            )
        if not self._arrays:
            self._open(outputs, index)
        for node_id, array in self._arrays.items():
            frame = _output(outputs, node_id, index)
            if (frame.data.shape, frame.data.dtype) != (array.shape[1:], array.dtype):
                raise CheckpointWriteError(
                    f"{node_id} answered frame {index} as {frame.data.shape} {frame.data.dtype} "
                    f"but its checkpoint was opened at {array.shape[1:]} {array.dtype} — a "
                    "checkpoint is one array and its geometry cannot change mid-span"
                )
            array[index - self._span.start] = frame.data
        self._next += 1

    def close(self) -> tuple[Sink, ...]:
        """Rename every part file into place, write the manifest, report.

        Returns:
            One `Sink` per checkpointed node, in the order they were given:
            which node was written, in what format, and into which folder
            relative to the project file. A directory rather than a file for
            `Sink.path`'s stated reason — a sink under fan-out produces one
            output per replicate, and these are those.

        Raises:
            CheckpointWriteError: if the span was not filled. The part files are
                removed first, so a short run leaves nothing a later session
                could mistake for a whole result.
        """
        if self._next != self._span.end:
            missing = self._span.end - self._next
            self.abandon()
            raise CheckpointWriteError(
                f"the run ended {missing} frames before the end of [{self._span.start}:"
                f"{self._span.end}), so no checkpoint was written"
            )
        # Before the renames, not after: on Windows a mapped file cannot be
        # replaced, and a rename that half-succeeded would leave one node's
        # result in place and the next node's beside it under a part name.
        self._release()
        for node_id in self._kept:
            self._part(node_id).replace(self._final(node_id))
        (self._directory / MANIFEST_NAME).write_text(
            yaml.safe_dump(self._manifest(), sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
        self._closed = True
        return tuple(
            Sink(node_id=node_id, format=CHECKPOINT_FORMAT, path=self._name)
            for node_id in self._kept
        )

    def abandon(self) -> None:
        """Drop everything written so far. Idempotent, and a no-op after `close`.

        The failure path of every caller, which is why it swallows the unlink
        rather than raising: it runs while another exception is propagating, and
        a file the operating system will not delete is not the failure worth
        reporting there. What is left behind is a `.part.npy`, which nothing
        reads and the next run of the same checkpoint overwrites.
        """
        if self._closed:
            return
        self._release()
        for node_id in self._kept:
            try:
                self._part(node_id).unlink(missing_ok=True)
            except OSError:
                continue

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Abandon whatever was not closed — the rule, stated once."""
        self.abandon()

    # ---- internals -------------------------------------------------------

    def _open(self, outputs: Mapping[str, Frame], index: int) -> None:
        """Size and create one part file per checkpointed node.

        On the first frame rather than in `__init__`, because the shape and
        element type of a node's output are facts about what it computed and no
        declaration on the tool states them.
        """
        self._directory.mkdir(parents=True, exist_ok=True)
        for node_id in self._kept:
            data = _output(outputs, node_id, index).data
            self._arrays[node_id] = open_memmap(
                self._part(node_id),
                mode="w+",
                dtype=data.dtype,
                shape=(self._span.frame_count, *data.shape),
            )
            self._layout[node_id] = (str(data.dtype), tuple(int(size) for size in data.shape))

    def _release(self) -> None:
        """Unmap every open file, so it can be renamed or removed."""
        for array in self._arrays.values():
            array.flush()
        self._arrays.clear()

    def _part(self, node_id: str) -> Path:
        return self._directory / f"{self._stem(node_id)}.part.npy"

    def _final(self, node_id: str) -> Path:
        return self._directory / f"{self._stem(node_id)}.npy"

    def _stem(self, node_id: str) -> str:
        """Node and product, which is what makes two products two files.

        Both parts follow the tool-id spelling rule — `NODE_ID_PATTERN` above,
        `Emission.name`'s own check — so the join needs no quoting and the name
        cannot depend on case folding. Nothing parses it back: the manifest
        names the file, and this is what a reviewer reads in the folder and what
        a read-back root's identity carries (this module's header).
        """
        return f"{node_id}.{self._kept[node_id].emission}"

    def _manifest(self) -> dict[str, Any]:
        """What a reader needs to know what these files are.

        The cache key is here and the display name is here, and neither is in a
        path: the key because a checkpoint may never enter one (`cache_key.py`),
        the name because it is not identity. The product is in both, and the
        header says why it is the one fact that must also be in the name.
        """
        return {
            "manifest_version": MANIFEST_VERSION,
            "replicate_id": None if self._replicate is None else self._replicate.replicate_id,
            "replicate_name": None if self._replicate is None else self._replicate.name,
            "span": {"start": self._span.start, "end": self._span.end},
            "entries": [
                {
                    "node_id": node_id,
                    "key": self._kept[node_id].key,
                    "emission": self._kept[node_id].emission,
                    "file": self._final(node_id).name,
                    "format": CHECKPOINT_FORMAT,
                    "dtype": self._layout[node_id][0],
                    "shape": [self._span.frame_count, *self._layout[node_id][1]],
                }
                for node_id in self._kept
            ],
        }


def _output(outputs: Mapping[str, Frame], node_id: str, index: int) -> Frame:
    """One node's output for a frame, or the refusal.

    Raises:
        CheckpointWriteError: if the node produced nothing. A `KeyError` would
            be right and would name only the id; what a caller needs is that a
            *checkpointed* node is missing, which is a project naming a node the
            plan did not compute.
    """
    frame = outputs.get(node_id)
    if frame is None:
        raise CheckpointWriteError(
            f"{node_id} is checkpointed but produced no output for frame {index}"
        )
    return frame
