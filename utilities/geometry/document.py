"""The geometry file as the utility writes and reads it: region's `plate` and `shapes`, and the
`drawing`, each shape's name to its kind and, when it has one, its stamp group. A shape the drawing
does not name, or whose primitive does not fit the kind it is given, is rebuilt from the primitive
alone: a circle as a circle, a polygon of four right angles as a square or a rectangle, any other as
a polygon, in no group. The checks here are the ones rebuilding needs; region's loader stays the
judge of what a region accepts."""
import json
import math
from dataclasses import replace

from . import shapes as sh

FIT_PX = 1e-3   # how far a vertex may sit from the square or rectangle rebuilt through it


def to_json(plate, shapes):
    drawing = {}
    for s in shapes:
        drawing[s.name] = {"kind": s.kind, **({"group": s.group} if s.group else {})}
    return {"plate": list(plate), "shapes": [s.primitive() for s in shapes], "drawing": drawing}


def save(path, plate, shapes):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(to_json(plate, shapes), f, indent=1)
        f.write("\n")


def _rect(name, pts):
    """The square or rectangle whose vertices `pts` are, in either winding, or None."""
    if len(pts) != 4:
        return None
    for order in (pts, [pts[0], pts[3], pts[2], pts[1]]):
        (x0, y0), (x1, y1), _, (x3, y3) = order
        w, h = math.hypot(x1 - x0, y1 - y0), math.hypot(x3 - x0, y3 - y0)
        if min(w, h) < sh.MIN_SIZE:
            return None
        cx, cy = sum(x for x, _ in order) / 4, sum(y for _, y in order) / 4
        kind = "square" if abs(w - h) <= FIT_PX else "rectangle"
        r = sh.Rect(name, kind, cx, cy, w, h, math.atan2(y1 - y0, x1 - x0))
        if all(math.dist(a, b) <= FIT_PX for a, b in zip(r.vertices(), order)):
            return r
    return None


def _inferred(d):
    name = d["name"]
    if "circle" in d:
        cx, cy, r = d["circle"]
        return sh.Circle(name, float(cx), float(cy), float(r))
    pts = [(float(x), float(y)) for x, y in d["polygon"]]
    return _rect(name, pts) or sh.Polygon(name, tuple(pts))


def _as_drawn(d, entry):
    """The shape as the drawing gives it, or None when the primitive does not fit that kind."""
    if not isinstance(entry, dict) or not isinstance(entry.get("group", ""), str):
        return None
    kind = entry.get("kind")
    s = _inferred(d)
    if kind == "polygon" and "polygon" in d:
        s = sh.Polygon(s.name, tuple((float(x), float(y)) for x, y in d["polygon"]))
    elif kind == "rectangle" and s.kind == "square":
        s = replace(s, kind="rectangle")
    elif kind != s.kind:
        return None
    return replace(s, group=entry.get("group", ""))


def load(path):
    """(plate, shapes, the names whose kind was inferred), the plate as (height, width). Raises
    ValueError on a file it cannot read shapes from, saying why."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"{path} could not be read: {e}") from e
    if not isinstance(d, dict) or "plate" not in d or not isinstance(d.get("shapes"), list):
        raise ValueError(f"{path} is not a geometry file: it has no plate and shapes")
    plate = d["plate"]
    if not isinstance(plate, list) or len(plate) != 2 or not all(isinstance(v, int) and v > 0 for v in plate):
        raise ValueError(f"{path}'s plate is {plate!r}, not [height, width]")
    drawing = d.get("drawing") if isinstance(d.get("drawing"), dict) else {}
    shapes, inferred = [], []
    for i, item in enumerate(d["shapes"]):
        try:
            name = item["name"]
            s = _as_drawn(item, drawing[name]) if name in drawing else None
            if s is None:
                s = _inferred(item)
                inferred.append(name)
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"{path}'s shape {i} is not a named circle or polygon") from e
        shapes.append(s)
    if len({s.name for s in shapes}) != len(shapes):
        raise ValueError(f"{path} names two shapes alike")
    return (plate[0], plate[1]), shapes, inferred
