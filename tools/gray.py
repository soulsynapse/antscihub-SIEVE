"""Frame tool: BGR to gray by luma (cv2's Rec. 601 weights). The step the decoder used to take."""
import cv2

NAME, KIND, EXPECTS, PRODUCES = "gray", "frame", "bgr", "gray"
DEFAULTS = {}


def run(frames, row, params):
    return cv2.cvtColor(frames(row), cv2.COLOR_BGR2GRAY)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)   # no knobs


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
