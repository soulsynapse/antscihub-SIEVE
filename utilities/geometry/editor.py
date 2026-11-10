"""The drawing's state with no window: the shapes, the one selected, the drawing mode and the gesture
under way, driven by presses, moves and releases at plate points. `px` on each call is plate pixels
per screen pixel, so a handle is hit at a fixed size on screen whatever the zoom. With a plate set,
a shape drawn, or edited from within the plate, is held within it; a shape already past its edge
moves free."""
import math
from dataclasses import replace

from . import shapes as sh

MODES = ("select", "circle", "circle3", "square", "rectangle", "polygon")
HANDLE_PX = 6     # half a handle's side on screen, and the reach of a click on one
ROTATE_PX = 24    # how far above its top edge a shape's rotation handle stands
DRAG_PX = 4       # a press released further than this is a drag, closing a two-point shape on release
HOLD_STEPS = 40   # bisections finding how far toward the cursor a gesture goes before the edge


def _toward(a, b, t):
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


class Editor:
    """`on_change`, when set, is called after anything a view would draw differently."""

    def __init__(self, plate=None):
        self.plate = plate
        self.shapes = []
        self.selected = None
        self.mode = "select"
        self.pending = []
        self.cursor = None
        self._drag = None
        self._press = None
        self._undo, self._redo = [], []
        self._saved = ()
        self.on_change = None

    def _changed(self):
        if self.on_change is not None:
            self.on_change()

    def set_mode(self, mode):
        if mode not in MODES:
            raise ValueError(f"{mode!r} is not one of {MODES}")
        self.mode, self.pending, self._drag = mode, [], None
        self._changed()

    def shape(self, name):
        return next((s for s in self.shapes if s.name == name), None)

    @property
    def current(self):
        return self.shape(self.selected) if self.selected is not None else None

    def rotation_handle(self, px):
        s = self.current
        if s is None or s.kind == "circle":
            return None
        (x, y), (ux, uy) = s.top()
        return (x + ux * ROTATE_PX * px, y + uy * ROTATE_PX * px)

    def _replace(self, new):
        self.shapes = [new if s.name == new.name else s for s in self.shapes]

    def _add(self, new):
        if new is None:
            return
        self.shapes.append(new)
        self.selected = new.name

    def select(self, name):
        """Selects the shape of that name, or none for None or a name no shape holds."""
        self.selected = name if self.shape(name) is not None else None
        self._changed()

    def rename(self, old, new):
        """False, nothing changed, when `new` is empty or another shape's name; a selection follows
        the rename."""
        s = self.shape(old)
        if s is None or not isinstance(new, str) or not new or (new != old and self.shape(new) is not None):
            return False
        if new != old:
            self.shapes = [replace(t, name=new) if t is s else t for t in self.shapes]
            if self.selected == old:
                self.selected = new
            self._commit()
            self._changed()
        return True

    def delete_selected(self):
        if self.selected is not None:
            self.shapes = [s for s in self.shapes if s.name != self.selected]
            self.selected = None
            self._commit()
            self._changed()

    def _commit(self):
        """Ends an undo step at the shapes as they now are, when they differ from the last step's end."""
        now = tuple(self.shapes)
        if now != self._saved:
            self._undo.append(self._saved)
            self._redo.clear()
            self._saved = now

    def undo(self):
        """Back one step; a gesture under way is dropped first."""
        self._step(self._undo, self._redo)

    def redo(self):
        self._step(self._redo, self._undo)

    def _step(self, src, dst):
        self._drag, self.pending = None, []
        if src:
            dst.append(self._saved)
            self._saved = src.pop()
        self.shapes = list(self._saved)
        if self.current is None:
            self.selected = None
        self._changed()

    def _clamp(self, p):
        if self.plate is None:
            return tuple(p)
        h, w = self.plate
        return (min(max(0.0, p[0]), w), min(max(0.0, p[1]), h))

    def within(self, s):
        if self.plate is None:
            return True
        h, w = self.plate
        x0, y0, x1, y1 = s.box()
        return x0 >= 0 and y0 >= 0 and x1 <= w and y1 <= h

    def _held(self, make):
        """`make(1)` when it is within the plate or `make(0)`, the gesture's start, is not; otherwise
        `make(t)` at the largest t bisection finds within."""
        whole = make(1.0)
        if self.within(whole) or not self.within(make(0.0)):
            return whole
        lo, hi = 0.0, 1.0
        for _ in range(HOLD_STEPS):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if self.within(make(mid)) else (lo, mid)
        return make(lo)

    def _limited(self, c):
        """`c` with its radius cut to the room its centre has to the plate's edges; None when that
        is under MIN_SIZE."""
        if self.plate is None:
            return c
        h, w = self.plate
        r = min(c.r, c.cx, c.cy, w - c.cx, h - c.cy)
        out = sh.Circle(c.name, c.cx, c.cy, r)
        if not self.within(out):
            out = sh.Circle(c.name, c.cx, c.cy, r * (1 - 1e-12))
        return out if out.r >= sh.MIN_SIZE else None

    def _name(self, kind):
        return sh.next_name(kind, {s.name for s in self.shapes})

    def press(self, p, px, button="left"):
        p = tuple(p)
        if self.mode == "select":
            self._press_select(p, px, button)
        elif button == "left":
            self._press_draw(self._clamp(p), px)
        if self._drag is None:
            self._commit()
        self._changed()

    def move(self, p, px):
        p = tuple(p)
        self.cursor = self._clamp(p)
        if self._drag is not None:
            self._apply_drag(p)
        self._changed()

    def release(self, p, px):
        p = tuple(p)
        if self._drag is not None:
            self._apply_drag(p)
            self._drag = None
        elif (self.mode in ("circle", "square", "rectangle") and len(self.pending) == 1 and self._press is not None
              and math.dist(self._press, p) > DRAG_PX * px):
            self._finish_two(self._clamp(p))
        self._press = None
        self._commit()
        self._changed()

    def finish(self):
        """Closes a polygon under way of three or more vertices."""
        if self.mode == "polygon" and len(self.pending) >= 3:
            self._add(sh.Polygon(self._name("polygon"), tuple(self.pending)))
        self.pending = []
        self._commit()
        self._changed()

    def cancel(self):
        """Drops a shape under way, or with none returns to select."""
        if self.pending:
            self.pending = []
        else:
            self.mode = "select"
        self._changed()

    def _press_draw(self, p, px):
        self._press = p
        if self.mode == "circle3":
            self.pending.append(p)
            if len(self.pending) == 3:
                self._add(self._drawn("circle3", self._name("circle"), self.pending[0], self.pending[2]))
                self.pending = []
        elif self.mode == "polygon":
            if len(self.pending) >= 3 and math.dist(p, self.pending[0]) <= HANDLE_PX * px:
                self.finish()
            else:
                self.pending.append(p)
        elif not self.pending:
            self.pending = [p]
        else:
            self._finish_two(p)

    def _finish_two(self, p):
        a = self.pending[0]
        self.pending = []
        if math.dist(a, p) < sh.MIN_SIZE:
            return
        new = self._drawn(self.mode, self._name(self.mode), a, p)
        if new is not None and (new.kind != "rectangle" or (new.w >= sh.MIN_SIZE and new.h >= sh.MIN_SIZE)):
            self._add(new)

    def _drawn(self, mode, name, a, p):
        """The shape `mode` makes from its first point `a` and its last `p`, held within the plate,
        or None; a three-point circle's middle point is `pending[1]`."""
        if mode == "circle":
            return self._limited(sh.circle_from_centre(name, a, p))
        if mode == "circle3":
            c = sh.circle_through(name, a, self.pending[1], p)
            return None if c is None else self._limited(c)
        if mode == "square":
            return self._held(lambda t: sh.square_from_diagonal(name, a, _toward(a, p, t)))
        return sh.rectangle_from_corners(name, a, p)

    def preview(self):
        """The shape the gesture under way would make at the cursor, or None."""
        if not self.pending or self.cursor is None:
            return None
        if self.mode in ("circle", "square", "rectangle") or (self.mode == "circle3" and len(self.pending) == 2):
            return self._drawn(self.mode, "", self.pending[0], self.cursor)
        return None

    def _press_select(self, p, px, button):
        tol = HANDLE_PX * px
        s = self.current
        if s is not None:
            if button == "right" and s.kind == "polygon":
                hit = self._handle_at(s, p, tol)
                if hit is not None:
                    self._replace(s.without_vertex(hit))
                return
            rot = self.rotation_handle(px)
            if button == "left" and rot is not None and math.dist(p, rot) <= tol:
                c = s.centre
                self._drag = ("rotate", s, math.atan2(p[1] - c[1], p[0] - c[0]))
                return
            hit = self._handle_at(s, p, tol)
            if button == "left" and hit is not None:
                self._drag = ("handle", s, hit)
                return
            if button == "left" and s.kind == "polygon":
                edge = s.edge_near(p, tol)
                if edge is not None:
                    s = s.with_vertex(edge, p)
                    self._replace(s)
                    self._drag = ("handle", s, edge + 1)
                    return
        if button != "left":
            return
        under = next((t for t in reversed(self.shapes) if t.contains(p)), None)
        self.selected = under.name if under is not None else None
        if under is not None:
            self._drag = ("move", under, p)

    @staticmethod
    def _handle_at(s, p, tol):
        near = [(math.dist(p, q), k) for k, q in s.handles().items() if math.dist(p, q) <= tol]
        return min(near, key=lambda t: t[0])[1] if near else None

    def _apply_drag(self, p):
        what, origin, arg = self._drag
        held = self.plate is not None and self.within(origin)
        if what == "move":
            dx, dy = p[0] - arg[0], p[1] - arg[1]
            if held:
                h, w = self.plate
                x0, y0, x1, y1 = origin.box()
                dx, dy = min(max(dx, -x0), w - x1), min(max(dy, -y0), h - y1)
            new = self._held(lambda t: origin.moved(t * dx, t * dy))
        elif what == "handle" and origin.kind == "circle":
            new = origin.dragged(arg, p)
            new = (self._limited(new) or origin) if held else new
        elif what == "handle":
            start, q = origin.handles()[arg], self._clamp(p) if held else p
            new = self._held(lambda t: origin.dragged(arg, _toward(start, q, t)))
        else:
            c = origin.centre
            theta = math.remainder(math.atan2(p[1] - c[1], p[0] - c[0]) - arg, 2 * math.pi)
            new = self._held(lambda t: origin.rotated(t * theta))
        self._replace(new)
