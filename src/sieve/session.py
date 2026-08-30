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
from sieve.proxy import Proxy, proxy_form
from sieve.serve import Ordinals, Route, Served, Serving
from sieve.store import Store, opened

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
    def open_source(tool: Tool, address: str) -> tuple[Store, Any | None, int | None]:
        """Open *address* with *tool*.  Blocks — call from a worker thread.

        Returns (store, first_frame, first_position).
        """
        store = opened(tool, address)
        position = store.first_start()
        frame = None if position is None else store.frame(position)
        return store, frame, position

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
        self.ceiling = 0.0
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

    def toggle_whole(self) -> bool:
        """Toggle between crop and whole-frame view.  Returns new *whole*."""
        if self.store is None or self.crop is None:
            return self.whole
        self.whole = not self.whole
        return self.whole

    # -- steps -------------------------------------------------------------

    def set_steps(self, steps: tuple[Tool, ...]) -> None:
        self.steps = steps
        self.ceiling = 0.0

    def set_ceiling(self, value: float) -> None:
        """Move the overlay's scale top deliberately. 0 re-takes it."""
        self.ceiling = max(float(value), 0.0)

    def evaluate_step(self, position: int) -> tuple | None:
        """Run the first loaded step at *position*, returning (field, value).

        Never blocks: returns ``None`` when any needed frame is not cached
        at the step's wanted form. That form is the step's own, bounded to
        the proxy's long edge — whole-frame it is the proxy's form exactly,
        and a crop inside the bound is the fill's, so evaluation succeeds
        once the covering tier has reached the neighbourhood.
        """
        if not self.steps or self.store is None or self.serving is None:
            return None
        step = self.steps[0].role
        rect = self.form().rect
        # Bounded by the same long edge the proxy is built at, which whole-frame
        # resolves to the proxy's own form — the tier a whole-frame view is
        # already served from, rather than a second downscale rule. A crop
        # inside the bound is untouched and stays native; above it the form is
        # resampled and `forms.grade` calls anything from it APPROX, which is
        # what this field is: drawn, then discarded. The series is written
        # where frames are admitted, never from here.
        want = proxy_form(step.form_for(rect))
        ordinal = self.serving.ordinals.rank(position)
        if ordinal is None:
            return None
        listed = self.serving.ordinals.listed
        frames: dict[int, Any] = {}
        for offset in step.offsets:
            needed_ord = ordinal + offset
            if needed_ord < 0 or needed_ord >= len(listed):
                return None
            needed_pos = listed[needed_ord]
            # Through the tiers, not into the cache. The fill holds the whole
            # frame in colour at source sampling and a step wants gray, so an
            # exact key lookup misses every time and `dominator` will not
            # cross a pixel format — whole-frame the answer is the proxy,
            # which is already gray at this very form.
            served = self.serving.exact(needed_pos, want)
            if served.frame is None:
                return None
            frames[needed_ord] = served.frame
        # Not guarded. A step that raises is a broken tool, and swallowing it
        # here makes it indistinguishable from a frame that is not cached yet
        # — the overlay simply never appears and nothing says why.
        field = step.field(frames, ordinal)
        value = float(step.reduce(field))
        if not self.ceiling:
            # Held, not autoscaled: the first honest field sets the top and
            # later frames are drawn against it, so a still scene does not
            # look as active as a moving one. `set_ceiling` moves it.
            self.ceiling = max(float(field.max()), 1.0)
        return field, value

    # -- internal ----------------------------------------------------------

    def _rebudget(self) -> None:
        if self.store is None:
            return
        self.store.frames.set_budget(_CACHE_BYTES // max(1, self.form().nbytes))
