"""The bake node: on a wire of any kind, what it receives passes through unchanged until it is
baked. Its kind is its wire's, so on a frame wire it is a frame node and on a signal or tracks wire
a series node, and its params say what a bake would write, the rows, the increment and the frame
writer's quality, and change nothing it hands out live. The mode, live until a bake exists, is saved
on the node and shown there; what baking writes and where is docs/spec/bake.md's and the store's.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, PRODUCES = "bake", "same", "same"
EXPECTS = ("bgr", "gray", "mask", "hsv", "flow", "blobs", "signal", "tracks")
MODES = ("live", "baked", "stale")
QUALITIES = ("lossless", "standard")
DEFAULTS = {"from": "", "to": "", "increment": 1, "quality": "lossless"}
MAX_INCREMENT = 600


def run(src, row, params=None):
    if params is None:      # the series call, run(series, params): the rows leave as they came
        return passed(src.data)
    return src(row)


def passed(data):
    """A series pass-through's result: rows as rows with the records each holds as the signal, a signal as itself."""
    data = np.asarray(data)
    if data.dtype == object:
        rows = np.empty(len(data), object)
        rows[:] = list(data)
        return {"rows": rows, "signal": np.array([len(t) for t in rows], np.float32)}
    return {"signal": data.astype(np.float32).reshape(-1)}


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_text("from", DEFAULTS["from"])
    w.add_text("to", DEFAULTS["to"])
    w.add_int("increment", 1, MAX_INCREMENT, DEFAULTS["increment"])
    w.add_choice("quality", QUALITIES, DEFAULTS["quality"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, motion, reduce

    sys.exit(play([gray, sys.modules[__name__], motion, reduce], sys.argv[1] if len(sys.argv) > 1 else None))
