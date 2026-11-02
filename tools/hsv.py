"""Frame tool: BGR to HSV on cv2's scale (H 0-179, S and V 0-255); bgr in, hsv out.

One conversion the memo shares among every inrange reading it, where each inrange converting for
itself pays the full frame once per colour. inrange takes bgr or hsv and reads which through
frames.type().
"""
import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "hsv", "frame", "bgr", "hsv"
DEFAULTS = {}


def run(frames, row, params):
    return cv2.cvtColor(frames(row), cv2.COLOR_BGR2HSV)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)   # no knobs
