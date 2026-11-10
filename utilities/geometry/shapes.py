"""The four kinds as values with no window: a circle, a square and a rectangle as a centre, a size
and an angle, a polygon as its vertices, each edited by returning a new shape, and each written as
region's circle or polygon by `primitive`. Points are (x, y) in plate pixels; angles in radians. A
shape's `group` names the stamp group it is in, empty for none, and every edit keeps it."""
import math
from dataclasses import dataclass, replace

KINDS = ("circle", "square", "rectangle", "polygon")
MIN_SIZE = 1.0   # plate pixels; a handle dragged through its anchor stops a pixel short of a shape of no area


def _rotate(p, about, theta):
    c, s = (0.0 if abs(v) < 1e-12 else v for v in (math.cos(theta), math.sin(theta)))   # a quarter turn exact, so a shape flush with the plate's edge stays within it
    dx, dy = p[0] - about[0], p[1] - about[1]
    return (about[0] + c * dx - s * dy, about[1] + s * dx + c * dy)


def _inside_polygon(p, pts):
    x, y = p
    hit = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def segment_distance(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    n = ax * ax + ay * ay
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / n))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


@dataclass(frozen=True)
class Circle:
    name: str
    cx: float
    cy: float
    r: float
    group: str = ""
    kind = "circle"

    @property
    def centre(self):
        return (self.cx, self.cy)

    def box(self):
        return (self.cx - self.r, self.cy - self.r, self.cx + self.r, self.cy + self.r)

    def contains(self, p):
        return math.hypot(p[0] - self.cx, p[1] - self.cy) <= self.r

    def handles(self):
        """The rim dot, on the rim at the circle's right."""
        return {"rim": (self.cx + self.r, self.cy)}

    def dragged(self, handle, p):
        return replace(self, r=max(MIN_SIZE, math.hypot(p[0] - self.cx, p[1] - self.cy)))

    def moved(self, dx, dy):
        return replace(self, cx=self.cx + dx, cy=self.cy + dy)

    def primitive(self):
        return {"name": self.name, "circle": [self.cx, self.cy, self.r]}


@dataclass(frozen=True)
class Rect:
    """A square or a rectangle, `kind` saying which; a square's `w` and `h` are equal under every edit."""
    name: str
    kind: str
    cx: float
    cy: float
    w: float
    h: float
    angle: float = 0.0
    group: str = ""

    @property
    def centre(self):
        return (self.cx, self.cy)

    def _world(self, lx, ly):
        return _rotate((self.cx + lx, self.cy + ly), self.centre, self.angle)

    def _local(self, p):
        x, y = _rotate(p, self.centre, -self.angle)
        return (x - self.cx, y - self.cy)

    def vertices(self):
        hw, hh = self.w / 2, self.h / 2
        return [self._world(-hw, -hh), self._world(hw, -hh), self._world(hw, hh), self._world(-hw, hh)]

    def box(self):
        xs, ys = zip(*self.vertices())
        return (min(xs), min(ys), max(xs), max(ys))

    def contains(self, p):
        x, y = self._local(p)
        return abs(x) <= self.w / 2 and abs(y) <= self.h / 2

    def handles(self):
        """Corners and edge midpoints keyed (sx, sy), each of -1, 0 or 1 along the shape's own axes."""
        return {(sx, sy): self._world(sx * self.w / 2, sy * self.h / 2)
                for sx in (-1, 0, 1) for sy in (-1, 0, 1) if (sx, sy) != (0, 0)}

    def top(self):
        """The midpoint of the edge the rotation handle stands above, and the outward direction from it."""
        return self._world(0, -self.h / 2), _rotate((0.0, -1.0), (0.0, 0.0), self.angle)

    def dragged(self, handle, p):
        """The shape with handle (sx, sy) at `p` and the handle opposite it fixed; a square's side is
        the larger of the two reaches at a corner and the one reach at an edge."""
        sx, sy = handle
        qx, qy = self._local(p)
        ax, ay = -sx * self.w / 2, -sy * self.h / 2
        dx, dy = qx - ax, qy - ay
        gx = math.copysign(1, dx) if dx else (sx or 1)
        gy = math.copysign(1, dy) if dy else (sy or 1)
        if self.kind == "square":
            side = max(MIN_SIZE, max(abs(dx) * abs(sx), abs(dy) * abs(sy)))
            w = h = side
        else:
            w = max(MIN_SIZE, abs(dx)) if sx else self.w
            h = max(MIN_SIZE, abs(dy)) if sy else self.h
        lx = ax + gx * w / 2 if sx else 0.0
        ly = ay + gy * h / 2 if sy else 0.0
        cx, cy = self._world(lx, ly)
        return replace(self, cx=cx, cy=cy, w=w, h=h)

    def rotated(self, theta):
        return replace(self, angle=self.angle + theta)

    def moved(self, dx, dy):
        return replace(self, cx=self.cx + dx, cy=self.cy + dy)

    def primitive(self):
        return {"name": self.name, "polygon": [list(v) for v in self.vertices()]}


@dataclass(frozen=True)
class Polygon:
    name: str
    points: tuple
    group: str = ""
    kind = "polygon"

    @property
    def centre(self):
        """The vertices' mean, which a rotation about it leaves where it was."""
        n = len(self.points)
        return (sum(x for x, _ in self.points) / n, sum(y for _, y in self.points) / n)

    def vertices(self):
        return list(self.points)

    def box(self):
        xs, ys = zip(*self.points)
        return (min(xs), min(ys), max(xs), max(ys))

    def contains(self, p):
        return _inside_polygon(p, list(self.points))

    def handles(self):
        return dict(enumerate(self.points))

    def top(self):
        x0, y0, x1, _ = self.box()
        return ((x0 + x1) / 2, y0), (0.0, -1.0)

    def dragged(self, handle, p):
        pts = list(self.points)
        pts[handle] = tuple(p)
        return replace(self, points=tuple(pts))

    def with_vertex(self, after, p):
        """A vertex at `p` inserted after vertex `after`, on the edge to the next."""
        pts = list(self.points)
        pts.insert(after + 1, tuple(p))
        return replace(self, points=tuple(pts))

    def without_vertex(self, index):
        """Vertex `index` removed; the polygon unchanged when it has three."""
        if len(self.points) <= 3:
            return self
        return replace(self, points=self.points[:index] + self.points[index + 1:])

    def edge_near(self, p, tol):
        """The index of the vertex starting the edge within `tol` of `p` nearest it, or None."""
        pts = list(self.points)
        d, i = min((segment_distance(p, a, b), i) for i, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1])))
        return i if d <= tol else None

    def rotated(self, theta):
        c = self.centre
        return replace(self, points=tuple(_rotate(p, c, theta) for p in self.points))

    def moved(self, dx, dy):
        return replace(self, points=tuple((x + dx, y + dy) for x, y in self.points))

    def primitive(self):
        return {"name": self.name, "polygon": [list(p) for p in self.points]}


def circle_from_centre(name, centre, rim):
    return Circle(name, centre[0], centre[1], math.hypot(rim[0] - centre[0], rim[1] - centre[1]))


def circle_through(name, a, b, c):
    """The circle through three rim points; None when they are collinear."""
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    a2, b2, c2 = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
    return Circle(name, ux, uy, math.hypot(ax - ux, ay - uy))


def square_from_corners(name, a, b):
    """The upright square with a corner at `a`, reaching toward `b` by the larger of the two offsets."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    side = max(abs(dx), abs(dy))
    sx, sy = math.copysign(1, dx), math.copysign(1, dy)
    return Rect(name, "square", a[0] + sx * side / 2, a[1] + sy * side / 2, side, side)


def rectangle_from_corners(name, a, b):
    return Rect(name, "rectangle", (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(b[0] - a[0]), abs(b[1] - a[1]))


def form(s):
    """What two shapes share when one is the other moved: kind, size, rotation and, for a polygon,
    its vertices about its centre, rounded so that a copy moved there and back still matches."""
    if s.kind == "circle":
        return ("circle", round(s.r, 6))
    if s.kind == "polygon":
        cx, cy = s.centre
        return ("polygon",) + tuple((round(x - cx, 6), round(y - cy, 6)) for x, y in s.points)
    return (s.kind, round(s.w, 6), round(s.h, 6), round(math.remainder(s.angle, 2 * math.pi), 6))


def placed(s, at):
    """`s` moved so its centre is at `at`."""
    return s.moved(at[0] - s.centre[0], at[1] - s.centre[1])


def next_name(stem, taken):
    """`stem-k` for the least k from 1 not in `taken`."""
    k = 1
    while f"{stem}-{k}" in taken:
        k += 1
    return f"{stem}-{k}"
