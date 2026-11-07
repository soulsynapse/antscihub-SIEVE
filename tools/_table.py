"""The table kind the blob tools share: its dtype, the plane it was found in, how a column is added
and how a record meets a plane. Not a tool; the registry skips a stem beginning with `_`, and a tool
imports from here and from no other tool (tests/test_seams.py). What a column means, a statistic
over a table or a linker's state belongs to the tool that computes it, never here.

A table is a structured array, one record a region; its dtype carries the (height, width) of the
plane it was found in as metadata, `plane(table)`, so a tool relating it to a plane or table of
another shape can scale. `blobs` promises the position columns and the plane; any other column may
be NaN or absent where its producer did not make it. `contour` is an object column, (N, 2) x, y,
so the table is never a flat array.
"""
import math

import cv2
import numpy as np

DTYPE = np.dtype([("x", np.int32), ("y", np.int32), ("w", np.int32), ("h", np.int32), ("area", np.int32),
                  ("cx", np.float32), ("cy", np.float32), ("angle", np.float32),
                  ("major", np.float32), ("minor", np.float32),
                  ("mean", np.float32), ("peak", np.float32), ("core", np.int32), ("contour", object)])
TRACKS_DTYPE = np.dtype(DTYPE.descr + [("id", np.int32)])      # a tracks table of blobs' own columns
OUTLINES = ("box", "contour")


def plane_dtype(shape, dtype=DTYPE):
    """`dtype` with the plane's (height, width) on it."""
    return np.dtype(dtype.descr, metadata={"plane": (int(shape[0]), int(shape[1]))})


def plane(table):
    """The (height, width) the table was found in, or None when it has none."""
    return (table.dtype.metadata or {}).get("plane")


def with_column(table, name, values):
    """The table with `values` as a column named `name`, the plane kept; a name the table already
    has raises ValueError, since overwriting a producer's column would silently change its meaning."""
    if name in table.dtype.names:
        raise ValueError(f"the table already has a column {name!r}")
    values = np.asarray(values)
    dtype = np.dtype(table.dtype.descr + [(name, values.dtype)], metadata=dict(table.dtype.metadata or {}))
    out = np.empty(len(table), dtype)
    for n in table.dtype.names:
        out[n] = table[n]
    out[name] = values
    return out


def footprint(b, shape, scale=(1.0, 1.0), outline="contour"):
    """Where record `b` lies in a plane of `shape`, as (rows, cols, inside): the slices of the plane
    pixels whose centres fall in its box scaled by `scale` (y, x), and the bool mask within them of
    those whose centres fall in its filled contour, or in the whole box when `outline` is box or
    the record has no contour. A plane pixel is inside by its centre, so a record covers the same
    ground at any scale."""
    sy, sx = scale
    y, x, h, w = (int(b[k]) for k in ("y", "x", "h", "w"))
    rows = slice(max(math.ceil(y * sy - 0.5), 0), max(min(math.ceil((y + h) * sy - 0.5), shape[0]), 0))
    cols = slice(max(math.ceil(x * sx - 0.5), 0), max(min(math.ceil((x + w) * sx - 0.5), shape[1]), 0))
    contour = b["contour"] if outline == "contour" and "contour" in b.dtype.names else None
    if contour is None:
        local = np.ones((h, w), bool)
    else:
        local = np.zeros((h, w), np.uint8)
        cv2.fillPoly(local, [(np.asarray(contour, np.int32) - (x, y)).reshape(-1, 1, 2)], 1)
        local = local.astype(bool)
    iy = np.clip(np.floor((np.arange(rows.start, rows.stop) + 0.5) / sy).astype(int) - y, 0, h - 1)
    ix = np.clip(np.floor((np.arange(cols.start, cols.stop) + 0.5) / sx).astype(int) - x, 0, w - 1)
    return rows, cols, local[np.ix_(iy, ix)]


def outline(painter, b, kind):
    """A record's box or contour in the painter's pen; the contour's points are pixel centres, +0.5."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QPolygonF

    if kind == "contour" and "contour" in b.dtype.names and b["contour"] is not None:
        painter.drawPolygon(QPolygonF([QPointF(float(x) + 0.5, float(y) + 0.5) for x, y in b["contour"]]))
    else:
        painter.drawRect(QRectF(float(b["x"]), float(b["y"]), float(b["w"]), float(b["h"])))


def draw(painter, table, kind="box", color=(80, 220, 120)):
    """Every record of `table` outlined in `color`, one device pixel wide at any zoom; a frame
    tool's draw() over a table, given the result it was handed."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPen

    if table is None or len(table) == 0:
        return
    pen = QPen(QColor(*color), 0)
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    for b in table:
        outline(painter, b, kind)


TRAIL = 30          # rows of path drawn behind each record of a tracks table


def draw_tracks(painter, row, result, start, kind="box"):
    """A series tool's draw() over a tracks result: the row's records outlined in a hue per id, the
    id beside each, and the id's path over the last TRAIL rows."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QPen

    if not isinstance(result, dict) or not 0 <= row - start < len(result["rows"]):
        return
    rows, i = result["rows"], row - start
    painter.setBrush(Qt.NoBrush)
    for b in rows[i]:
        pen = QPen(QColor.fromHsv(int(b["id"]) * 47 % 360, 200, 240), 0)
        pen.setCosmetic(True)
        painter.setPen(pen)
        outline(painter, b, kind)
        painter.drawText(QPointF(float(b["x"]), float(b["y"]) - 2), str(int(b["id"])))
        path = [(float(t["cx"][0]), float(t["cy"][0])) for t in (rows[k][rows[k]["id"] == b["id"]]
                                                                 for k in range(max(0, i - TRAIL), i + 1)) if len(t)]
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))
