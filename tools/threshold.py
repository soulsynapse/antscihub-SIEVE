"""Frame tool: binarize gray frames with one cut, out as a 0/255 mask. For a color band use tools/inrange."""
import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "threshold", "frame", "gray", "mask"
PARAMS = {
    "thresh": {"default": 128, "kind": "int", "range": (0, 255)},
    "invert": {"default": False, "kind": "bool"},
}


def run(frames, row, params):
    mode = cv2.THRESH_BINARY_INV if params["invert"] else cv2.THRESH_BINARY
    _, b = cv2.threshold(frames(row), params["thresh"], 255, mode)
    return b


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
