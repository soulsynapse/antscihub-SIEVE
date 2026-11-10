"""The drawing's state with no window: the shapes, the one selected, the drawing mode and the gesture
under way, driven by presses, moves and releases at plate points. `px` on each call is plate pixels
per screen pixel, so a handle is hit at a fixed size on screen whatever the zoom."""
import math

from . import shapes as sh

MODES = ("select", "circle", "circle3", "square", "rectangle", "polygon")
HANDLE_PX = 6     # half a handle's side on screen, and the reach of a click on one
ROTATE_PX = 24    # how far above its top edge a shape's rotation handle stands
DRAG_PX = 4       # a press released further than this is a drag, closing a two-point shape on release


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

    def delete_selected(self):
        if self.selected is not None:
            self.shapes = [s for s in self.shapes if s.name != self.selected]
            self.selected = None
            self._changed()

    def _clamp(self, p):
        if self.plate is None:
            return tuple(p)
        h, w = self.plate
        return (min(max(0.0, p[0]), w), min(max(0.0, p[1]), h))

    def _name(self, kind):
        return sh.next_name(kind, {s.name for s in self.shapes})

    def press(self, p, px, button="left"):
        p = tuple(p)
        if self.mode == "select":
            self._press_select(p, px, button)
        elif button == "left":
            self._press_draw(self._clamp(p), px)
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
        self._changed()

    def finish(self):
        """Closes a polygon under way of three or more vertices."""
        if self.mode == "polygon" and len(self.pending) >= 3:
            self._add(sh.Polygon(self._name("polygon"), tuple(self.pending)))
        self.pending = []
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
                self._add(sh.circle_through(self._name("circle"), *self.pending))
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
        make = {"circle": sh.circle_from_centre, "square": sh.square_from_diagonal,
                "rectangle": sh.rectangle_from_corners}[self.mode]
        new = make(self._name(self.mode), a, p)
        if self.mode != "rectangle" or (new.w >= sh.MIN_SIZE and new.h >= sh.MIN_SIZE):
            self._add(new)

    def preview(self):
        """The shape the gesture under way would make at the cursor, or None."""
        if not self.pending or self.cursor is None:
            return None
        a, p = self.pending[0], self.cursor
        if self.mode == "circle":
            return sh.circle_from_centre("", a, p)
        if self.mode == "square":
            return sh.square_from_diagonal("", a, p)
        if self.mode == "rectangle":
            return sh.rectangle_from_corners("", a, p)
        if self.mode == "circle3" and len(self.pending) == 2:
            return sh.circle_through("", *self.pending, p)
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
        if what == "move":
            new = origin.moved(p[0] - arg[0], p[1] - arg[1])
        elif what == "handle":
            new = origin.dragged(arg, p)
        else:
            c = origin.centre
            new = origin.rotated(math.atan2(p[1] - c[1], p[0] - c[0]) - arg)
        self._replace(new)
