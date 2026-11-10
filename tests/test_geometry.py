"""The geometry utility: a video opened at the plate the player's Decoder reads, seeked to any frame,
and a view zoomed no smaller than fit and shown at 100%."""
import os

import cv2
import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player.decoder import Decoder  # noqa: E402
from utilities.geometry.video import EXACT_DECODE_BELOW  # noqa: E402
from utilities.geometry.window import GeometryWindow  # noqa: E402

H, W, N = 48, 64, EXACT_DECODE_BELOW + 16    # past the forward-decoded opening, so the last frame is a seek


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    path = tmp_path_factory.mktemp("g") / "clip.avi"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    for i in range(N):
        w.write(np.full((H, W, 3), 3 * i, np.uint8))
    w.release()
    return str(path)


@pytest.fixture
def window(clip):
    QApplication.instance() or QApplication([])
    win = GeometryWindow(clip)
    yield win
    win.close()


def test_the_plate_is_the_clip_and_the_decoders_shape_and_the_seek_bar_reaches_the_last_frame(window, clip):
    d = Decoder(clip)
    try:
        assert window.plate == (H, W) == d.read(0).shape[:2]
    finally:
        d.close()
    window.seek_bar.setValue(N - 1)
    assert window.index == N - 1 and window.frame_label.text().startswith(f"{N - 1} / {N - 1}")
    assert abs(int(window.frame[0, 0, 0]) - 3 * (N - 1)) <= 2
    window.seek_bar.setValue(5)
    assert abs(int(window.frame[0, 0, 0]) - 15) <= 2


def test_zooming_out_stops_at_fit_and_100_percent_is_one_to_one(window):
    window.show()
    window.resize(900, 700)
    QApplication.processEvents()
    view = window.view
    fit = view.fit_scale()
    assert fit > 1

    def wheel(notches):
        at = QPointF(view.viewport().rect().center())
        e = QWheelEvent(at, view.viewport().mapToGlobal(at), QPoint(), QPoint(0, 120 * notches),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(view.viewport(), e)

    wheel(3)
    assert view.scale_now() == pytest.approx(fit * 1.25 ** 3)
    wheel(-10)
    assert view.scale_now() == pytest.approx(fit)
    window.actual_button.click()
    assert view.scale_now() == 1
    window.fit_button.click()
    assert view.scale_now() == pytest.approx(fit)
