"""A cut's record: the footage a cut is of, the cuts it was made from and its extent on the footage.

The plan builds one for each cut a node is of, from what the cutting tools declare; the graph, the
walk and the window read it and none works out an extent, an origin or a served file of its own.
Rows are the footage's and half-open, (first, the row past the last); a rect is (y0, y1, x0, x1) in
the footage's pixels. Imports nothing of the player.
"""
from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np

INF = float("inf")


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
    is served, and is no part of which cut it is. A `provisional` cut is made of, or inside one
    made of, a result the window walked and nothing holds: it is walked by the window alone and
    never held. One `cut_off` is provisional and may run on past the rows that result is over."""
    footage: str
    made_from: tuple = ()
    extent: Extent = Extent()
    file: tuple | None = field(default=None, compare=False)
    provisional: bool = False
    cut_off: bool = False

    def cut(self, rows=None, rect=None, rects=None, file=None, provisional=False, cut_off=False):
        """The cut a node reading this one makes: `rows` the footage's, `rect` or `rects`, one a
        row of `rows`, in the pixels of this cut's frames; provisional and cut off where this one
        is or the flags say. ValueError for `rects` that are not one a row."""
        if rects is not None and (rows is None or rect is not None or len(rects) != rows[1] - rows[0]):
            raise ValueError("a shape a row is one rect for each row of its rows, and no rect beside them")
        said = Extent(rows and tuple(rows), rect and tuple(rect), rects and tuple(map(tuple, rects)))
        return Record(self.footage, (self,), _both(self.extent, said, _placed), file,
                      self.provisional or provisional or cut_off, self.cut_off or cut_off)

    def __and__(self, other):
        if self.footage != other.footage:
            raise ValueError("two cuts of two footages have no intersection")
        return Record(self.footage, (self, other), _both(self.extent, other.extent, _met), None,
                      self.provisional or other.provisional, self.cut_off or other.cut_off)

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


def read(rows, reach, row):
    """What a value at `row` read of a cut in time: (the first row, the row past the last) of
    `rows`, the cut's, each None where the value read nothing of that edge. `reach` is (rows
    before, rows after) the row that the value reads, None a side without bound, which reads its
    edge at every row. `rows` of None is the whole footage, and so is a first row of 0, the
    footage's own first row being no cut's. A last row is the cut's whatever it is, the footage's
    count not always known."""
    if rows is None:
        return None, None
    below, on_from = reading(rows, reach)
    return rows[0] if row < below else None, rows[1] if row >= on_from else None


def reading(rows, reach):
    """Where a value read each edge of a cut of `rows`, as `read` has it: (the row below which it
    read the first row, the row from which it read the last), either infinite where every row or
    none did."""
    (first, end), (before, after) = rows, reach
    return (-INF if first <= 0 else INF if before is None else first + before,
            -INF if after is None else end - after)


def cut_in_time(record):
    """(first, the row past the last) of the rows `record` cuts from the one cut it was made
    from, or None where it cuts no rows of it or was made from two."""
    if len(record.made_from) != 1 or record.extent.rows is None:
        return None
    return None if record.extent.rows == record.made_from[0].extent.rows else record.extent.rows


def holding(records, row):
    """The first of `records` whose rows hold `row`, or None."""
    return next((r for r in records if r.extent.holds(row)), None)


_KNOWN = {}    # id of a node's cuts -> (those cuts, each to its first place among them, their first rows, their rows past the last): asked a compute and a run held, of cuts a gate makes by the thousand
EVERY_ROW = 1 << 62


def _known(records):
    had = _KNOWN.get(id(records))
    if had is None or had[0] is not records:
        if len(_KNOWN) > 256:
            _KNOWN.clear()
        places = {}
        for i, r in enumerate(records):
            places.setdefault(r, i)
        rows = np.array([r.extent.rows or (0, EVERY_ROW) for r in records], np.int64).reshape(-1, 2)
        had = _KNOWN[id(records)] = (records, places, rows[:, 0].copy(), rows[:, 1].copy())
    return had


_OF = {}    # (what, id of a node's cuts) -> (those cuts, the answer of them)


def _once(what, records, make):
    had = _OF.get((what, id(records)))
    if had is None or had[0] is not records:
        if len(_OF) > 512:
            _OF.clear()
        had = _OF[what, id(records)] = (records, make())
    return had[1]


def first_served(records):
    """The file the first of `records` to be served one is served, as Record.served has it, or
    None; at the cost of one look where `records` is the same tuple from one ask to the next."""
    return _once("served", records, lambda: next((f for r in records if (f := r.served()) is not None), None))


def cuts_in_time(records):
    """cut_in_time of each of `records` that has one, in their order; the same list, at the cost
    of one look, where `records` is the same tuple from one ask to the next."""
    return _once("in time", records, lambda: [s for r in records if (s := cut_in_time(r))])


def among(record, records):
    """Whether `record` is one of `records`, at the cost of one look and not of `records`, which
    is to be the same tuple from one ask to the next."""
    return record in _known(records)[1]


def touching(records, spans):
    """The places among `records`, in order, of those holding a row of any of `spans`, each (first
    row, row past the last), a record of every row holding all; at the cost of those found and
    not of `records`, which is to be the same tuple from one ask to the next."""
    _, _, starts, ends = _known(records)
    hit = np.zeros(len(starts), bool)
    for a, b in spans:
        hit |= (starts < b) & (a < ends)
    return np.flatnonzero(hit).tolist()


def _above(record):
    yield record
    for r in record.made_from:
        yield from _above(r)


def computed_in(records, cut, row):
    """Of `records`, a node's cuts, the one its value at `row` is computed in: its one record; or
    the first `cut`, the cut its reader computes in, is or was made from; or with no `cut` the
    first holding `row`. None where none is. With a `cut` it costs the cuts between `cut` and the
    footage, not `records`, which is to be the same tuple from one ask to the next."""
    if len(records) == 1:
        return records[0]
    if cut is not None:
        places = _known(records)[1]
        at = min((places[r] for r in _above(cut) if r in places), default=None)
        return None if at is None else records[at]
    return holding(records, row)


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
