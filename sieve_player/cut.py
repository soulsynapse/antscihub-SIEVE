"""A cut's record: the footage a cut is of, the cuts it was made from and its extent on the footage.

The plan builds one for each cut a node is of, from what the cutting tools declare; the graph, the
walk and the window read it and none works out an extent, an origin or a served file of its own.
Rows are the footage's and half-open, (first, the row past the last); a rect is (y0, y1, x0, x1) in
the footage's pixels. Imports nothing of the player.
"""
from dataclasses import dataclass, field
from typing import NamedTuple


class Extent(NamedTuple):
    """Where a cut lies on its footage: `rows`, None for every row; `rect`, None for every pixel;
    or `rects` in place of `rect`, one a row of `rows`, a shape a row over a period."""
    rows: tuple | None = None
    rect: tuple | None = None
    rects: tuple | None = None

    def at(self, row):
        """The rect at `row`, a row of the extent; None for every pixel."""
        return self.rect if self.rects is None else self.rects[row - self.rows[0]]

    def holds(self, row):
        return self.rows is None or self.rows[0] <= row < self.rows[1]


def _rows(a, b):
    if a is None or b is None:
        return a if b is None else b
    first = max(a[0], b[0])
    return first, max(first, min(a[1], b[1]))


def _met(a, b):
    if a is None or b is None:
        return a if b is None else b
    y0, x0 = max(a[0], b[0]), max(a[2], b[2])
    return y0, max(y0, min(a[1], b[1])), x0, max(x0, min(a[3], b[3]))


def _placed(within, rect):
    """`rect`, in the pixels of a frame cut to `within`, on the footage and inside `within`."""
    if within is None or rect is None:
        return rect if within is None else within
    y, x = within[0], within[2]
    return _met((rect[0] + y, rect[1] + y, rect[2] + x, rect[3] + x), within)


def _both(a, b, meet):
    rows = _rows(a.rows, b.rows)
    if a.rects is None and b.rects is None:
        return Extent(rows, meet(a.rect, b.rect))
    return Extent(rows, None, tuple(meet(a.at(r), b.at(r)) for r in range(*rows)))


@dataclass(frozen=True)
class Record:
    """One cut. `file` is (path, footage print) of the file that holds the cut's pixels where one
    is served, and is no part of which cut it is."""
    footage: str
    made_from: tuple = ()
    extent: Extent = Extent()
    file: tuple | None = field(default=None, compare=False)

    def cut(self, rows=None, rect=None, rects=None, file=None):
        """The cut a node reading this one makes: `rows` the footage's, `rect` or `rects`, one a
        row of `rows`, in the pixels of this cut's frames. ValueError for `rects` that are not one
        a row."""
        if rects is not None and (rows is None or rect is not None or len(rects) != rows[1] - rows[0]):
            raise ValueError("a shape a row is one rect for each row of its rows, and no rect beside them")
        said = Extent(rows and tuple(rows), rect and tuple(rect), rects and tuple(map(tuple, rects)))
        return Record(self.footage, (self,), _both(self.extent, said, _placed), file)

    def __and__(self, other):
        if self.footage != other.footage:
            raise ValueError("two cuts of two footages have no intersection")
        return Record(self.footage, (self, other), _both(self.extent, other.extent, _met))

    def origin(self, row=None):
        """(x, y) on the footage of the first pixel of the cut's frame at `row`, which a cut of one
        rect does not read."""
        rect = self.extent.at(row)
        return (0, 0) if rect is None else (rect[2], rect[0])

    def lift(self, place, row=None):
        """`place`, (x, y) in the cut's frame at `row`, on the footage. A row needs no lift."""
        x, y = self.origin(row)
        return place[0] + x, place[1] + y

    def served(self):
        """The file that holds this cut's pixels or, where it has none, the nearest cut's it was
        made from alone; None where the footage's own file does."""
        r = self
        while r.file is None and len(r.made_from) == 1:
            r = r.made_from[0]
        return r.file


def holding(records, row):
    """The first of `records` whose rows hold `row`, or None."""
    return next((r for r in records if r.extent.holds(row)), None)


def place_in(read, shown, row, shape, plate):
    """(x, y), in a frame of `shape`, (height, width), cut by `shown`, of the first pixel of
    `read`'s frame at `row`, `plate` being the footage's shape. (0, 0) where the two are one
    extent, whatever the frame; None where they are two and the frame is not of `shown`'s pixels,
    a rescaled one, so no place on it is known."""
    if read.extent == shown.extent:
        return 0, 0
    rect = shown.extent.at(row)
    if tuple(shape) != (tuple(plate) if rect is None else (rect[1] - rect[0], rect[3] - rect[2])):
        return None
    (rx, ry), (sx, sy) = read.origin(row), shown.origin(row)
    return rx - sx, ry - sy
