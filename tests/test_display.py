"""to_qimage: uint8 as it is, a measured plane over its top, a flow field as the colour wheel."""
import os

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage  # noqa: E402

from sieve_player.window import flow_top, to_qimage  # noqa: E402


def test_a_plane_is_shown_over_its_top_and_a_field_by_direction():
    plane = np.array([[0.0, 500.0], [1000.0, 250.0]], np.float32)
    img = to_qimage(plane)
    assert img.format() == QImage.Format_Grayscale8 and img.pixelColor(0, 1).value() == 255
    assert to_qimage(plane, 2000.0).pixelColor(0, 1).value() == 127         # a running top from before
    assert to_qimage(np.array([[7, 250]], np.uint8)).pixelColor(1, 0).value() == 250
    field = np.zeros((2, 2, 2), np.float32)
    field[0, 0], field[1, 1] = (3.0, 0.0), (0.0, -4.0)
    assert flow_top(field) == 4.0
    img = to_qimage(field)
    assert img.format() == QImage.Format_BGR888 and img.pixelColor(0, 1).value() == 0
    right, up = img.pixelColor(0, 0), img.pixelColor(1, 1)
    assert right.hue() != up.hue() and up.value() == 255 and 0 < right.value() < 255
