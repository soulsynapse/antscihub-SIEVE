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

**Keyed by pts and form, because there is no array here.** ADR-0004 admits an
ordinal only as a per-store coordinate — row *i* of an array, with a table
saying what row *i* means. A dict has no rows, so it keeps the identity that
is already durable and skips the table. The tier that does hold arrays is
where that coordinate comes back.

The form is half the key for the reason `experiments/tool-experiments/tools.py`
gives about `residency`: what is held is an input *in a form*, two consumers at
different forms need different arrays of one instant, and a store keyed by
position alone would think one satisfied the other. Keyed by position alone,
this held the whole 5.3K picture and re-decoded the crop somebody actually
wanted on every ask.

**Listed and delivered are recorded apart, and only one refusal is a hole.**
`missing` keeps what a source said it could not deliver, rather than inferring
it from an absence — the reason `experiments/tool-experiments/series.py` gives
about coverage: a value nobody wrote and a value that is genuinely nothing are
the same picture once the record is thrown away. Only `Refusal.GONE` goes in
it. `LATER` is a moment, and filing it would answer the same way forever on
the strength of one instant; `FORM` is about the shape asked for and says
nothing about the position at all.

**The extent is asked, never stored.** `Extent` is documented as a query
rather than a constant and this held it as a constant, which made a folder
that grew from twelve stills to thirteen invisible to everything above here
(`docs/findings/2026.08.29-what-two-more-sources-found-the-contract-cannot-say.md`).
The tiers this ports from had the discipline already: `SignalStrip` takes its
coverage as an injected callable and `SegmentProxy.refresh` re-scans rather
than caching what it found.

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
from sieve.contract.nodes import Answer, Opened, Output, Refusal, read_form

#: Frames held decoded, at the source's own form. One 5312x2988 BGR frame is
#: 47.6 MB, so this is a handful and not a window: what the storage plan holds
#: by the hundred is a *crop* at the level of interest, and a tier that
#: memoised source frames would be a gigabyte for twenty of them. Small until
#: there is a form worth holding, rather than a number tuned against a file.
DEFAULT_BUDGET = 4

#: How far `first_start` will walk before giving up. It walks starts
#: now rather than every position, so this is generous: a source whose
#: declared starts refuse this many times is wrong about its own structure,
#: which no amount of further walking repairs.
WALK_LIMIT = 240


class Frames:
    """Budget-capped LRU of decoded frames, keyed by pts and form.

    Ported from the storage explorer's `Store`, whose rule holds here: the
    lock exists for the fill thread, and every operation under it is a dict
    touch and never a decode. A lock a decode runs inside is the fill thread
    stalling whoever is drawing, which is the freeze this whole shelf exists
    to avoid.
    """

    def __init__(self, budget: int = DEFAULT_BUDGET) -> None:
        self.budget = max(1, budget)
        self._held: OrderedDict[tuple[int, str], Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, position: int, form: Form) -> Any | None:
        key = (position, form.key())
        with self._lock:
            if key not in self._held:
                return None
            self._held.move_to_end(key)
            return self._held[key]

    def put(self, position: int, form: Form, frame: Any) -> None:
        key = (position, form.key())
        with self._lock:
            self._held[key] = frame
            self._held.move_to_end(key)
            while len(self._held) > self.budget:
                self._held.popitem(last=False)

    def covered(self, positions: tuple[int, ...], form: Form) -> tuple[int, ...]:
        """Which of *positions* are held at *form*, in the order given.

        One pass under the lock rather than a `get` apiece, because the
        callers are a fill reporting what it landed and a drag looking for
        something near: both ask about a window at once, and asking six
        hundred times is six hundred acquisitions of a lock the fill thread
        wants back. It answers with positions and not frames deliberately —
        a caller that wanted the arrays would be holding a window's worth
        outside the budget that caps them.
        """
        key = form.key()
        with self._lock:
            return tuple(p for p in positions if (p, key) in self._held)

    def set_budget(self, budget: int) -> None:
        with self._lock:
            self.budget = max(1, budget)
            while len(self._held) > self.budget:
                self._held.popitem(last=False)

    def wipe(self) -> None:
        """Drop everything. What a form change calls before the rect moves."""
        with self._lock:
            self._held.clear()

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
        #: positions the source will never deliver — recorded, never inferred,
        #: and only ever `Refusal.GONE`
        self.missing: set[int] = set()

    @property
    def positions(self) -> tuple[int, ...]:
        """What the source lists, asked now.

        A property and not a field: an open extent moves, and a caller holding
        a tuple from open time is holding a number that was true then. Costs a
        `listdir` on a directory source and a tuple hand-back on a container,
        which is cheap enough that caching it would trade correctness for
        nothing.
        """
        if self.output.extent is None:
            return ()
        return self.output.extent().listed

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

    def answer(self, position: int, want: Form | None = None) -> Answer:
        """A frame at *position* in *want*, from the held ones if it is there.

        `GONE` is remembered, so a second ask does not re-pay a seek to be
        told the same thing. `LATER` and `FORM` are not: the first is a moment
        and the second is about the shape, and caching either turns one
        refusal into a permanent answer. That distinction is the whole of why
        `Refusal` exists — before it, a forward-only source that refused once
        was filed as a hole and never asked again.

        Everything goes through `read_form`, which asks the source for the
        wanted form first and falls back to the canonical construction only
        where it will not serve one.
        """
        wanted = self.form if want is None else want
        if position in self.missing:
            return Answer(refusal=Refusal.GONE)
        held = self.frames.get(position, wanted)
        if held is not None:
            return Answer(held)
        answered = read_form(self.output, position, wanted)
        if answered.refusal is Refusal.GONE:
            self.missing.add(position)
        elif answered.delivered:
            self.frames.put(position, wanted, answered.frame)
        return answered

    def frame(self, position: int, want: Form | None = None) -> Any | None:
        """The array, or None however it was refused. For a caller that draws.

        Kept beside `answer` because whatever puts pixels on a screen has one
        branch: there is something to draw or there is not. A caller that
        schedules, records coverage, or decides whether to ask again wants
        `answer` — and this is the shorter name, so the shorter name is the
        one that loses information.
        """
        return self.answer(position, want).frame

    def starts(self) -> tuple[int, ...]:
        """Where a read may begin, as the source says. Every position if not.

        `None` from a source means it draws no such distinction, and treating
        every listed position as a start is what that says.
        """
        if self.output.starts is None:
            return self.positions
        return self.output.starts()

    def first_start(self, limit: int = WALK_LIMIT) -> int | None:
        """The first position a read may begin at that actually reads back.

        Not the first deliverable position, and the difference is the point.
        Walking the extent from its head is how this used to find one, and on
        `video-tests/GX010047c2_02_17_26.MP4` that was twenty refusals at
        ~300 ms apiece — 7.9 s before a first picture, spent learning what the
        tool already knew. Asking `starts` skips the cut-away prefix entirely
        and lands in 436 ms.

        What it gives up is exactness at the head: that file's pts 0 does read
        back, by decoding forward from a keyframe, and this returns pts 4004
        instead because pts 0 is not a start. Finding the earlier one costs the
        walk this exists to avoid, and nothing yet asks for the earliest frame
        rather than a frame — when something does, it asks for a position and
        gets it.

        Still a walk, and still bounded, because a start is a structural claim
        and not a promise: a truncated file lists a keyframe whose packets are
        not all there, and one of this file's does. `limit` caps it so a source
        wrong throughout gives up rather than reading itself entirely.
        """
        candidates = self.starts() or self.positions
        for position in candidates[: limit or len(candidates)]:
            if self.answer(position).delivered:
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
