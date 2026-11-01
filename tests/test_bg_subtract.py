"""bg-subtract: the frame against its bg input, by sign; BGR per channel then the largest; mixed inputs meet in gray; matched light."""
import numpy as np

from tools import bg_subtract


def test_modes_channels_and_mixed_inputs():
    bg = np.full((4, 4), 100, np.uint8)
    f = bg.copy()
    f[1, 1], f[2, 2] = 40, 130                                  # one darker pixel, one brighter
    assert bg_subtract.difference(f, bg, "absolute")[1, 1] == 60 and bg_subtract.difference(f, bg, "absolute")[2, 2] == 30
    d = bg_subtract.difference(f, bg, "darker")
    assert d[1, 1] == 60 and d[2, 2] == 0 and d.dtype == np.uint8
    assert bg_subtract.difference(f, bg, "brighter")[2, 2] == 30 and bg_subtract.difference(f, bg, "brighter")[1, 1] == 0
    color = np.full((4, 4, 3), 100, np.uint8)
    color[1, 1, 2] = 10                                         # a change in one channel
    assert bg_subtract.difference(color, np.full((4, 4, 3), 100, np.uint8), "absolute")[1, 1] == 90
    assert bg_subtract.difference(color, bg, "absolute").shape == (4, 4)   # BGR frame, gray background


def test_run_reads_bg_by_name_and_match_light_removes_a_global_dim():
    bg = np.full((4, 4), 100, np.uint8)
    f = (bg // 2).astype(np.uint8)                              # the lights halved
    f[1, 1] = 10                                                # and an ant
    frames = lambda r, input="in": {"in": f, "bg": bg}[input]  # noqa: E731
    assert bg_subtract.run(frames, 0, {"mode": "darker", "match_light": False}).min() == 50
    d = bg_subtract.run(frames, 0, {"mode": "darker", "match_light": True})
    assert d[0, 0] == 0 and d[1, 1] == 79                     # the frame's mean 47.5 scaled to 100: 10 becomes 21
