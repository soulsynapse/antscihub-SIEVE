"""Frame tool: a static composite of the whole clip, the same image at every row; gray or BGR in, out as in.

`samples` rows spaced evenly over the clip are read through the upstream node and folded to one
image per pixel by `stat`. `mean` and `max` and `min` stream; `median` holds the sample stack while
it partitions and takes the lower middle value, so it stays in the frame's dtype. Mean and median
keep an animal that sat in one place for half the samples, and the composite then carries it: a
dark animal on pale ground wants `max`, the brightest each pixel ever showed, which drops it if it
was away in any one sample, and a pale animal on dark ground wants `min`. Show the node to see
which this clip gets. STATIC says the output is one image at every row, so the player holds it
once; it is built on the first row asked for and kept here too under frames.key and the params,
since the memo may let it go and a rebuild is seconds of seeks, paid on the worker inside that
row, see docs/findings/2026-10-31-background-composite-cost.md.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "background", "frame", ("gray", "bgr"), "same"
STATIC = True
STATS = ("mean", "median", "max", "min")
DEFAULTS = {"stat": "median", "samples": 50}
MAX_SAMPLES = 200
_last = None    # ((frames.key, stat, samples), composite): one clip's composite, the last built


def sample_rows(count, samples):
    """`samples` distinct rows spaced evenly over `count`, the first and last among them."""
    n = max(1, min(int(samples), count))
    return np.unique(np.linspace(0, count - 1, n).round().astype(int))


def samples_of(frames, rows):
    """Each row's frame, stopping at the first the clip turns out not to have: a container's header
    may claim rows the stream lacks, and the last sample sits on the claim."""
    out = []
    for r in rows:
        try:
            out.append(frames(r))
        except IndexError:
            break
    return out


def composite(frames, params):
    stat, rows = params["stat"], sample_rows(frames.count, params["samples"])
    if stat not in STATS:
        raise ValueError(f"background: no stat {stat!r}; one of {STATS}")
    if stat == "median":
        stack = np.stack(samples_of(frames, rows))
        mid = (len(stack) - 1) // 2
        return np.partition(stack, mid, axis=0)[mid]
    acc, n = None, 0
    for f in samples_of(frames, rows):
        n += 1
        if acc is None:
            acc = f.astype(np.float64) if stat == "mean" else f.copy()
        elif stat == "mean":
            acc += f
        else:
            (np.maximum if stat == "max" else np.minimum)(acc, f, out=acc)
    return (acc / n).round().astype(f.dtype) if stat == "mean" else acc


def run(frames, row, params):
    global _last
    key = (frames.key, params["stat"], int(params["samples"]))
    if _last is None or _last[0] != key:
        _last = (key, composite(frames, params))
    return _last[1]


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("stat", STATS, DEFAULTS["stat"])
    w.add_int("samples", 1, MAX_SAMPLES, DEFAULTS["samples"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
