"""The recording session: one open recording, its tiers, and its navigation.

Owns the tier stack, the fill, the proxy, the crop, and the position — the
state that used to live on ``MainWindow`` and made it import every storage
module. Nothing here imports Qt; the caller owns the thread boundary and is
responsible for getting callbacks back to whatever thread it draws from.
"""

from __future__ import annotations

from typing import Any, Callable

from sieve.chunks import ChunkStore
from sieve.contract import Tool
from sieve.contract.edges import Access
from sieve.contract.forms import Form
from sieve.fill import Readers, WindowFill, WriteBehind, window_for
from sieve.ordinals import Ordinals
from sieve.pipeline import Binding, Bound, Chain, Node, bind
from sieve.proxy import Proxy, proxy_form
from sieve.series import Series, Sinks
from sieve.serve import Route, Served, Serving
from sieve.store import Store, opened

#: The head's node id. One source for now; a chain naming two would name them
#: apart here, which is why this is a constant and not a literal.
HEAD = "source"

#: Positions a landing claims.
WINDOW = 300

#: What the held frames may weigh.
_CACHE_BYTES = 600_000_000

#: A crop below this on either axis is a slip, not a gesture.
_MIN_CROP = 64

#: Sentinel: leave the picture where it is.
HOLD = object()


class Session:
    """One open recording: its tiers, fill, navigation, and crop.

    Holds no widget and imports no Qt.  The caller owns the thread boundary
    and is responsible for getting callbacks back to whatever thread draws.
    """

    def __init__(self, on_covered: Callable[..., None] | None = None) -> None:
        self._on_covered = on_covered
        self.store: Store | None = None
        self.serving: Serving | None = None
        self.fill: WindowFill | None = None
        self.readers: Readers | None = None
        self.writer: WriteBehind | None = None
        self.crop: Form | None = None
        self.whole: bool = True
        self.at: int | None = None
        self.steps: tuple[Tool, ...] = ()
        self.bound: Bound | None = None
        #: every series written this session, under its own key. Outlives
        #: the binding on purpose: a knob moved and moved back names the
        #: key it named before, and finds the rows it already covered.
        self.sinks = Sinks()
        #: which node's field the canvas is drawing. One at a time; the chain
        #: binds every step whether or not anything is looking at it.
        self.showing: str | None = None
        #: steps that would not bind, and why — reported rather than dropped
        #: silently, which is how a broken tool becomes a missing overlay
        #: nobody can explain.
        self.unbound: tuple[tuple[str, str], ...] = ()
        self.ceiling: float = 0.0

    # -- queries -----------------------------------------------------------

    @property
    def address(self) -> str | None:
        """The address of the open recording, or ``None``."""
        return self.store.address if self.store is not None else None

    @property
    def aspect(self) -> float:
        """Source aspect ratio."""
        if self.store is None:
            return 1.0
        return self.store.aspect

    @property
    def source_form(self) -> Form | None:
        """The source's own form, or ``None`` when nothing is open."""
        return self.store.form if self.store is not None else None

    @property
    def source_size(self) -> tuple[int, int] | None:
        """(width, height) of the source frame, or ``None``."""
        return self.store.form.out if self.store is not None else None

    @property
    def positions(self) -> tuple[int, ...]:
        """Listed positions of the open recording."""
        if self.serving is None:
            return ()
        return self.serving.ordinals.listed

    @property
    def access(self) -> Access:
        """Access pattern of the open source."""
        if self.store is None:
            return Access.RANDOM
        return self.store.output.edge.at.access

    def starts(self) -> tuple[int, ...]:
        """Key-frame starts of the open source."""
        if self.store is None:
            return ()
        return self.store.starts()

    @property
    def has_crop(self) -> bool:
        return self.crop is not None

    def form(self) -> Form:
        """What a fill holds and a chunk is written from."""
        if self.store is None:
            raise RuntimeError("no source is open")
        return self.crop if self.crop is not None else self.store.form

    def shown_form(self) -> Form:
        """What the canvas is asking for — not always what is held."""
        if self.store is None:
            raise RuntimeError("no source is open")
        if self.whole or self.crop is None:
            return self.store.form
        return self.crop

    def shown_aspect(self) -> float:
        """Aspect ratio of whatever the canvas is showing."""
        f = self.shown_form()
        return f.out[0] / f.out[1]

    # -- source lifecycle --------------------------------------------------

    @staticmethod
    def open_source(tool: Tool, address: str) -> tuple:
        """Open *address* with *tool*.  Blocks — call from a worker thread.

        Returns (store, first_frame, first_position, fingerprint).

        The fingerprint is asked here rather than by whoever draws, for the
        same reason the open is: it is the source's own work — two seeks and a
        stat for a file, a hash of names and sizes for a folder of stills —
        and its cost is the tool's to have, not the frame period's. `None`
        from a source with no durable identity, which is a camera.

        Guarded, because the contract does not forbid `fingerprint` raising
        and the caller reports anything out of this as "that recording could
        not be opened" — which would be said about a store that opened and
        decoded a frame, and would drop it unclosed, holding a lock on the
        file the person was just told was unreadable. Identity is a nicety.
        The open is not.
        """
        store = opened(tool, address)
        position = store.first_start()
        frame = None if position is None else store.frame(position)
        try:
            identity = store.opened.fingerprint()
        except Exception:  # noqa: BLE001 — a tool's identity is not its open
            identity = None
        return store, frame, position, identity

    def attach(self, store: Store, tool: Tool | None, address: str) -> None:
        """Wire tiers for a newly opened *store*.  Call from the GUI thread."""
        self.store = store
        self.serving = Serving(store, Ordinals(store.positions))
        self.crop = None
        self.whole = True
        self._rebudget()
        if tool is not None:
            self.serving.chunks = ChunkStore()
            self.writer = WriteBehind(self.serving.chunks)
            self.readers = Readers(tool, address)
            self.serving.proxy = Proxy(
                self.serving.ordinals.listed, store.form, self.readers,
                holes=store.missing,
            )

    def start_proxy(self, position: int | None) -> None:
        """Start or redirect the proxy build around *position*."""
        if self.serving is None or self.serving.proxy is None:
            return
        ordinal = (
            self.serving.ordinals.rank(position) if position is not None else 0
        )
        self.serving.proxy.build(ordinal or 0)

    def close(self) -> None:
        """Tear down everything the recording brought, in safe order."""
        if self.fill is not None:
            self.fill.stop()
            self.fill = None
        if self.writer is not None:
            self.writer.drain()
            self.writer = None
        if self.readers is not None:
            self.readers.close()
            self.readers = None
        if self.serving is not None:
            if self.serving.proxy is not None:
                self.serving.proxy.close()
            if self.serving.chunks is not None:
                self.serving.chunks.destroy()
        self.serving = None
        self.crop = None
        self.whole = True
        self.at = None
        self.steps = ()
        self.bound = None
        self.showing = None
        self.unbound = ()
        self.ceiling = 0.0
        self.sinks.wipe()
        if self.store is not None:
            self.store.close()
            self.store = None

    # -- navigation --------------------------------------------------------

    def guess(self, position: int) -> Any:
        """A drag.  Returns a frame, ``None`` (clear), or :data:`HOLD`."""
        if self.serving is None:
            return HOLD
        self.at = position
        served = self.serving.guess(position, self.shown_form())
        if served.route is Route.HOLD:
            return HOLD
        return served.frame

    def commit(self, position: int) -> Any:
        """A release or step.  Returns a frame, ``None``, or :data:`HOLD`."""
        if self.serving is None:
            return HOLD
        self.at = position
        served = self.serving.commit(position, self.shown_form())
        if served.route is Route.HOLD:
            return HOLD
        return served.frame

    def land(self, position: int) -> Any:
        """A release on the strip: serve and potentially refill.

        Returns a frame, ``None``, or :data:`HOLD`.
        """
        frame = self.commit(position)
        if self.serving is None:
            return frame
        ordinal = self.serving.ordinals.rank(position)
        if ordinal is None:
            return frame
        active = self.serving.active
        if active is not None and active[0] <= ordinal < active[1]:
            return frame
        self._set_window(ordinal)
        return frame

    # -- window fill -------------------------------------------------------

    def _set_window(self, anchor: int) -> None:
        if self.serving is None or self.readers is None or self.writer is None:
            return
        chunks = self.serving.chunks
        if chunks is None:
            return
        listed = self.serving.ordinals.listed
        low, high = window_for(anchor, WINDOW, len(listed))
        if self.serving.active == (low, high):
            return
        if self.fill is not None:
            self.fill.stop(wait=False)
        self.serving.active = (low, high)
        if self.serving.proxy is not None:
            self.serving.proxy.build(anchor)
        self.serving.held_form = self.form()
        self.fill = WindowFill(
            listed, low, high, anchor, self.form(),
            self.store.frames, chunks, self.writer, self.readers,
            on_covered=self._on_covered,
            holes=self.store.missing,
        )
        self.fill.launch()

    # -- crop --------------------------------------------------------------

    def map_crop(self, left: int, top: int, width: int, height: int,
                 view_width: int, view_height: int) -> Form | None:
        """Map a rectangle drawn in view coordinates to a source crop.

        Returns the Form, or ``None`` if no source is open or not showing
        the whole frame.
        """
        if self.store is None or not self.whole:
            return None
        source_w, source_h = self.store.form.out
        across = source_w / max(1, view_width)
        down = source_h / max(1, view_height)
        x, y = round(left * across), round(top * down)
        w, h = round(width * across), round(height * down)
        x = max(0, min(x, source_w - _MIN_CROP))
        y = max(0, min(y, source_h - _MIN_CROP))
        w = max(_MIN_CROP, min(w, source_w - x))
        h = max(_MIN_CROP, min(h, source_h - y))
        x, y, w, h = (value - value % 2 for value in (x, y, w, h))
        return Form((x, y, w, h), (w, h), "gray")

    def apply_crop(self, crop: Form) -> None:
        """Stop fill, drain writer, wipe caches, set crop."""
        if self.fill is not None:
            self.fill.stop()
            self.fill = None
        if self.writer is not None:
            self.writer.drain()
        if self.serving is not None:
            self.serving.active = None
            self.serving.held_form = None
        if self.store is not None:
            self.store.frames.wipe()
        if self.serving is not None and self.serving.chunks is not None:
            self.serving.chunks.wipe()
        self.crop = crop
        self.whole = False
        self.ceiling = 0.0
        self._rebudget()
        # The crop is half of what a step's values are filed under, so a new
        # one is a new binding and a new store to write into, not the old one
        # looked at differently.
        self._rebind()

    def toggle_whole(self) -> bool:
        """Toggle between crop and whole-frame view.  Returns new *whole*."""
        if self.store is None or self.crop is None:
            return self.whole
        self.whole = not self.whole
        return self.whole

    # -- steps -------------------------------------------------------------

    def set_steps(self, steps: tuple[Tool, ...]) -> None:
        """Place every loaded step in the chain, each fed by the source.

        A fan off the head rather than a chain, and that is not a limitation
        of the binding: nothing in this tree consumes a value, so every step
        here wants frames and one fed another step's output is refused. What
        this replaces is `steps[0]` being the pipeline and the rest being
        cards.
        """
        self.steps = steps
        self.ceiling = 0.0
        self._rebind()

    def _rebind(self) -> None:
        """Build the chain and resolve it against the open source.

        Called again whenever the crop moves: a step's wanted form follows the
        crop, and a form is half of what its values are filed under, so a new
        crop is a new binding rather than the same one looked at differently.
        """
        self.bound = None
        self.showing = None
        self.unbound = ()
        # The binding that held these is gone. They stay under their keys:
        # what is being rebuilt is usually the same chain at a new knob,
        # and the old knob is a place this comes back to.
        self.sinks.release()
        if self.store is None or not self.steps:
            return
        head = self.store.output
        heads = {HEAD: {head.edge.name: head}}
        rect = self.form().rect

        # Each step probed on its own, so one that cannot bind is named
        # rather than taking the others down with it. An authored chain
        # should refuse to run whole; this fan is assembled out of whatever
        # happens to be installed, which is a different thing and is the
        # arrangement the pipeline document exists to replace.
        usable: list[Tool] = []
        refused: list[tuple[str, str]] = []
        for tool in self.steps:
            probe = Chain(
                (Node(HEAD, self.store.tool), Node(tool.name, tool)),
                (Binding(HEAD, head.edge.name, tool.name),))
            try:
                bind(probe, heads, rect, self._sink_for)
            except (ValueError, KeyError) as why:
                refused.append((tool.name, str(why)))
            else:
                usable.append(tool)

        self.unbound = tuple(refused)
        if not usable:
            return
        chain = Chain(
            tuple([Node(HEAD, self.store.tool)]
                  + [Node(tool.name, tool) for tool in usable]),
            tuple(Binding(HEAD, head.edge.name, tool.name) for tool in usable))
        self.bound = bind(chain, heads, rect, self._sink_for)
        self.showing = usable[0].name

    def feeds(self) -> dict[str, str]:
        """Which node feeds which, by name. Empty when nothing is bound.

        Handed over rather than reached for. The drawing needs the shape of
        the chain and nothing else about it, and a caller assembling this
        itself would be reading the pipeline's records two levels deep
        through the session that exists to hold them.
        """
        if self.bound is None:
            return {}
        return {edge.consumer: edge.producer
                for edge in self.bound.chain.bindings}

    def _sink_for(self, node: str, key: str, form: Form,
                  listed: tuple[int, ...], timebase: str) -> Series:
        """Where one node's values are kept, whoever wrote them.

        Out of the session's collection and not built here, so a node
        rebound under a key it has had before is handed the rows it
        already covered rather than an empty array.

        Nothing writes yet: a value is recorded where its inputs landed
        (ADR-0005) and the fill does not run steps, so every row reads back
        `LATER` and the overlay keeps computing its field on the way past
        without recording anything. That is the honest state, not an
        oversight — the recorder is its own piece of work.
        """
        return self.sinks.series(source=self.address or "", step_key=key,
                                 form_key=form.key(), listed=listed,
                                 timebase=timebase)

    def set_ceiling(self, value: float) -> None:
        """Move the overlay's scale top deliberately. 0 re-takes it."""
        self.ceiling = max(float(value), 0.0)

    def step_inputs(self, position: int) -> tuple | None:
        """What the shown step needs at *position*: (step, frames, row).

        Tier reads and nothing else, so it stays on the thread that owns the
        tiers while the arithmetic goes elsewhere. Never blocks: returns
        ``None`` when any needed frame is not resident.

        What is needed is the binding's to say — `Demand` carries the form and
        the positions, already resolved against the listing — and what is
        *held* is this session's. The one thing added here is the bound on the
        form, and it is a display concession rather than part of the
        declaration: the demand's form is the step's own, and this reads it at
        the proxy's long edge instead. Whole-frame that resolves to the
        proxy's form exactly, so a scrub is served from the tier it was
        already being served from; a crop inside the bound stays native. Above
        the bound the read is resampled and `forms.grade` calls it APPROX,
        which is what this field is: drawn, then discarded. A value recorded
        under the demand's own form is a different thing and is not written
        from here (ADR-0005).
        """
        if self.bound is None or self.showing is None or self.serving is None:
            return None
        ordinal = self.serving.ordinals.rank(position)
        if ordinal is None:
            return None
        demand = self.bound.demand(self.showing, ordinal)
        if demand is None:
            return None
        want = proxy_form(demand.form)
        frames: dict[int, Any] = {}
        for row, needed in zip(demand.rows, demand.positions):
            # Through the tiers, not into the cache. The fill holds the whole
            # frame in colour at source sampling and a step wants gray, so an
            # exact key lookup misses every time and `dominator` will not
            # cross a pixel format — whole-frame the answer is the proxy,
            # which is already gray at this very form.
            served = self.serving.exact(needed, want)
            if served.frame is None:
                return None
            frames[row] = served.frame
        return self.bound.chain.node(self.showing).tool.role, frames, demand.row

    @staticmethod
    def run_step(step: Any, frames: Any, ordinal: int) -> tuple:
        """The step's arithmetic. Touches no tier and no session state.

        Separate from `step_inputs` so it can run off the thread that owns
        the tiers. A step that raises is left to raise: guarding it made a
        broken tool indistinguishable from a frame that is not cached yet —
        the overlay simply never appeared and nothing said why.
        """
        field = step.field(frames, ordinal)
        return field, float(step.reduce(field))

    def note_field(self, field: Any) -> None:
        """Take the ceiling from the first honest field, then hold it.

        Held, not autoscaled: later frames are drawn against the first one's
        top, so a still scene does not look as active as a moving one.
        `set_ceiling` moves it.
        """
        if not self.ceiling:
            self.ceiling = max(float(field.max()), 1.0)

    def evaluate_step(self, position: int) -> tuple | None:
        """Inputs then arithmetic, on the calling thread. Returns (field, value)."""
        got = self.step_inputs(position)
        if got is None:
            return None
        field, value = self.run_step(*got)
        self.note_field(field)
        return field, value

    # -- internal ----------------------------------------------------------

    def _rebudget(self) -> None:
        if self.store is None:
            return
        self.store.frames.set_budget(_CACHE_BYTES // max(1, self.form().nbytes))
