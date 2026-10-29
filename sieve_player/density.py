"""The density of a plane: a row's pixels counted into bins on a fixed log1p axis.

v2's density plot, kept by the walk rather than wired: the worker folds every plane the walk
computes into (T, BINS) counts, so the window holds a histogram per row however large
the plane, and no row's picture depends on another row. v2 scaled its axis to the window's maximum,
which is why every change there rebinned the whole window; here a window move is a slice. The axis is
the integers up to a knee and log1p above it, to 2**24, past any gray-units-squared measure: an integer
plane such as a gray image or a difference then has no empty bin between its values, which a log axis
finer than one unit would leave. The plot crops to the bins the window occupies. A value below zero
lands in bin 0 with the zeros.
"""
import cv2
import numpy as np

BINS = 256
KNEE = 20                                   # values below it are their own bins: a bin narrower than one unit is a gap between integers
TOP = float(np.log1p(2.0**24))              # the axis ends here, in log1p of the value
STEP = (TOP - np.log1p(KNEE)) / (BINS - 1 - KNEE)   # log1p per bin above the knee; the first such bin is about one unit wide


def is_plane(a):
    """What the density is kept for: any two-dimensional array of values, a measure or a gray image,
    never a mask, whose histogram is two bins, or a field."""
    return isinstance(a, np.ndarray) and a.ndim == 2 and a.dtype != bool


def value_of(b):
    """The value at the centre of bin `b`."""
    return float(b) if b < KNEE else float(np.expm1(np.log1p(KNEE) + (b - KNEE) * STEP))


def pos_of(v):
    """A value's place on the axis, in bins, unrounded: value_of's inverse."""
    v = max(float(v), 0.0)
    return v if v < KNEE else KNEE + (np.log1p(v) - np.log1p(KNEE)) / STEP


def bin_of(v):
    """The bin a value lands in."""
    return int(round(v)) if v < KNEE - 0.5 else min(BINS - 1, KNEE + int(round((np.log1p(v) - np.log1p(KNEE)) / STEP)))


_LUT = np.array([bin_of(v) for v in range(256)], np.uint8)   # a uint8 plane's bins, exact


def fold(plane):
    """A row's pixel counts per bin, (BINS,) uint32. A uint8 plane is one calcHist and a table, which
    is nearly free; a float plane pays a log over every pixel, about what changeenergy itself costs."""
    f = np.asarray(plane)
    if f.dtype == np.uint8:
        by_value = cv2.calcHist([f], [0], None, [256], [0, 256]).ravel()
        return np.bincount(_LUT, weights=by_value, minlength=BINS).astype(np.uint32)
    f = cv2.max(f.astype(np.float32) if f.dtype != np.float32 else f, 0.0)   # below zero: no log; the zeros' bin
    lin = cv2.convertScaleAbs(f)                                                 # rounds
    lg = cv2.convertScaleAbs(cv2.log(f + 1.0), alpha=1 / STEP, beta=KNEE - np.log1p(KNEE) / STEP)   # NaN saturates to 0
    low = cv2.compare(f, KNEE - 0.5, cv2.CMP_LT)                                 # 255 where the linear bins apply
    idx = cv2.bitwise_or(cv2.bitwise_and(lin, low), cv2.bitwise_and(lg, cv2.bitwise_not(low)))
    return np.bincount(idx.ravel(), minlength=BINS).astype(np.uint32)
