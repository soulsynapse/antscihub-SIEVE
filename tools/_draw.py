"""How a table is drawn on the frame: a record's outline, every record of a table in one colour,
and a tracks result in a hue per id with its trail. Not a tool; a tool imports it and no other
tool (tests/test_seams.py). Qt is imported inside the functions, so a tool's run() never pulls it in.
"""

TRAIL = 30          # rows of path drawn behind each record of a tracks table


def contour(painter, points):
    """An (N, 2) x, y outline in the painter's pen; the points are pixel centres, +0.5."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF

    painter.drawPolygon(QPolygonF([QPointF(float(x) + 0.5, float(y) + 0.5) for x, y in points]))


def outline(painter, b, kind):
    """A record's box or contour in the painter's pen."""
    from PySide6.QtCore import QRectF

    if kind == "contour" and "contour" in b.dtype.names and b["contour"] is not None:
        contour(painter, b["contour"])
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
