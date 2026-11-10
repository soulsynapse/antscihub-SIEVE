"""The drawing's state with no window: the shapes, the one selected, the drawing mode and the gesture
under way, driven by presses, moves and releases at plate points. `px` on each call is plate pixels
per screen pixel, so a handle is hit at a fixed size on screen whatever the zoom. With a plate set,
a shape drawn, or edited from within the plate, is held within it; a shape already past its edge
moves free. A stamp group holds identical members alone: with its link on, an edit to one other than
a move gives every member the edited form at its own centre, and with it off the edited member
leaves the group at the step's end, as does any member that no longer matches the rest."""
import math
from dataclasses import replace

from . import shapes as sh

MODES = ("select", "circle", "circle3", "square", "rectangle", "polygon", "stamp")
HANDLE_PX = 6     # half a handle's side on screen, and the reach of a click on one
ROTATE_PX = 24    # how far above its top edge a shape's rotation handle stands
DRAG_PX = 4       # a press released further than this is a drag, closing a two-point shape on release
HOLD_STEPS = 40   # bisections finding how far toward the cursor a gesture goes before the edge


def _toward(a, b, t):
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


class Editor:
    """`on_change`, when set, is called after anything a view would draw differently. A new shape is
    named by `stem`, or by its kind while `stem` is empty, and the least free index."""

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
        self.stem = ""
        self.stamp_from = None
        self.links_off = set()

    def _changed(self):
        if self.on_change is not None:
            self.on_change()

    def set_mode(self, mode):
        """"stamp" makes the selected shape the stamp, and is select while none is selected."""
        if mode not in MODES:
            raise ValueError(f"{mode!r} is not one of {MODES}")
        if mode == "stamp":
            self.stamp_from = self.selected
            mode = "stamp" if self.selected is not None else "select"
        self.mode, self.pending, self._drag = mode, [], None
        self._changed()

    def linked(self, s):
        return bool(s.group) and s.group not in self.links_off

    def set_link(self, group, on):
        if on:
            self.links_off.discard(group)
        else:
            self.links_off.add(group)
        self._changed()

    def _members(self, s):
        """The other members an edit to `s` carries, none while its group's link is off."""
        if not self.linked(s):
            return []
        return [m for m in self.shapes if m.group == s.group and m.name != s.name]

    def _set(self, new):
        """`new` in place of its namesake, and in place of each member it carries its form at that
        member's centre."""
        forms = {m.name: replace(sh.placed(new, m.centre), name=m.name) for m in self._members(new)}
        forms[new.name] = new
        self.shapes = [forms.get(s.name, s) for s in self.shapes]

    def _fits(self, s):
        return self.within(s) and all(self.within(sh.placed(s, m.centre)) for m in self._members(s))

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

    def load(self, shapes):
        """Starts over on `shapes`: nothing selected, select mode, no undo behind it."""
        self.shapes, self.selected, self.stamp_from = list(shapes), None, None
        self.mode, self.pending, self._drag = "select", [], None
        self._regrouped()
        self._undo, self._redo, self._saved = [], [], tuple(self.shapes)
        self._changed()

    def outside(self):
        """The names of the shapes past the plate's edge, which are held nowhere and never saved."""
        return [s.name for s in self.shapes if not self.within(s)]

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

    def move_shape(self, name, step):
        """Moves the shape `step` places later in the order, stopping at either end; one undo step."""
        s = self.shape(name)
        if s is None:
            return
        i = self.shapes.index(s)
        j = min(max(0, i + step), len(self.shapes) - 1)
        if i != j:
            self.shapes.insert(j, self.shapes.pop(i))
            self._commit()
            self._changed()

    def delete_selected(self):
        if self.selected is not None:
            self.shapes = [s for s in self.shapes if s.name != self.selected]
            self.selected = None
            self._commit()
            self._changed()

    def _regrouped(self):
        """Each group cut to its largest set of identical members, the earliest of equal sets, and
        dropped when that is one."""
        keep = {}
        for g in sorted({s.group for s in self.shapes if s.group}):
            classes = {}
            for s in self.shapes:
                if s.group == g:
                    classes.setdefault(sh.form(s), []).append(s.name)
            best = max(classes.values(), key=len)
            if len(best) > 1:
                keep.update((n, g) for n in best)
        self.shapes = [s if keep.get(s.name, "") == s.group else replace(s, group=keep.get(s.name, ""))
                       for s in self.shapes]

    def _commit(self):
        """Ends an undo step at the shapes as they now are, when they differ from the last step's end."""
        self._regrouped()
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
        if self._fits(whole) or not self._fits(make(0.0)):
            return whole
        lo, hi = 0.0, 1.0
        for _ in range(HOLD_STEPS):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if self._fits(make(mid)) else (lo, mid)
        return make(lo)

    def _limited(self, c):
        """`c` with its radius cut to the room its centre, and each member's it carries, has to the
        plate's edges; None when that is under MIN_SIZE."""
        if self.plate is None:
            return c
        h, w = self.plate
        centres = [c.centre] + [m.centre for m in self._members(c)]
        r = min([c.r] + [min(x, y, w - x, h - y) for x, y in centres])
        out = replace(c, r=r)
        if not self._fits(out):
            out = replace(c, r=r * (1 - 1e-12))
        return out if out.r >= sh.MIN_SIZE else None

    def _name(self, kind):
        return sh.next_name(self.stem or kind, {s.name for s in self.shapes})

    def press(self, p, px, button="left"):
        p = tuple(p)
        if self.mode == "select":
            self._press_select(p, px, button)
        elif self.mode == "stamp":
            if button == "left":
                self._press_stamp(p)
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
            return self._held(lambda t: sh.square_from_corners(name, a, _toward(a, p, t)))
        return sh.rectangle_from_corners(name, a, p)

    def _stamped(self, p):
        """The stamp's copy centred at `p`, slid within the plate, named and in no group; None with
        no stamp, or one too large for the plate."""
        src = self.shape(self.stamp_from) if self.stamp_from is not None else None
        if src is None:
            return None
        copy = replace(sh.placed(src, p), name=self._name(src.kind), group="")
        if self.plate is not None:
            h, w = self.plate
            x0, y0, x1, y1 = copy.box()
            copy = copy.moved(min(max(0, -x0), w - x1), min(max(0, -y0), h - y1))
        return copy if self.within(copy) else None

    def _press_stamp(self, p):
        src = self.shape(self.stamp_from) if self.stamp_from is not None else None
        if src is None:
            self.mode = "select"
            return
        copy = self._stamped(p)
        if copy is None:
            return
        group = src.group
        if not group:
            group = sh.next_name("group", {s.group for s in self.shapes})
            self.links_off.discard(group)
            self._replace(replace(src, group=group))
        self.shapes.append(replace(copy, group=group))

    def preview(self):
        """The shape the gesture under way, or the stamp, would make at the cursor, or None."""
        if self.mode == "stamp" and self.cursor is not None:
            return self._stamped(self.cursor)
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
                    self._set(s.without_vertex(hit))
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
                    self._set(s)
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
            self._replace(self._held(lambda t: origin.moved(t * dx, t * dy)))
            return
        if what == "handle" and origin.kind == "circle":
            new = origin.dragged(arg, p)
            new = (self._limited(new) or origin) if held else new
        elif what == "handle":
            start, q = origin.handles()[arg], self._clamp(p) if held else p
            new = self._held(lambda t: origin.dragged(arg, _toward(start, q, t)))
        else:
            c = origin.centre
            theta = math.remainder(math.atan2(p[1] - c[1], p[0] - c[0]) - arg, 2 * math.pi)
            new = self._held(lambda t: origin.rotated(t * theta))
        self._set(new)
