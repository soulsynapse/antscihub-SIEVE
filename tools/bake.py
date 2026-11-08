"""The bake node: on a wire of any kind, what it receives passes through unchanged until it is
baked. Its kind is its wire's, so on a frame wire it is a frame node and on a signal or tracks wire
a series node, and its params say what a bake would write, which `bake()` reads for the worker,
and change nothing it hands out live. The mode, live or serving the bake, is the document's
(sieve_player/document.py) and shown on the node. Bake, on the node's card, has the worker write
the input over the range into the store under the node's key (sieve_player/worker.py, store.py,
writers.py); the kinds it can write are the store's to say.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, PRODUCES = "bake", "same", "same"
EXPECTS = ("bgr", "gray", "mask", "hsv", "flow", "blobs", "signal", "tracks")
QUALITIES = ("lossless", "standard")
DEFAULTS = {"from": "", "to": "", "increment": 1, "quality": QUALITIES[0]}
MAX_INCREMENT = 600


def bake(params, count):
    """(the plate rows a bake of `params` writes over a clip of `count` rows, as a range whose step
    is the increment, the frame writer's quality): from `from` to `to`, a bound left blank being the
    clip's end, every `increment` rows, empty when the range names no row; ValueError when a bound
    does not read as a row."""
    lo, hi = _bound(params.get("from", ""), 0), _bound(params.get("to", ""), count - 1)
    inc = max(1, int(params.get("increment", 1)))
    return range(max(lo, 0), min(hi, count - 1) + 1, inc), str(params.get("quality", DEFAULTS["quality"]))


def _bound(text, default):
    text = str(text).strip()
    return default if text == "" else int(text)


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
