"""What SIEVE has on hand from one open recording.

The substrate's first job in ADR-0009's list — getting frames in a named form
— and the tier the storage experiments measured. This is its ground floor:
one open source, the positions it lists, and a budget of frames already
decoded. The tiers above it (`ChunkStore`, `WindowFill`, the display proxy,
the keyframe strip) are built and measured in
`experiments/storage-experiments/session-explorer.py` and land on this.

**Opening is expensive and that is settled, not accidental.** ADR-0004 has
the frame table built by demuxing the source at open, decoding nothing, so a
source that answers `extent()` has already paid for the whole file. `open`
therefore blocks for as long as the file takes and must not be called on a
thread anything draws from; `opened` is the callable a worker runs.

**Keyed by pts, because there is no array here.** ADR-0004 admits an ordinal
only as a per-store coordinate — row *i* of an array, with a table saying
what row *i* means. A dict has no rows, so it keeps the identity that is
already durable and skips the table. The tier that does hold arrays is where
that coordinate comes back.

**Listed and delivered are recorded apart.** `read` returning `None` is the
source admitting it cannot supply something its own extent listed, which the
mid-GOP footage in `video-tests/` produces on the first frames of the file.
`missing` is that fact kept rather than inferred from an absence, for the
reason `experiments/tool-experiments/series.py` states about coverage: a
value nobody wrote and a value that is genuinely nothing are the same picture
once the record is thrown away.

Nothing here imports Qt. Threads are the caller's to own, and the rule they
owe this module is below.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from sieve.contract import Tool
from sieve.contract.edges import FRAME
from sieve.contract.forms import Form
from sieve.contract.nodes import Opened, Output, read_form

#: Frames held decoded, at the source's own form. One 5312x2988 BGR frame is
#: 47.6 MB, so this is a handful and not a window: what the storage plan holds
#: by the hundred is a *crop* at the level of interest, and a tier that
#: memoised source frames would be a gigabyte for twenty of them. Small until
#: there is a form worth holding, rather than a number tuned against a file.
DEFAULT_BUDGET = 4

#: How far `first_deliverable` will walk before giving up. A leading run of
#: undeliverable positions is a cut prefix — packets referencing a keyframe
#: the file does not contain — and is bounded by one GOP, so a file still
#: answering None past this is missing for a reason walking will not fix.
WALK_LIMIT = 240


class Frames:
    """Budget-capped LRU of decoded frames, keyed by pts.

    Ported from the storage explorer's `Store`, whose rule holds here: the
    lock exists for the fill thread, and every operation under it is a dict
    touch and never a decode. A lock a decode runs inside is the fill thread
    stalling whoever is drawing, which is the freeze this whole shelf exists
    to avoid.
    """

    def __init__(self, budget: int = DEFAULT_BUDGET) -> None:
        self.budget = max(1, budget)
        self._held: OrderedDict[int, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, position: int) -> Any | None:
        with self._lock:
            if position not in self._held:
                return None
            self._held.move_to_end(position)
            return self._held[position]

    def put(self, position: int, frame: Any) -> None:
        with self._lock:
            self._held[position] = frame
            self._held.move_to_end(position)
            while len(self._held) > self.budget:
                self._held.popitem(last=False)

    def set_budget(self, budget: int) -> None:
        with self._lock:
            self.budget = max(1, budget)
            while len(self._held) > self.budget:
                self._held.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._held)


class Store:
    """One open recording: what it lists, what it has answered, what it held.

    Not thread-safe beyond `Frames`, because `Opened` is not: the contract
    says one per address per session, so exactly one thread may call `frame`.
    Today that is the GUI thread and every read is an exact request the user
    just released, which is the one thing
    `docs/findings/2026.08.22-what-froze-the-felt-loop.md` permits it to
    block on. A fill tier arriving later brings its own opened source rather
    than sharing this one.
    """

    def __init__(self, tool: Tool, opened: Opened, output: Output) -> None:
        self.tool = tool
        self.opened = opened
        self.output = output
        self.frames = Frames()
        #: listed by the source; ascending, and closed for a file
        self.positions: tuple[int, ...] = ()
        #: listed but not deliverable — recorded, never inferred
        self.missing: set[int] = set()
        extent = output.extent() if output.extent is not None else None
        if extent is not None:
            self.positions = extent.listed

    @property
    def address(self) -> str:
        return self.opened.address

    @property
    def form(self) -> Form:
        """The source's own form — whole frame, source sampling, as decoded."""
        return self.output.edge.spec.form

    @property
    def aspect(self) -> float:
        width, height = self.form.out
        return width / height if height else 0.0

    def frame(self, position: int, want: Form | None = None) -> Any | None:
        """A frame at *position*, from the held ones if it is there.

        `None` means the source could not deliver a position it listed, and
        is remembered in `missing` so a second ask does not re-pay the decode
        to be told the same thing. Anything other than the source's own form
        goes through `read_form`, which is the one path that makes two
        producers of one form agree in the low bits.
        """
        if position in self.missing:
            return None
        if want is None or want == self.form:
            held = self.frames.get(position)
            if held is not None:
                return held
            frame = self.output.read(position)
            if frame is None:
                self.missing.add(position)
                return None
            self.frames.put(position, frame)
            return frame
        frame = read_form(self.output, position, want)
        if frame is None:
            self.missing.add(position)
        return frame

    def first_deliverable(self, limit: int = WALK_LIMIT) -> int | None:
        """The first listed position that actually reads back. Expensive.

        A file cut mid-GOP lists frames whose packets reference a keyframe it
        does not contain, and each one costs a full seek to be told so: on
        `video-tests/GX010047c2_02_17_26.MP4` the extent opens at pts -20020
        and the first twenty positions read back None at ~300 ms apiece, so
        this walk is seconds before a first picture. That is the honest price
        of the contract's split between listed and deliverable, and the tier
        that stops anyone paying it in front of a user is the keyframe strip
        the storage plan puts first — downscaled keyframes for orientation
        before anything else exists. Until that tier exists, this runs on
        whatever thread opened the source and never on one that draws.
        """
        for position in self.positions[: limit or len(self.positions)]:
            if self.frame(position) is not None:
                return position
        return None

    def close(self) -> None:
        self.opened.close()


def opened(tool: Tool, address: str) -> Store:
    """Open *address* with *tool*. Blocks for the frame table; not for a GUI thread.

    Raises whatever the tool raises. A source that opens but offers no frame
    edge is the failure `Source.offers` declares away, so it is an error here
    rather than a `Store` that answers nothing: the tool said frames and did
    not bring one.
    """
    handle = tool.role.open(address)
    for output in handle.outputs.values():
        if output.edge.kind == FRAME:
            return Store(tool, handle, output)
    handle.close()
    raise ValueError(f"{tool.name} offered no frame edge for {address}")
