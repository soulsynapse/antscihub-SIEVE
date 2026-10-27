"""Frame tool: the mask of pixels inside an HSV box, as color_detector_v2 draws it.

BGR in, 0/255 gray out. Bounds are on cv2's scale (H 0-179, S and V 0-255). Hue is circular, so
h_lo above h_hi selects the two outer strips (reds); S and V do not wrap. A channel at its full
range constrains nothing. `load_bounds(path)` reads the detector's settings JSON into params; the
card's Load… button does the same by hand, and the `settings` path input does it from whatever
selector is wired into it. The file's min_area and merge_distance are contour settings, not pixel
ones, and are left for a later tool.
"""
import json

import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "inrange", "frame", "bgr", "gray"
H_MAX, SV_MAX = 179, 255
DEFAULTS = {"h_lo": 0, "h_hi": H_MAX, "s_lo": 0, "s_hi": SV_MAX, "v_lo": 0, "v_hi": SV_MAX}
PATHS = {"settings": lambda path: load_bounds(path)}


def run(frames, row, params):
    hsv = cv2.cvtColor(frames(row), cv2.COLOR_BGR2HSV)
    h0, h1 = params["h_lo"], params["h_hi"]
    lo = [h0, params["s_lo"], params["v_lo"]]
    hi = [h1, params["s_hi"], params["v_hi"]]
    if h0 <= h1:
        return cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
    a = cv2.inRange(hsv, np.array(lo, np.uint8), np.array([H_MAX, hi[1], hi[2]], np.uint8))
    b = cv2.inRange(hsv, np.array([0, lo[1], lo[2]], np.uint8), np.array(hi, np.uint8))
    return cv2.bitwise_or(a, b)


def load_bounds(path):
    """Params from a color_detector_v2 settings file. Raises on a malformed file."""
    with open(path, encoding="utf-8") as f:
        bounds = json.load(f)["bounds"]
    out = {}
    for ch, top in (("h", H_MAX), ("s", SV_MAX), ("v", SV_MAX)):
        lo, hi = (int(v) for v in bounds[ch.upper()])
        if not (0 <= lo <= top and 0 <= hi <= top):
            raise ValueError(f"{ch.upper()} bounds {lo}-{hi} outside 0-{top}")
        if ch != "h" and lo > hi:
            raise ValueError(f"{ch.upper()} bounds {lo}-{hi} reversed; only H wraps")
        out[f"{ch}_lo"], out[f"{ch}_hi"] = lo, hi
    return out


def settings(parent=None):
    import os

    from PySide6.QtWidgets import QFileDialog, QPushButton

    from sieve_player import ParamWidget
    from sieve_player.theme import readout

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.sliders = {name: self.add_int(name, 0, H_MAX if name[0] == "h" else SV_MAX, DEFAULTS[name])
                            for name in DEFAULTS}
            self.button, self.status = QPushButton("Load…"), readout()
            self.form.add_row("settings", self.button)
            self.form.add_line(self.status)
            self.button.clicked.connect(self._pick)

        def _pick(self):
            path, _ = QFileDialog.getOpenFileName(self, "Open color settings", "", "Settings (*.json);;All (*)")
            if path:
                self.load(path)

        def load(self, path):
            try:
                params = load_bounds(path)
            except Exception as exc:  # the file is the user's; say what was wrong with it
                self.status.setText(f"could not load: {exc}")
                return
            for name, s in self.sliders.items():
                s.setValue(params[name])
            self.status.setText(os.path.basename(path))

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
