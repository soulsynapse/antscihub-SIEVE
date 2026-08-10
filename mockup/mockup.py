"""The GUI as the tree has it, copied into one runnable file with mock data.

Nothing imports from `sieve`: this is a surface to reshape toward VISION
without touching the app, so every widget here is a plain-PySide6 copy of its
`src/sieve/gui` counterpart — same layout, colors, sizes, and hotkeys, with
the session, specs, and pipeline replaced by the sample document at the top.

Where a widget has no counterpart yet it is VISION's shape, not the tree's:
`PinnedStep` is the one step held under the canvas, which the tree currently
fills with a generic trace. `MockComposite` is the other one, and it is v2's
`gui/composite_view.py` rather than an invention — the tree's `canvas.py` is a
viewport that paints the frame it was handed, and what the walk needs over it
is the composite: the walked step's output over that step's input, and the
block grid where the output is a block series.

`crop-1` is the third, and it is `docs/adr/gui-knows-kinds-not-tools.md` worked
through rather than a tool the tree has: a rect param whose generated editor is
a box drawn on the canvas, with the card's spin boxes editing the same value
through the same clamp. Neither surface owns it, and what the box keeps is what
every step after it is given — the grid downstream is laid over the kept region,
which is the consequence a decoration would not have. It cuts a set of regions
rather than one, so it is also where the stack has to draw a step with more
outputs than the card below it can read: a row of numbered squares in the gap,
an arrow into each from the card that made them, and the chain continuing out of
the one the user selected.

`output-1` is the fourth: what leaves the chain is a step at the foot of it and
not a screen beside it, so the write list is that step's param and the edges
into its card are what is ticked. The save position went with it — a pane whose
whole content was one step's form is that step's form.

`_AddBox` is the fifth, and it is why a popup is not the default for every
question (`docs/adr/a-position-is-asked-for-in-the-chain.md`): a step that is
not one yet, opened into the chain by the project card's ADD STEP and moved
through it with the same ↑/↓ that move the walk.
VISION's add-tool box is "below the last step" because that is where its
scenario stands; what a position *is* does not change further up, so the box
goes wherever the chain has a gap, and the offer it holds is the position's.

It is also what ⇄ opens, standing over the card instead of between two: adding
and swapping are one question asked of a gap and of a card, so there is no swap
menu. The modes differ underneath, where a swap keeps the node it is — its id,
its edges, the ticks naming it — and an add mints one. That difference is the
reason a swap is not a remove and an add, and it is invisible on screen, which
is why it is written here and in `MOCKUP-MAP.md` rather than left to be read
off the picture.

Run: `uv run python mockup/mockup.py`
"""

from __future__ import annotations

import math
import random
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetricsF,
    QImage,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QPen,
    QPolygonF,
    QRadialGradient,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# The sample document.

LIBRARY_ROOT = "D:/ethology/2026"
LIBRARY = f"library — {LIBRARY_ROOT}"

# Name, what the project holds, and when it was last opened. The second line is
# what the pipeline's knob rows are here: the thing about the card a click acts on.
PROJECTS = [
    ("arena_2026-07-30", "6 sources · 6000 frames @ 30 fps", "opened today"),
    ("colony_04_stirred", "18 sources · chain saved", "3 days ago"),
    ("petri_replicates", "4 sources · no chain yet", "last month"),
]

def add_project() -> None:
    """Another project in the library, holding what a new one holds: nothing.

    Named here rather than through a dialog because the name is a knob like any
    other — the project card is where it would be edited, and a modal asking for
    it up front would be the one form in the surface that blocks the walk.
    """
    PROJECTS.append(
        (f"untitled_{len(PROJECTS) + 1}", "no sources · no chain yet", "just created")
    )


def close_project(index: int) -> None:
    """Out of the library. Deleted from the list and not marked, unlike REMOVED:
    nothing here is keyed by a project's position, so the ones below can move."""
    del PROJECTS[index]


# The project's videos, and which one the chain reads. Module state for the
# reason BANDS is: the pipeline pane is rebuilt on every walk move, and a
# selection living in the combo box would revert each time the user moved.
SOURCES = [
    "arena_r1.mp4",
    "arena_r2.mp4",
    "arena_r3.mp4",
    "arena_r4.mp4",
    "arena_r5.mp4",
    "arena_r6.mp4",
]
SELECTED_SOURCE = 0

NODES = [
    ("source-1", "source"),
    ("crop-1", "crop"),
    ("rescale-1", "rescale"),
    ("normalize-1", "normalize"),
    ("background-1", "background"),
    ("threshold-1", "colour threshold"),
    ("subtract-1", "background subtract"),
    ("blocks-1", "block signal"),
    ("morlet-1", "morlet band"),
    ("count-1", "windowed count"),
    ("output-1", "output"),
]

# What each step reads, by position in the stack — the chain is a DAG and the
# stack is one topological order of it, not the chain itself. VISION's scene is
# the branch here: background and colour threshold both read the normalized
# frames, and the subtraction ingests both, so background's output reaches down
# past a step that does not consume it. Held beside NODES rather than inside a
# tool, because which steps a step reads is the graph's to say.
INPUTS: dict[int, tuple[int, ...]] = {
    0: (),
    1: (0,),
    2: (1,),
    3: (2,),
    4: (3,),
    5: (3,),
    6: (4, 5),
    7: (6,),
    8: (7,),
    9: (8,),
    10: (9,),
}

_OUTPUT_INDEX = 10

# What the output step writes: `(step, product, on)`. The output is a tool like
# any other and its inputs are the steps whose products are ticked — a writer
# reads what it writes — so this table is where `INPUTS[_OUTPUT_INDEX]` comes
# from rather than a screen's checkoff. Ticking `blocks-1 — block series` is
# what makes an edge leave that card and reach past the three steps under it.
WRITES: list[tuple[int, str, bool]] = [
    (7, "block series", False),
    (8, "band power", False),
    (9, "windowed count", True),
    (9, "event table", True),
]


def refresh_output_inputs() -> None:
    """The write list, read back as the output step's ports."""
    INPUTS[_OUTPUT_INDEX] = tuple(
        sorted({step for step, _product, on in WRITES if on})
    )


def set_written(row: int, on: bool) -> None:
    step, product, _was = WRITES[row]
    WRITES[row] = (step, product, on)
    refresh_output_inputs()


refresh_output_inputs()

# Steps the user has removed, by position. The stack is drawn from what is left
# rather than from a shortened NODES, because every table here is keyed by
# position — INPUTS, STAGES, the knobs, the guidance — and a removal that
# renumbered would have to rewrite all of them to say what dropping one step
# means. What it means is that the chain reads past it, which is `_sources_of`.
REMOVED: set[int] = set()

# Positions whose tool was swapped for another. Their `node_id` does not move —
# that is the whole of what a swap preserves and a remove-then-add would not —
# but the knobs, plots and guidance written against them here were written for
# the tool that has gone, so they are dropped the way an added step's are.
RETOOLED: set[int] = set()


def live_nodes() -> list[int]:
    """The chain in the order the stack draws it, which is the stages' order.

    Not `range(len(NODES))`: an added step is appended to `NODES` so that no
    existing position moves, and where it *stands* is which stage's members it
    was spliced into. The two agreed until a step could be added; taking the
    order from the stages is what keeps the rail's ticks, the walk's ↑/↓, and
    the numbers on the cards saying the same thing about where a step is.
    """
    return [index for _name, _chip, members in STAGES for index in members if index not in REMOVED]


# VISION: the slot under the canvas holds the detection step until the user
# pins something else there.
PINNED_DEFAULT = 9

# v2's fixed stage headers with their `in -> out` type chips (chain_model.py),
# and which of NODES each groups. The source is a stage of one: what the chain
# reads is chosen the way everything downstream of it is, on a card in the walk
# with a knob, rather than in a strip above the stack that the walk skips.
STAGES = [
    ("source", "video -> image", (0,)),
    ("spatial prep", "image -> image", (1, 2, 3, 4, 5, 6)),
    ("signal extraction", "image -> block series", (7,)),
    ("temporal filter", "series -> series", (8,)),
    ("detection", "series -> events", (9,)),
    ("output", "events -> files", (10,)),
]

# What a step can be swapped for, keyed by the stage that holds it. VISION's
# swap is an offering derived from the position rather than a list any tool
# declares, and the position is the stage's `in -> out` chip — so anything
# carrying that signature can stand there, and the key is the stage, not the
# tool it currently holds.
SWAPPABLE = {
    "source": ["source", "image sequence"],
    "spatial prep": [
        "crop",
        "rescale",
        "normalize",
        "background",
        "colour threshold",
        "background subtract",
        "mask",
    ],
    "signal extraction": ["block signal", "optical flow", "frame difference"],
    "temporal filter": ["morlet band", "bandpass", "moving average"],
    "detection": ["windowed count", "threshold crossings"],
    "output": ["output", "event table", "labelled clips"],
}

def stage_after(site: int) -> int:
    """Which stage a step added after `site` would stand in.

    A gap inside a stage's run belongs to that stage; the gap at its foot is
    the next stage's first position. That is the whole rule, and it is what
    makes the offer under the source the spatial tools VISION's scenario names
    rather than a second source — the source's stage is a stage of one, so the
    only gap it has is its last.
    """
    holder = next(i for i, (_n, _c, members) in enumerate(STAGES) if site in members)
    live = [member for member in STAGES[holder][2] if member not in REMOVED]
    return holder if site != live[-1] else min(holder + 1, len(STAGES) - 1)


def offer_after(site: int) -> list[str]:
    """What could stand in the gap under `site`: the position's signature.

    `SWAPPABLE` stands in for the derivation (the tool lists are sample data),
    but what it stands in for is keyed on the stage's `in -> out` chip and
    never on the tool above the gap.
    """
    return SWAPPABLE[STAGES[stage_after(site)][0]]


def offer_at(index: int) -> list[str]:
    """What could stand where `index` stands — the same question, of a card.

    Adding and swapping are one question asked of two kinds of position, which
    is why one box serves both: a gap has no tool in it and a card has one, and
    neither fact is an input to the offering. What differs is underneath, where
    a swap keeps the node's identity and an add mints one.
    """
    return SWAPPABLE[_stage_of(index)[0]]


def retool(index: int, tool: str) -> None:
    """Put another tool at `index`, keeping the node it is.

    The id does not move, so the ticks on the output card that name this step,
    and every edge into and out of it, survive the swap — which is the whole
    difference between this and removing the step and adding one back.
    """
    NODES[index] = (NODES[index][0], tool)
    RETOOLED.add(index)


def add_node(site: int, tool: str) -> int:
    """Splice a step into the gap under `site`, and hand back where it landed.

    Appended to `NODES` rather than inserted, for the reason `REMOVED` exists:
    every table here is keyed by position, and an insertion that renumbered
    would have to rewrite all of them to say what adding one step means. What
    it means is the inverse of `_sources_of` — the new step reads what the gap
    reads and whatever read past the gap now reads it, which is `without_node`
    run backwards. The output is exempt: its inputs are the ticked products
    (`refresh_output_inputs`), so a step spliced above it does not steal them.
    """
    index = len(NODES)
    NODES.append((f"{tool.replace(' ', '-')}-{index}", tool))
    INPUTS[index] = (site,)
    for dst, sources in list(INPUTS.items()):
        if dst not in (index, _OUTPUT_INDEX) and site in sources:
            INPUTS[dst] = tuple(index if src == site else src for src in sources)

    stage = stage_after(site)
    name, chip, members = STAGES[stage]
    at = members.index(site) + 1 if site in members else 0
    STAGES[stage] = (name, chip, members[:at] + (index,) + members[at:])
    return index


GUIDANCE = {
    "source-1": (
        "The video every later step reads. Choosing one re-derives the chain "
        "against it; the working window and the playhead are positions in this "
        "file, so they are what moving to another source resets."
    ),
    "crop-1": (
        "Drag the box on the canvas, or type the same four numbers here — they "
        "are one value, and the box is the editor the rect kind generates. "
        "Everything downstream sees only what the box keeps: the block grid is "
        "laid over the kept region, so cropping to the dish is what stops the "
        "arena wall from being blocks you have to threshold around. Cut a region "
        "per dish and the squares under the card are them; the chain below is "
        "drawn for the one you have selected, and the others are the same chain "
        "you have not walked."
    ),
    "rescale-1": (
        "Pick the largest reduction at which the behavior you are scoring is "
        "still visible on the canvas. Everything downstream reads the reduced "
        "frames; the saved outputs record the factor used."
    ),
    "normalize-1": (
        "Per-frame stretching makes each frame's extremes span the range; window "
        "mode holds one mapping across the working window so brightness is "
        "comparable within it."
    ),
    "background-1": (
        "One plate estimated from many frames: whatever holds still over the "
        "sample is the arena, not the animals. Nothing downstream of this step "
        "reads it except the subtraction — the colour threshold below is fed "
        "from the same normalized frames this is, which is why its card sits "
        "between the two and takes nothing from either."
    ),
    "threshold-1": (
        "The colour cut that says which pixels could be an animal at all. It "
        "reads the normalized frames, not the plate, so moving the background "
        "sample cannot move this mask — the two arrive at the subtraction as "
        "separate inputs and are weighed there."
    ),
    "subtract-1": (
        "The step with two inputs: the plate from the background step and the "
        "mask from the threshold, keyed by port. What it emits is what the "
        "mask kept and the plate does not explain, which is the picture the "
        "block grid is laid over."
    ),
    "blocks-1": (
        "Block size is the grain of the analysis: each block contributes one "
        "value per frame to the series the temporal steps read. Smaller blocks "
        "localize; the cost is attributed, not capped."
    ),
    "morlet-1": (
        "Drag the frequency band on the scalogram: the transform snaps it to the "
        "bank's edges and the readout shows the truth it uses. The density below "
        "is the population of all blocks' band power — the count is made of it."
    ),
    "count-1": (
        "The threshold speaks counts: drag it against the windowed series until "
        "the events you can see on the footage are the green spans you can count "
        "on the plot. D is the window the count is taken over."
    ),
    "output-1": (
        "The last step, and a step: what leaves the chain is chosen here rather "
        "than on a screen beside it. Ticking a product is what makes the step "
        "that holds it an input of this one — the edges into this card are the "
        "write list, so a chain that writes the block series says so in the "
        "picture. Run materializes exactly what is ticked and nothing above it "
        "that only the canvas wanted."
    ),
}

# The bands the drags write. VISION has the document own these; the mockup has
# no document, and a band living in the widget would reset every time the pin
# moved or the walk rebuilt the stack — which would misreport how a drag feels.
BANDS: dict[str, tuple[float, float]] = {
    "morlet-1": (0.8, 2.4),
    "morlet-1/density": (0.62, math.inf),
    "count-1": (30.0, math.inf),
}

# What a document would emit when a band moves. The density band decides which
# blocks the canvas rings, so the plot that drags it and the surface that draws
# it are two widgets neither of which owns the other; in v2 the document tells
# both, and here whoever draws a band registers and the drag calls back.
BAND_WATCHERS: list[QWidget] = []


def notify_band_changed() -> None:
    for widget in BAND_WATCHERS:
        widget.update()


# The crops, each normalized to the source frame as (x, y, w, h). A rect param,
# and the ADR's worked example: the box on the canvas and the spin boxes on the
# card are two editors of one value, so neither can be the place it lives.
#
# A list rather than one rect because one step cuts every region the user wants
# scored separately — replicate dishes in one recording, a treatment arena and
# its control — and cutting them is one tool's job, not one chain per dish. So
# the step has more outputs than the card has room for, and the stack draws them
# where the branch is: a row of numbered squares in the gap under the card, one
# arrow down from the tool into each. What the rest of the chain is drawn for is
# the region selected here; the others are the same chain, unwalked.
CROPS: list[list[float]] = [
    [0.09, 0.06, 0.82, 0.88],
    [0.11, 0.12, 0.34, 0.36],
    [0.57, 0.50, 0.32, 0.40],
]
SELECTED_CROP = 0


def crop() -> list[float]:
    """The region the canvas and everything downstream of it are drawn for."""
    return CROPS[SELECTED_CROP]


#: The smallest crop a drag can leave, as a fraction of the frame. A box with no
#: area has no aspect, and every downstream fit divides by it.
CROP_MIN = 0.04

#: `(owner, callback)`. The owner is only ever a key: a card is rebuilt on every
#: walk move, and a callback still holding a deleted spin box is the crash that
#: comes of a module-level watcher list.
CROP_WATCHERS: list[tuple[QWidget, object]] = []


def watch_crop(owner: QWidget, callback) -> None:
    CROP_WATCHERS.append((owner, callback))
    owner.destroyed.connect(lambda *_: _unwatch_crop(callback))


def _unwatch_crop(callback) -> None:
    CROP_WATCHERS[:] = [pair for pair in CROP_WATCHERS if pair[1] is not callback]


def notify_crop_changed(source=None) -> None:
    """Tell every editor but the one that wrote, which is already showing it."""
    for owner, callback in list(CROP_WATCHERS):
        if owner is not source:
            callback()


def set_crop(rect: tuple[float, float, float, float], source=None) -> None:
    """Write the selected crop, clamped so it stays on the frame and keeps area."""
    x, y, w, h = rect
    w = min(max(w, CROP_MIN), 1.0)
    h = min(max(h, CROP_MIN), 1.0)
    CROPS[SELECTED_CROP][:] = [
        min(max(x, 0.0), 1.0 - w),
        min(max(y, 0.0), 1.0 - h),
        w,
        h,
    ]
    notify_crop_changed(source)


def select_crop(index: int, source=None) -> None:
    """Walk onto one of the step's regions.

    The same notification a drag sends, because it is the same kind of move: the
    canvas, the spin boxes, and the fan under the card are all showing one
    region, and which one is as much the crop's value as where its box is.
    """
    global SELECTED_CROP
    index = max(0, min(len(CROPS) - 1, index))
    if index == SELECTED_CROP:
        return
    SELECTED_CROP = index
    notify_crop_changed(source)


def add_crop(source=None) -> None:
    """Another region, offset off the selected one so both are grabbable."""
    global SELECTED_CROP
    x, y, w, h = crop()
    w, h = max(CROP_MIN, w * 0.6), max(CROP_MIN, h * 0.6)
    CROPS.append(
        [
            min(max(x + 0.06, 0.0), 1.0 - w),
            min(max(y + 0.06, 0.0), 1.0 - h),
            w,
            h,
        ]
    )
    SELECTED_CROP = len(CROPS) - 1
    notify_crop_changed(source)


def remove_crop(source=None) -> None:
    """Drop the selected region. A crop step with no region cuts nothing."""
    global SELECTED_CROP
    if len(CROPS) <= 1:
        return
    del CROPS[SELECTED_CROP]
    SELECTED_CROP = min(SELECTED_CROP, len(CROPS) - 1)
    notify_crop_changed(source)


# ---------------------------------------------------------------------------
# The palette, then the two surfaces: the composite and the generic graph.

_SURFACE = QColor(18, 18, 22)
_TRACE = QColor(120, 200, 255)

# v2's plot palette (band_plot.py) and card colors (chain_stack.py).
PANEL = QColor(31, 33, 38)
PANEL_HOT = QColor(38, 41, 47)
LINE = QColor(55, 58, 66)
TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)
ACCENT = QColor(94, 200, 180)
BAND = QColor(240, 110, 100)
DETECT = QColor(96, 210, 120)
_STACK_BG = QColor(24, 26, 30)
#: The chain's edges. A card's hairline is `LINE` against the card's own fill;
#: the same value on the stack's darker ground is a line nobody sees, and the
#: edges are the one thing on that ground.
EDGE = QColor(88, 94, 108)


def _plot_font(size: int, *, bold: bool = False, spaced: bool = False) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    if spaced:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    return font


# ---------------------------------------------------------------------------
# The canvas: composite_view.py's step composite — the walked step's output
# over that step's input at one opacity, and where the output is a block
# series rather than an image, the grid drawn in place of the overlay.

#: The composed pair's size in pixels. Every frame here is painted rather than
#: decoded; the pane letterboxes whatever aspect it is handed.
_FRAME_W, _FRAME_H = 480, 360

#: The grid `blocks-1` makes over the *whole* frame, as (ny, nx). Block b sits
#: at (b // nx, b % nx). What the step actually makes is `block_grid()`: a block
#: is a fixed square of pixels, so cropping takes blocks away rather than
#: reshaping them, and a grid that stretched to fill the crop would be the one
#: thing the composite exists to rule out.
BLOCK_GRID = (18, 24)

#: Overlay opacity, and the three grid alphas in 0.2 steps — coarse on purpose
#: (composite_view.GRID_STEPS): separated-blocks against one-mass is a reading
#: of fill against border, and matching two continuous sliders is a pixel hunt.
_DEFAULT_OPACITY = 65
_GRID_STEPS = 5
_DEFAULT_FILL_STEP, _DEFAULT_LINE_STEP, _DEFAULT_HEAT_STEP = 3, 1, 3

#: The heat layer's cold-to-hot stops: v1's turbo read, blended over footage.
#: Deliberately not `_ramp`'s warm ramps — those are for a dark plot surface.
_HEAT_STOPS = (
    (48, 18, 59),
    (69, 91, 205),
    (62, 155, 254),
    (24, 214, 203),
    (72, 248, 130),
    (164, 252, 60),
    (226, 220, 56),
    (254, 163, 49),
    (239, 89, 17),
    (194, 36, 3),
    (122, 4, 3),
)

_HEADER_H, _FOOTER_H, _PANE_MARGIN = 22, 26, 6

#: Magnification is bounded below by the fit — 1.0 *is* fit, whatever the
#: widget size is — and above where a cell is unambiguous to place (zoom.py).
_MIN_ZOOM, _MAX_ZOOM, _ZOOM_STEP = 1.0, 16.0, 1.25

#: How near an edge the cursor grabs it, and how dark the removed region goes.
#: The scrim is heavy on purpose: crop is the one step whose output is defined
#: by what is missing, and a faint one reads as a selection the user could
#: ignore rather than as the frame every later step will be given.
_CROP_GRAB = 7.0
_CROP_SCRIM = QColor(8, 8, 10, 170)
_CROP_HANDLE = 4.0


def _heat_color(level: float, alpha: float) -> QColor:
    v = max(0.0, min(1.0, level)) * (len(_HEAT_STOPS) - 1)
    i = min(int(v), len(_HEAT_STOPS) - 2)
    a, b, t = _HEAT_STOPS[i], _HEAT_STOPS[i + 1], v - i
    color = QColor(*(round(a[k] + (b[k] - a[k]) * t) for k in range(3)))
    color.setAlphaF(alpha)
    return color


def _specks() -> list[tuple[float, float, float]]:
    """Every speck as (angle, radius fraction, rotation), fixed at import.

    Fixed because the composite blends two renders of the same scene: specks
    drawn from a fresh stream per image would put the input's dish under the
    output's, which is the one thing an overlay must never do.
    """
    rng = random.Random(7)
    loose = [
        (rng.uniform(0, math.tau), 0.15 + 0.77 * rng.random(), rng.uniform(0, 180))
        for _ in range(70)
    ]
    # One aggregation, so the grid has adjacent detected cells to share walls.
    clustered = [
        (0.9 + rng.gauss(0, 0.16), 0.55 + rng.gauss(0, 0.07), rng.uniform(0, 180))
        for _ in range(22)
    ]
    return loose + clustered


SPECKS = _specks()


def _speck_uv(angle: float, radius: float) -> tuple[float, float]:
    """A speck's position in frame-normalized coordinates."""
    r = min(_FRAME_W, _FRAME_H) * 0.46 * radius
    return 0.5 + r * math.cos(angle) / _FRAME_W, 0.5 + r * math.sin(angle) / _FRAME_H


def _dish_image(
    width: int, height: int, levels: tuple[int, int], *, specks: bool = True
) -> QImage:
    """The dish and its specks, painted once into an image.

    `levels` is the dish's centre and rim grey. The pair is what a normalize
    step moves, and moving it is what makes an overlay legible under the
    opacity slider: two images that differ only in resolution blend into
    something the slider cannot be seen to act on.

    Without the specks it is the plate a background step estimates: the same
    scene with everything that moved taken out of it, which is the whole of
    what that step claims to have found.
    """
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(20, 20, 22))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    center = QPointF(width / 2, height / 2)
    radius = min(width, height) * 0.46
    gradient = QRadialGradient(center, radius)
    gradient.setColorAt(0.0, QColor(levels[0], levels[0], min(255, levels[0] + 2)))
    gradient.setColorAt(1.0, QColor(levels[1], levels[1], min(255, levels[1] + 4)))
    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(center, radius, radius)
    if specks:
        painter.setBrush(QColor(28, 28, 30))
        _paint_specks(painter, width, height)
    painter.end()
    return image


def _paint_specks(painter: QPainter, width: int, height: int) -> None:
    for angle, r, rotation in SPECKS:
        u, v = _speck_uv(angle, r)
        painter.save()
        painter.translate(u * width, v * height)
        painter.rotate(rotation)
        painter.drawEllipse(QPointF(0, 0), width * 0.010, width * 0.005)
        painter.restore()


def _specks_only_image(
    width: int, height: int, ground: QColor, ink: QColor
) -> QImage:
    """The specks with the dish taken away — a mask, or what a subtraction left.

    Both later spatial steps make a picture of this shape and differ in what
    they paint it with: a threshold's mask is flat, and a subtraction keeps a
    little of the ground it could not explain.
    """
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(ground)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(ink)
    _paint_specks(painter, width, height)
    painter.end()
    return image


def block_grid() -> tuple[int, int]:
    """The grid the crop leaves, as (ny, nx): the same square blocks, fewer of them."""
    ny, nx = BLOCK_GRID
    _x, _y, w, h = crop()
    return max(1, round(ny * h)), max(1, round(nx * w))


def _block_power(ny: int, nx: int) -> list[float]:
    """Band power per block at the playhead, in the density plot's 0..1 units.

    Built from the specks rather than from noise: the cells that ring are the
    cells with something in them, which is the correspondence between picture
    and grid the composite exists to show. The units are the density plot's
    axis and not v2's raw power, because the same drag has to move both — a
    grid on its own scale would ring against a handle the user cannot see.

    Specks outside the crop are still walked: one just past the edge bleeds into
    the cells inside it, and dropping it would make the crop edge the one place
    in the frame where a block cannot be lit by its neighbour.
    """
    rng = random.Random(29)
    values = [0.10 + 0.14 * rng.random() for _ in range(ny * nx)]
    cx, cy, cw, ch = crop()
    for angle, r, _ in SPECKS:
        u, v = _speck_uv(angle, r)
        col, row = (u - cx) / cw * nx - 0.5, (v - cy) / ch * ny - 0.5
        for j in range(max(0, int(row) - 1), min(ny, int(row) + 3)):
            for i in range(max(0, int(col) - 1), min(nx, int(col) + 3)):
                d2 = (i - col) ** 2 + (j - row) ** 2
                values[j * nx + i] += 0.55 * math.exp(-d2 / 0.9)
    return [min(1.0, value) for value in values]


def block_power() -> list[float]:
    """The per-block values for the crop in force, remade when it moves.

    Remade rather than cached against the crop: a drag writes the value on every
    mouse-move, and the honest thing for the mockup to show is what that costs.
    """
    return _block_power(*block_grid())


def grid_caption() -> str:
    """What the signal step says it made, as v2's grid caption states it."""
    ny, nx = block_grid()
    return f"mean |diff| · {ny}x{nx} blocks · hover solos, click pins"


def crop_rect(width: int, height: int, rect: list[float] | None = None) -> QRect:
    """A crop as whole pixels of a `width` x `height` frame, never empty."""
    x, y, w, h = crop() if rect is None else rect
    return QRect(
        round(x * width),
        round(y * height),
        max(1, round(w * width)),
        max(1, round(h * height)),
    )


def _cropped(image: QImage) -> QImage:
    return image.copy(crop_rect(image.width(), image.height()))

#: A tab-side step (morlet, windowed count) has no rendered output of its own,
#: so selecting one composes the deepest step that did render and the caption
#: says so — v2's `_composite_target`, which is why walking past `blocks-1`
#: leaves the grid up rather than blanking the canvas.
_SOURCE_INDEX = 0
_CROP_INDEX = 1
_BLOCKS_INDEX = 7
_DEEPEST_RENDERED = _BLOCKS_INDEX
_BACKGROUND_INDEX = 4
_THRESHOLD_INDEX = 5
_SUBTRACT_INDEX = 6


def _composed_step(index: int) -> tuple[int, bool]:
    """`(step composed, whether that is a fallback)` for the walked step."""
    return (index, False) if index <= _DEEPEST_RENDERED else (_DEEPEST_RENDERED, True)


def _composite_frames(index: int) -> tuple[QImage, QImage | None]:
    """`(input, output)` for the step at `index`; no output where a grid is one.

    The source has no input to compose against — a decoded frame is what it
    makes out of a file, and the picture under it is the file — so it returns
    the frame alone and the surface drops the opacity slider with it. Crop is
    the other one: what it removed is not a picture to fade in over what it
    kept, it is the region outside the box, and the box is drawn instead.
    """
    source = _dish_image(_FRAME_W, _FRAME_H, (142, 60))
    if index in (_SOURCE_INDEX, _CROP_INDEX):
        return source, None
    kept = _cropped(source)
    reduced = kept.scaled(
        max(1, kept.width() // 2),
        max(1, kept.height() // 2),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if index == 2:  # rescale: the same picture with half the pixels to carry it
        return kept, reduced
    stretched = _cropped(_dish_image(_FRAME_W, _FRAME_H, (214, 16))).scaled(
        reduced.width(),
        reduced.height(),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if index == 3:  # normalize: the stretch the slider is there to weigh
        return reduced, stretched
    size = (stretched.width(), stretched.height())
    if index == _BACKGROUND_INDEX:
        plate = _cropped(_dish_image(_FRAME_W, _FRAME_H, (214, 16), specks=False)).scaled(
            *size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return stretched, plate
    if index == _THRESHOLD_INDEX:
        return stretched, _specks_only_image(*size, QColor(12, 12, 14), QColor(236, 238, 245))
    if index == _SUBTRACT_INDEX:
        # The branch's two inputs arrive here, and the composite can show only
        # one of them under the output: the frames, because the plate is what
        # the output is the absence of.
        return stretched, _specks_only_image(*size, QColor(16, 17, 20), QColor(198, 206, 224))
    return stretched, None


class _Magnifier:
    """zoom.py: a zoom level and a pan centre in normalized content coordinates.

    Two rectangles, and the difference is load-bearing. The *fit* is where
    content lands aspect-fitted in the widget; the *view rect* is the fit
    magnified about the centre, and it is what everything — images, grid, hit
    test — paints and reads through, so the overlay cannot drift off the
    pixels it describes. The fit survives as the thing the view is clamped
    against, which is the whole zoom-floor rule.
    """

    def __init__(self) -> None:
        self.zoom = _MIN_ZOOM
        self._centre = QPointF(0.5, 0.5)

    @property
    def magnified(self) -> bool:
        return self.zoom > _MIN_ZOOM

    def reset(self) -> bool:
        self._centre = QPointF(0.5, 0.5)
        if self.zoom == _MIN_ZOOM:
            return False
        self.zoom = _MIN_ZOOM
        return True

    def view_rect(self, fit: QRectF) -> QRectF:
        """The fit magnified and panned, clamped so no pan reveals a gap.

        At zoom 1.0 it returns `fit` itself rather than an arithmetic
        reconstruction of it: a wheel-out storm leaves the content exactly
        fitted, not fitted to within a float epsilon.
        """
        if self.zoom <= _MIN_ZOOM:
            return fit
        width, height = fit.width() * self.zoom, fit.height() * self.zoom
        x = min(max(fit.center().x() - self._centre.x() * width, fit.right() - width), fit.left())
        y = min(max(fit.center().y() - self._centre.y() * height, fit.bottom() - height), fit.top())
        return QRectF(x, y, width, height)

    def at(self, point: QPointF, fit: QRectF) -> QPointF:
        """A widget point in normalized content coordinates, unrounded.

        Unrounded because rounding makes the wheel creep under a stationary
        cursor: each step would re-anchor a little off where the last landed.
        """
        view = self.view_rect(fit)
        if view.width() <= 0 or view.height() <= 0:
            return QPointF()
        return QPointF(
            (point.x() - view.x()) / view.width(),
            (point.y() - view.y()) / view.height(),
        )

    def wheel(self, detents: float, anchor: QPointF, fit: QRectF) -> bool:
        """Magnify about the cursor. True if the zoom moved.

        About the cursor and not the centre: what the user is looking at stays
        under the pointer while it grows, so placing a block does not turn into
        chasing it with a pan after every detent.
        """
        target = self.at(anchor, fit)
        zoom = min(max(self.zoom * (_ZOOM_STEP**detents), _MIN_ZOOM), _MAX_ZOOM)
        if zoom == self.zoom:
            return False
        self.zoom = zoom
        width, height = fit.width() * zoom, fit.height() * zoom
        if width > 0 and height > 0:
            self._centre = QPointF(
                (fit.center().x() - anchor.x()) / width + target.x(),
                (fit.center().y() - anchor.y()) / height + target.y(),
            )
        return True


class _CompositePane(QWidget):
    """The paint surface: base full, over at the owner's opacity, grid on top."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base: QImage | None = None
        self.over: QImage | None = None
        self.opacity = _DEFAULT_OPACITY / 100.0
        self.grid_on = False
        #: The crop box is drawn and draggable exactly when the crop step is
        #: walked: an overlay that stayed up on every step would be a mode, and
        #: what it edits belongs to one card.
        self.crop_on = False
        self.grid = block_grid()
        self.values = block_power()
        self.solo: int | None = None
        self.hover: int | None = None
        #: The block a click pinned. Gesture state, not the solo: it decides
        #: what the pointer leaving reverts to, and what is *drawn* still moves
        #: only when the model says so.
        self.latched: int | None = None
        self.fill_alpha = _DEFAULT_FILL_STEP / _GRID_STEPS
        self.line_alpha = _DEFAULT_LINE_STEP / _GRID_STEPS
        self.heat_alpha = _DEFAULT_HEAT_STEP / _GRID_STEPS
        #: Shift is held: every overlay drops so the frame can be read bare.
        self.peek = False
        self.magnifier = _Magnifier()
        #: The crop gesture: which part of the box is held, and where in the box
        #: the press landed, so a move drags the corner the cursor took rather
        #: than snapping it under the cursor on the first pixel of travel.
        self._crop_drag: str | None = None
        self._crop_grab = QPointF()
        #: Who a drag here writes as. The owner registers as the crop's watcher
        #: and repaints through `on_crop`, so the write has to name the owner or
        #: every mouse-move recomposes the picture the drag cannot change.
        self.crop_source: object = self
        #: A block index to solo, or None. Emitted, never self-applied.
        self.on_solo = lambda block: None
        self.on_hover = lambda block: None
        self.on_zoom = lambda: None
        self.on_crop = lambda: None
        self.setMouseTracking(True)
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ---- geometry ---------------------------------------------------------

    def in_band(self) -> list[bool]:
        """Which blocks the detection band holds right now.

        Read at paint time rather than cached: the band is the density plot's
        to drag, and a copy taken when the step was composed would ring the
        cells of a threshold the user has since moved off.
        """
        lo, hi = BANDS["morlet-1/density"]
        return [lo <= value <= hi for value in self.values]

    def _content_rect(self) -> QRectF:
        """The fit: where the content lands aspect-fitted, and nothing else."""
        image = self.base if self.base is not None else self.over
        available = QRectF(self.rect()).adjusted(_PANE_MARGIN, 2, -_PANE_MARGIN, -2)
        if image is not None and image.height() > 0:
            aspect = image.width() / image.height()
        elif self.grid_on:
            aspect = self.grid[1] / self.grid[0]
        else:
            return available
        width = min(available.width(), available.height() * aspect)
        return QRectF(
            available.center().x() - width / 2.0,
            available.center().y() - width / aspect / 2.0,
            width,
            width / aspect,
        )

    def view_rect(self) -> QRectF:
        return self.magnifier.view_rect(self._content_rect())

    def grid_edges(self) -> tuple[list[int], list[int]]:
        """The integer pixel columns and rows the grid lines fall on.

        Rounding the *line* rather than each cell's origin and extent is what
        closes the seam: neighbouring cells cannot round apart when they read
        the same number, and one ULP either side of a half-pixel is a row of
        unblended footage across the heatmap. The paint and the hit test both
        read this, so the cell under the pointer is the cell the pointer is
        over — registration is not maintained so much as unable to come apart.
        """
        g = self.view_rect()
        ny, nx = self.grid
        xs = [round(g.left() + i * g.width() / nx) for i in range(nx + 1)]
        ys = [round(g.top() + j * g.height() / ny) for j in range(ny + 1)]
        return xs, ys

    def block_at(self, pos: QPointF) -> int | None:
        """The block under `pos`, or None outside the grid.

        Two containment tests, not one. A magnified grid runs off under the
        letterbox and is clipped away at paint time, so a point the fit does
        not contain is over bare panel whatever the grid rect says — answering
        with the cell that would have been there solos one nobody can see.
        """
        if not self.grid_on:
            return None
        g = self.view_rect()
        if g.isEmpty() or not g.contains(pos) or not self._content_rect().contains(pos):
            return None
        ny, nx = self.grid
        xs, ys = self.grid_edges()
        col = min(max(bisect_right(xs, int(pos.x())) - 1, 0), nx - 1)
        row = min(max(bisect_right(ys, int(pos.y())) - 1, 0), ny - 1)
        return row * nx + col

    def crop_box(self, rect: list[float] | None = None) -> QRectF:
        """A crop in widget pixels, through the same view the frame is drawn in."""
        view = self.view_rect()
        x, y, w, h = crop() if rect is None else rect
        return QRectF(
            view.left() + x * view.width(),
            view.top() + y * view.height(),
            w * view.width(),
            h * view.height(),
        )

    def crop_under(self, pos: QPointF) -> int | None:
        """An unselected region under `pos`, topmost last-drawn first.

        Only the selected box is draggable, so a press on another one has one
        unambiguous meaning — walk onto that region — and the drag that follows
        is on the box the user is now looking at rather than on whichever one
        the press happened to land in.
        """
        if not self.crop_on:
            return None
        for index in reversed(range(len(CROPS))):
            if index != SELECTED_CROP and self.crop_box(CROPS[index]).contains(pos):
                return index
        return None

    def crop_part_at(self, pos: QPointF) -> str | None:
        """Which part of the box a press at `pos` takes, or None.

        Corners are tested before edges and edges before the interior, so the
        two-degree grab wins where they overlap — the corner of a box is the one
        place where guessing costs the user a second gesture to undo.
        """
        if not self.crop_on:
            return None
        box = self.crop_box()
        near_l = abs(pos.x() - box.left()) <= _CROP_GRAB
        near_r = abs(pos.x() - box.right()) <= _CROP_GRAB
        near_t = abs(pos.y() - box.top()) <= _CROP_GRAB
        near_b = abs(pos.y() - box.bottom()) <= _CROP_GRAB
        spans_x = box.left() - _CROP_GRAB <= pos.x() <= box.right() + _CROP_GRAB
        spans_y = box.top() - _CROP_GRAB <= pos.y() <= box.bottom() + _CROP_GRAB
        if spans_x and spans_y:
            vertical = "t" if near_t else ("b" if near_b else "")
            horizontal = "l" if near_l else ("r" if near_r else "")
            if vertical or horizontal:
                return vertical + horizontal
        return "move" if box.contains(pos) else None

    def _crop_cursor(self, part: str | None, pos: QPointF | None = None) -> None:
        if part is None and pos is not None and self.crop_under(pos) is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            return
        self.setCursor(
            {
                "tl": Qt.CursorShape.SizeFDiagCursor,
                "br": Qt.CursorShape.SizeFDiagCursor,
                "tr": Qt.CursorShape.SizeBDiagCursor,
                "bl": Qt.CursorShape.SizeBDiagCursor,
                "t": Qt.CursorShape.SizeVerCursor,
                "b": Qt.CursorShape.SizeVerCursor,
                "l": Qt.CursorShape.SizeHorCursor,
                "r": Qt.CursorShape.SizeHorCursor,
                "move": Qt.CursorShape.SizeAllCursor,
            }.get(part or "", Qt.CursorShape.ArrowCursor)
        )

    def _drag_crop(self, pos: QPointF) -> None:
        """Move the held part to the cursor, in normalized frame coordinates.

        Edges are written as absolute positions and the origin/extent recovered
        from the pair, so dragging an edge past its opposite flips the box
        rather than collapsing it against a minimum — `set_crop` gets a rect
        that is already the right way up, and the clamp only ever has to hold
        the box on the frame.
        """
        at = self.magnifier.at(pos, self._content_rect())
        x, y, w, h = crop()
        if self._crop_drag == "move":
            rect = (at.x() - self._crop_grab.x(), at.y() - self._crop_grab.y(), w, h)
        else:
            left, right, top, bottom = x, x + w, y, y + h
            if "l" in self._crop_drag:
                left = at.x()
            if "r" in self._crop_drag:
                right = at.x()
            if "t" in self._crop_drag:
                top = at.y()
            if "b" in self._crop_drag:
                bottom = at.y()
            left, right = min(left, right), max(left, right)
            top, bottom = min(top, bottom), max(top, bottom)
            rect = (left, top, right - left, bottom - top)
        set_crop(rect, self.crop_source)
        self.on_crop()
        self.update()

    # ---- input ------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        detents = event.angleDelta().y() / 120.0
        if detents == 0.0:
            super().wheelEvent(event)
            return
        if self.magnifier.wheel(detents, event.position(), self._content_rect()):
            self.on_zoom()
            self._set_hover(self.block_at(event.position()))
            self.update()
        event.accept()

    def reset_zoom(self) -> None:
        if self.magnifier.reset():
            self.on_zoom()
            self.update()

    def _emit_solo(self) -> None:
        """Ask for the gesture's solo, unless the model already holds it.

        Compared against `self.solo` — what the model applied — and not against
        a record of what was last asked: a request the model dropped is worth
        asking again, and one it satisfied is worth not asking twice, since a
        redundant one costs a repaint of every graph at pointer speed.
        """
        solo = self.hover if self.hover is not None else self.latched
        if solo != self.solo:
            self.on_solo(solo)

    def _set_hover(self, hover: int | None) -> None:
        """One funnel for the block under the pointer, per crossing not per sample."""
        if hover == self.hover:
            return
        self.hover = hover
        self.on_hover(hover)
        self._emit_solo()
        self.update()

    def clear_solo_gesture(self) -> None:
        """What a grid going away means for the gesture: forget hover and pin."""
        self.latched = None
        if self.hover is not None:
            self.hover = None
            self.on_hover(None)
        self._emit_solo()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._crop_drag is not None:
            self._drag_crop(event.position())
            return
        if self.crop_on:
            self._crop_cursor(self.crop_part_at(event.position()), event.position())
            return
        self._set_hover(self.block_at(event.position()))

    def leaveEvent(self, event) -> None:
        del event
        self._set_hover(None)

    def mousePressEvent(self, event) -> None:
        """Take the crop box's held part, or pin the block; the model still decides.

        Unpinning while the pointer is still on the block asks for nothing new
        — hover solos it either way — and that is the whole difference the
        click makes: what leaving the grid reverts to.
        """
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        part = self.crop_part_at(event.position())
        if part is not None:
            self._crop_drag = part
            at = self.magnifier.at(event.position(), self._content_rect())
            self._crop_grab = QPointF(at.x() - crop()[0], at.y() - crop()[1])
            return
        other = self.crop_under(event.position())
        if other is not None:
            select_crop(other)
            return
        block = self.block_at(event.position())
        if block is None:
            return
        self.latched = None if block == self.latched else block
        self._emit_solo()

    def mouseReleaseEvent(self, event) -> None:
        if self._crop_drag is None or event.button() is not Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        self._crop_drag = None
        self._crop_cursor(self.crop_part_at(event.position()), event.position())

    # ---- painting ---------------------------------------------------------

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        content = self._content_rect()
        # Everything after this is clipped to the fit, so a magnified view
        # spills into the letterbox no more than a fitted one does — the same
        # boundary `block_at` reads from the input side.
        painter.setClipRect(content)
        view = self.view_rect()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if self.base is not None:
            painter.drawImage(view, self.base)
        if self.over is not None and not self.peek:
            painter.setOpacity(self.opacity)
            painter.drawImage(view, self.over)
            painter.setOpacity(1.0)
        if self.grid_on and not self.peek:
            self._paint_grid(painter)
        if self.crop_on and not self.peek:
            self._paint_crop(painter, content)
        painter.end()

    def _paint_crop(self, painter: QPainter, content: QRectF) -> None:
        """The scrim on what goes, the box on what stays, handles on the edges.

        The scrim is four rectangles against the clip rather than one path with
        a hole: the removed region is whatever the box is not, and subtracting
        it as geometry is what keeps a magnified box — whose sides run off past
        the letterbox — from painting a seam of unscrimmed frame at the edge.

        Scrimmed against the selected region alone, and the other regions drawn
        on top of the scrim in outline. The canvas is showing one chain, and the
        one it is showing is the walked region's; the others are where the step
        also cut, which is why they are marks on the darkened part rather than
        holes in it.
        """
        box = self.crop_box().intersected(content)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_CROP_SCRIM)
        for outside in (
            QRectF(content.left(), content.top(), content.width(), box.top() - content.top()),
            QRectF(content.left(), box.bottom(), content.width(), content.bottom() - box.bottom()),
            QRectF(content.left(), box.top(), box.left() - content.left(), box.height()),
            QRectF(box.right(), box.top(), content.right() - box.right(), box.height()),
        ):
            if outside.width() > 0 and outside.height() > 0:
                painter.drawRect(outside)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setFont(_plot_font(8, bold=True))
        for index, rect in enumerate(CROPS):
            if index == SELECTED_CROP:
                continue
            other = self.crop_box(rect).intersected(content)
            if other.isEmpty():
                continue
            painter.setPen(QPen(EDGE, 1.0, Qt.PenStyle.DashLine))
            painter.drawRect(other)
            painter.setPen(QPen(DIM))
            painter.drawText(
                QPointF(other.left() + 4, other.top() + 12), str(index + 1)
            )

        painter.setPen(QPen(ACCENT, 1.0))
        painter.drawRect(box)
        painter.drawText(QPointF(box.left() + 4, box.top() + 12), str(SELECTED_CROP + 1))
        thirds = QColor(ACCENT)
        thirds.setAlpha(60)
        painter.setPen(QPen(thirds, 1.0))
        for k in (1, 2):
            x = box.left() + k * box.width() / 3
            y = box.top() + k * box.height() / 3
            painter.drawLine(QPointF(x, box.top()), QPointF(x, box.bottom()))
            painter.drawLine(QPointF(box.left(), y), QPointF(box.right(), y))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ACCENT)
        for px in (box.left(), box.center().x(), box.right()):
            for py in (box.top(), box.center().y(), box.bottom()):
                if px == box.center().x() and py == box.center().y():
                    continue
                painter.drawRect(
                    QRectF(
                        px - _CROP_HANDLE, py - _CROP_HANDLE, 2 * _CROP_HANDLE, 2 * _CROP_HANDLE
                    )
                )

    def _paint_grid(self, painter: QPainter) -> None:
        """Heatmap under, detected squares over — three independent alphas.

        The heat tiles every cell edge to edge, the way v1 blended its colormap
        over the footage. On top, only in-band cells, and a wall is one pixel
        wide *everywhere* — whether it separates a detected cell from bare heat
        or from another detected cell. That costs an asymmetry: a cell owns its
        top and left lines and gives up its bottom and right ones to the
        neighbours that have them, unless there is no detected neighbour there
        to give them to. The reward is that every wall pixel is painted once,
        by one cell, so the border alpha means one thing on screen rather than
        two, and the interior of a detected region — the least informative part
        of the picture — stops getting the heaviest ink.

        Ring and interior stay disjoint pixel regions and the fill takes what
        the walls leave, so border alpha 0 reads as separated blocks and equal
        alphas read as one mass. That separation is the control surface, not a
        rendering accident. Antialiasing stays off so a ring is a square ring.

        v2 bakes the heat layer as one image because its block count makes a
        per-cell loop cost more than the frame it draws over; the mockup's grid
        is small, and a cell loop here keeps heat and ring on the one set of
        edges rather than on Qt's rounding of a scaled image and on ours.
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        ny, nx = self.grid
        xs, ys = self.grid_edges()
        in_band = self.in_band()

        def detected(row: int, col: int) -> bool:
            return 0 <= row < ny and 0 <= col < nx and in_band[row * nx + col]

        if self.heat_alpha > 0.0:
            for b, value in enumerate(self.values):
                row, col = divmod(b, nx)
                painter.fillRect(
                    QRect(xs[col], ys[row], xs[col + 1] - xs[col], ys[row + 1] - ys[row]),
                    _heat_color(value, self.heat_alpha),
                )

        if self.fill_alpha > 0.0 or self.line_alpha > 0.0:
            fill, line = QColor(ACCENT), QColor(ACCENT)
            fill.setAlphaF(self.fill_alpha)
            line.setAlphaF(self.line_alpha)
            for b, on in enumerate(in_band):
                if not on:
                    continue
                row, col = divmod(b, nx)
                x0, x1 = xs[col], xs[col + 1] - 1
                y0, y1 = ys[row], ys[row + 1] - 1
                if x1 < x0 or y1 < y0:  # a cell too small to hold a pixel
                    continue
                right_wall = x1 > x0 and not detected(row, col + 1)
                bottom_wall = y1 > y0 and not detected(row + 1, col)
                if self.line_alpha > 0.0:
                    painter.fillRect(QRect(x0, y0, x1 - x0 + 1, 1), line)
                    if y1 > y0:
                        painter.fillRect(QRect(x0, y0 + 1, 1, y1 - y0), line)
                    if right_wall:
                        painter.fillRect(QRect(x1, y0 + 1, 1, y1 - y0), line)
                    if bottom_wall:
                        # The left wall already holds this row's first pixel,
                        # and the right wall its last one if it was drawn.
                        bx1 = x1 - 1 if right_wall else x1
                        if bx1 >= x0 + 1:
                            painter.fillRect(QRect(x0 + 1, y1, bx1 - x0, 1), line)
                if self.fill_alpha > 0.0:
                    right = x1 - 1 if right_wall else x1
                    bottom = y1 - 1 if bottom_wall else y1
                    if right >= x0 + 1 and bottom >= y0 + 1:
                        painter.fillRect(QRect(x0 + 1, y0 + 1, right - x0, bottom - y0), fill)

        if self.solo is not None and self.solo < ny * nx:
            row, col = divmod(self.solo, nx)
            painter.setPen(QPen(TEXT, 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(
                QRect(xs[col], ys[row], xs[col + 1] - xs[col], ys[row + 1] - ys[row]).adjusted(
                    1, 1, -1, -1
                )
            )


class MockComposite(QWidget):
    """composite_view.py's StepCompositeView: header, surface, the controls.

    Raw video is not a mode a viewer toggles: it is what the source step makes,
    and it is on screen exactly when that step is the one walked. Neither is
    full current state a mode, which is the composite with the tail walked.
    Every step after the source shows the contribution of one operation: which
    pixels it removed, kept, or invented, which is spatial information no
    per-frame scalar plot can carry.
    """

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._caption = ""
        self._index = index
        #: "frame", "crop", "overlay", or "grid" — what the surface is showing.
        self._mode = "overlay"
        self._pane = _CompositePane()
        self._pane.on_hover = lambda block: self._update_tag()
        self._pane.on_zoom = self.update
        self._pane.on_crop = self._crop_moved
        self._pane.crop_source = self
        #: A block index to solo, or None. Re-emitted; the owner applies it.
        self.on_solo = lambda block: None
        self._pane.on_solo = lambda block: self.on_solo(block)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(_DEFAULT_OPACITY)
        self._slider.setFixedWidth(120)
        self._slider.setToolTip("Output opacity over the step's input")
        self._slider.valueChanged.connect(self._on_opacity)
        self._readout = self._tag_label(f"{_DEFAULT_OPACITY}%")

        self._grid_sliders = tuple(
            self._grid_slider(step, tip)
            for step, tip in (
                (_DEFAULT_FILL_STEP, "In-band fill alpha"),
                (_DEFAULT_LINE_STEP, "Detected border alpha"),
                (_DEFAULT_HEAT_STEP, "Heatmap alpha"),
            )
        )
        for slider, apply in zip(self._grid_sliders, ("fill_alpha", "line_alpha", "heat_alpha")):
            slider.valueChanged.connect(lambda step, name=apply: self._on_grid_alpha(name, step))
        self._grid_tags = tuple(self._tag_label(text) for text in ("fill", "border", "heat"))
        self._tag = self._tag_label("input · output")

        footer = QHBoxLayout()
        footer.setContentsMargins(_PANE_MARGIN, 0, _PANE_MARGIN, 4)
        footer.addWidget(self._tag)
        footer.addStretch(1)
        for tag, slider in zip(self._grid_tags, self._grid_sliders):
            footer.addWidget(tag)
            footer.addWidget(slider)
        footer.addWidget(self._slider)
        footer.addWidget(self._readout)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, _HEADER_H, 0, 0)
        column.setSpacing(2)
        column.addWidget(self._pane, 1)
        column.addLayout(footer)
        self.setMinimumHeight(_HEADER_H + 160 + _FOOTER_H)

        # Shift-to-peek listens at the application so it works wherever the
        # keyboard focus happens to sit; Qt drops the filter with this object.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        BAND_WATCHERS.append(self._pane)
        # The other editor of the crop writes the same value, and what the
        # canvas has to redo for it is everything a walk would: the frames are
        # cut from the box and the grid is what the box leaves.
        watch_crop(self, lambda: self.compose(self._index))
        self.compose(index)

    def _grid_slider(self, step: int, tip: str) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, _GRID_STEPS)
        slider.setValue(step)
        slider.setFixedWidth(64)
        slider.setToolTip(f"{tip} (0 to 1 in 0.2 steps)")
        return slider

    def _tag_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(_plot_font(8))
        label.setStyleSheet(f"color: {DIM.name()};")
        return label

    # ---- what it is told --------------------------------------------------

    def compose(self, index: int) -> None:
        """Show the walked step: its output over its input, its box, or its grid."""
        self._index = index
        composed, fallback = _composed_step(index)
        self._caption = NODES[composed][0]
        if fallback:
            self._caption = f"{self._caption} (deepest rendered)"
        base, over = _composite_frames(composed)
        self._pane.base, self._pane.over = base, over
        grid_on = composed >= _BLOCKS_INDEX
        if self._pane.grid_on and not grid_on:
            self._pane.clear_solo_gesture()
        self._pane.grid_on = grid_on
        self._pane.crop_on = composed == _CROP_INDEX
        # The grid the crop leaves, and with it the values the density band is
        # read against: both are re-derived here rather than held, so a box
        # dragged while the walk sits on the source cannot leave the block step
        # showing cells for a crop that is gone.
        self._pane.grid = block_grid()
        self._pane.values = block_power()
        if self._pane.solo is not None and self._pane.solo >= len(self._pane.values):
            self._pane.clear_solo_gesture()
        if not self._pane.crop_on:
            self._pane.setCursor(Qt.CursorShape.ArrowCursor)
        self._mode = (
            "grid"
            if grid_on
            else ("crop" if self._pane.crop_on else ("overlay" if over is not None else "frame"))
        )
        self._show_controls()
        self._pane.reset_zoom()  # a new picture is a new fit
        self._update_tag()
        self._pane.update()
        self.update()

    def set_solo(self, block: int | None) -> None:
        """The soloed block, as the model has it — the only thing drawn as solo."""
        self._pane.solo = block
        self._pane.update()

    @property
    def pane(self) -> _CompositePane:
        return self._pane

    # ---- internals --------------------------------------------------------

    def eventFilter(self, watched, event) -> bool:
        """Shift-to-peek, pressed anywhere: overlays off while it is held."""
        kind = event.type()
        if (
            kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            and isinstance(event, QKeyEvent)
            and event.key() == Qt.Key.Key_Shift
            and not event.isAutoRepeat()
        ):
            self._pane.peek = kind is QEvent.Type.KeyPress
            self._pane.update()
        return super().eventFilter(watched, event)

    def _show_controls(self) -> None:
        """Only the controls that act on what is drawn.

        A source frame has neither an overlay to fade nor cells to shade, so it
        gets no slider at all rather than a dead one — a control that moves and
        changes nothing is the strongest claim a surface can make about what it
        is showing, and it would be false here.
        """
        for widget in (*self._grid_tags, *self._grid_sliders):
            widget.setVisible(self._mode == "grid")
        for widget in (self._slider, self._readout):
            widget.setVisible(self._mode == "overlay")

    def _crop_moved(self) -> None:
        """A drag on the box: the readout now, the frames on the next compose.

        Not a recompose: the step being drawn is the crop's own input, which the
        box does not change, and cutting four images per mouse-move to show a
        picture that is identical either way is the tuning loop's whole budget
        spent on nothing.
        """
        self._update_tag()
        self.update()

    def _update_tag(self) -> None:
        if self._mode == "frame":
            self._tag.setText(f"{SOURCES[SELECTED_SOURCE]} — decoded frame")
            return
        if self._mode == "crop":
            x, y, w, h = crop()
            ny, nx = block_grid()
            self._tag.setText(
                f"region {SELECTED_CROP + 1} of {len(CROPS)} — "
                f"keep {w:.0%}×{h:.0%} at ({x:.0%}, {y:.0%}) — "
                f"{ny}x{nx} blocks downstream"
            )
            return
        if not self._pane.grid_on:
            self._tag.setText("input · output")
            return
        hover = self._pane.hover
        if hover is None:
            self._tag.setText(grid_caption())
            return
        row, col = divmod(hover, self._pane.grid[1])
        state = "in band" if self._pane.in_band()[hover] else "out"
        self._tag.setText(f"block ({row},{col}) — {self._pane.values[hover]:.2f} — {state}")

    def _on_opacity(self, value: int) -> None:
        self._pane.opacity = value / 100.0
        self._readout.setText(f"{value}%")
        self._pane.update()

    def _on_grid_alpha(self, name: str, step: int) -> None:
        setattr(self._pane, name, step / _GRID_STEPS)
        self._pane.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(DIM)
        painter.setFont(_plot_font(8, bold=True, spaced=True))
        title = {
            "frame": "SOURCE FRAME",
            "crop": f"CROP REGION {SELECTED_CROP + 1}/{len(CROPS)}",
        }.get(self._mode, "STEP COMPOSITE")
        if self._caption:
            title = f"{title} — {self._caption.upper()}"
        if self._pane.grid_on:
            title = f"{title} — HOVER SOLOS · CLICK PINS · SHIFT PEEKS"
        if self._pane.crop_on:
            title = f"{title} — DRAG THE BOX · CLICK ANOTHER TO WALK IT · SHIFT PEEKS"
        # Magnified is a state a user can forget they are in, and at 8x a grid
        # shows a handful of cells that look like the whole thing.
        if self._pane.magnifier.magnified:
            title = f"{title} — {self._pane.magnifier.zoom:.1f}X"
        painter.drawText(QRectF(10, 4, self.width() - 20, 14), 0, title)
        painter.end()


# ---------------------------------------------------------------------------
# The generic trace: graph_panel.py, for the step that has no plot of its own.

_GRAPH_HEIGHT = 96


class MockGraph(QWidget):
    """A trace with one gated (NaN) stretch, one polyline per unbroken run."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # The band plots fix their height; this one grows, so it needs a floor
        # for the pin to have a height to fit itself to.
        self.setMinimumHeight(_GRAPH_HEIGHT)
        rng = random.Random(21)
        self._values: list[float | None] = []
        value = 0.3
        for i in range(240):
            value += (rng.random() - 0.5) * 0.16
            if 90 < i < 115:
                value += 0.10
            if 160 < i < 170:
                value += 0.14
            value = max(0.02, min(0.95, value))
            self._values.append(None if 125 < i < 140 else value)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _SURFACE)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(_TRACE, 1.6))
        runs: list[list[QPointF]] = [[]]
        for i, value in enumerate(self._values):
            if value is None:
                if runs[-1]:
                    runs.append([])
                continue
            runs[-1].append(
                QPointF(
                    self.width() * (i + 0.5) / len(self._values),
                    self.height() * (1.0 - value),
                )
            )
        for run in runs:
            if len(run) > 1:
                painter.drawPolyline(QPolygonF(run))
        painter.end()


# ---------------------------------------------------------------------------
# The rail: rail.py, with the tick colors the stylesheet will one day own.

_TICK_SIZE = 8


class _Tick(QWidget):
    def __init__(self, current: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_TICK_SIZE, _TICK_SIZE)
        self._current = current

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(56, 116, 200) if self._current else QColor(201, 201, 201))
        painter.end()


class NodeRail(QWidget):
    def __init__(self, node_count: int, current: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(_TICK_SIZE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for index in range(node_count):
            layout.addWidget(_Tick(current=index == current))
        layout.addStretch(1)


# ---------------------------------------------------------------------------
# The sliding track: control.py's _SlidingPanes, verbatim in behavior.

_SLIDE_DURATION_MS = 260
# Three positions, not four: the save screen was the write list and a Run
# button, and both are the output step's — so the last position is the step form
# it stands on, reached the way every other step's is.
_POS_PROJECT, _POS_PIPELINE, _POS_STEP = range(3)
_POS_LAST = _POS_STEP


class _SlidingPanes(QWidget):
    def __init__(self, panes: list[QWidget], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._panes = panes
        self._current = 0
        self._offset = 0.0
        self._track = QWidget(self)
        for pane in self._panes:
            pane.setParent(self._track)
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(_SLIDE_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._relayout()

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self._track.move(-round(self._offset * self.width()), 0)

    offset = Property(float, _get_offset, _set_offset)

    def current_index(self) -> int:
        return self._current

    def set_current(self, index: int) -> None:
        running = self._animation.state() == QAbstractAnimation.State.Running
        if index == self._current and not running:
            return
        self._current = index
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(float(index))
        self._animation.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        width, height = self.width(), self.height()
        self._track.resize(width * len(self._panes), height)
        for index, pane in enumerate(self._panes):
            pane.setGeometry(index * width, 0, width, height)
        self._set_offset(self._offset)


# ---------------------------------------------------------------------------
# The four positions' contents, each a mock of its module.


# ---------------------------------------------------------------------------
# The pipeline position: v2's chain stack — cards under fixed stage headers,
# the source card above the scroll, the graphs in the card that makes them.


def _ramp(value: float, warm: bool) -> QColor:
    """A sequential ramp per plot: dark floor to the plot's own hot end."""
    v = max(0.0, min(1.0, value))
    if warm:  # scalogram: violet to amber
        stops = ((16, 14, 28), (96, 58, 138), (238, 158, 66))
    else:  # density: near-black to the accent teal
        stops = ((16, 20, 24), (32, 92, 84), (120, 226, 204))
    if v < 0.5:
        a, b, t = stops[0], stops[1], v * 2
    else:
        a, b, t = stops[1], stops[2], (v - 0.5) * 2
    return QColor(*(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def _heat_image(cols: int, rows: int, value, warm: bool) -> QImage:
    """A (cols, rows) surface baked once and stretched at paint time.

    v2 keeps its heatmaps as images for the reason the drag makes visible here:
    a per-cell paint loop runs on every mouse-move, and the tuning loop's whole
    claim is that the graphs refill faster than the footage plays.
    """
    image = QImage(cols, rows, QImage.Format.Format_ARGB32)
    for x in range(cols):
        for y in range(rows):
            image.setPixelColor(x, y, _ramp(value(x, y), warm=warm))
    return image


# v2's band_plot.py frame: the margins hold the title row on top and the
# handles' readouts on the right, which is why a handle line can run past the
# plot into a dot and a value.
_MARGIN_L, _MARGIN_R, _MARGIN_T, _MARGIN_B = 48, 66, 24, 8
_GRAB_PX = 8.0
_EDGE_PX = 4.0  # past this much beyond the plot edge, a drag means unbounded.
_PLAYHEAD_AT = 0.37  # the same position the timeline strip paints.

# The Morlet bank the frequency band snaps to: twelve voices per octave across
# the scalogram's axis. `unbounded = False` is this bank having edges.
SCALOGRAM_BANK = [0.25 * 2 ** (k / 12) for k in range(61)]


def snap_to_bank(band: tuple[float, float]) -> tuple[float, float]:
    """The band the transform would actually use: each edge at its nearest voice."""
    return tuple(min(SCALOGRAM_BANK, key=lambda f: abs(f - edge)) for edge in band)


class MockBandPlot(QWidget):
    """band_plot.py's shared frame: title row, grid, playhead, two handles.

    The handle is v2's whole of it: both edges always drawn, the line running
    into the right margin to a dot and its value, an unbounded edge dimmed
    rather than absent, and the drag — grab within `_GRAB_PX` of a line or its
    readout dot, past the edge means ±inf unless the subclass clamps, and a
    drag through the other handle swaps which one is held so the band cannot
    invert. What the mockup has no owner for is the *other* meaning of a drag:
    v2 scrubs the playhead with any press off a handle, and here nothing owns
    a playhead, so a press off a handle does nothing.
    """

    title = ""
    unbounded = True

    def __init__(
        self,
        height: int,
        key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        self._key = key
        self._drag: str | None = None

    @property
    def _band(self) -> tuple[float, float] | None:
        return BANDS.get(self._key)

    @_band.setter
    def _band(self, value: tuple[float, float]) -> None:
        BANDS[self._key] = value

    # ---- the value axis ---------------------------------------------------

    def _fwd(self, value: float) -> float:
        return value

    def _inv(self, t: float) -> float:
        return t

    def _range(self) -> tuple[float, float]:
        return 0.0, 1.0

    def format_value(self, value: float) -> str:
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.3g}"

    def readout_text(self) -> str:
        return ""

    def gate(self) -> list[bool]:
        return []

    # ---- geometry ---------------------------------------------------------

    def plot_rect(self) -> QRectF:
        return QRectF(self.rect().adjusted(_MARGIN_L, _MARGIN_T, -_MARGIN_R, -_MARGIN_B))

    def y_of(self, value: float) -> float:
        lo, hi = self._range()
        r = self.plot_rect()
        value = min(max(value, lo), hi)
        t = (self._fwd(value) - self._fwd(lo)) / max(self._fwd(hi) - self._fwd(lo), 1e-12)
        return r.bottom() - t * r.height()

    def value_of(self, y: float) -> float:
        lo, hi = self._range()
        r = self.plot_rect()
        t = min(max((r.bottom() - y) / max(r.height(), 1.0), 0.0), 1.0)
        return self._inv(self._fwd(lo) + t * (self._fwd(hi) - self._fwd(lo)))

    def handle_y(self, which: str) -> float:
        lo, hi = self._range()
        if self._band is None:
            value = lo if which == "lo" else hi
        else:
            value = self._band[0] if which == "lo" else self._band[1]
        return self.y_of(min(max(value, lo), hi))

    # ---- the gesture ------------------------------------------------------

    def _grabbable(self, pos: QPointF) -> str | None:
        """The handle a press at `pos` grabs, or None.

        The zone reaches into the right margin so the readout dot is a target
        too; vertically it is `_GRAB_PX` exactly.
        """
        zone = QRectF(self.plot_rect()).adjusted(0.0, -_GRAB_PX, float(_MARGIN_R), _GRAB_PX)
        if not zone.contains(pos):
            return None
        near = min(("lo", "hi"), key=lambda w: abs(self.handle_y(w) - pos.y()))
        return near if abs(self.handle_y(near) - pos.y()) <= _GRAB_PX else None

    def mousePressEvent(self, event) -> None:
        if event.button() is not Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._drag = self._grabbable(event.position())
        if self._drag is None:
            super().mousePressEvent(event)
            return
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag is None:
            super().mouseMoveEvent(event)
            return
        self._drag_handle(event.position().y())
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag is None or event.button() is not Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        self._drag = None
        event.accept()

    def _drag_handle(self, y: float) -> None:
        r = self.plot_rect()
        band = self._band
        lo, hi = band if band is not None else (-math.inf, math.inf)
        if self.unbounded and y < r.top() - _EDGE_PX:
            value = math.inf
        elif self.unbounded and y > r.bottom() + _EDGE_PX:
            value = -math.inf
        else:
            value = self.value_of(y)
        if self._drag == "lo":
            lo = value
            if lo > hi:
                lo, hi = hi, lo
                self._drag = "hi"
        else:
            hi = value
            if hi < lo:
                lo, hi = hi, lo
                self._drag = "lo"
        self._band = (lo, hi)
        self.band_changed()
        self.update()

    def band_changed(self) -> None:
        """The cheap tier: what a subclass re-derives per move, not per release."""

    # ---- painting ---------------------------------------------------------

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), PANEL)
        r = self.plot_rect()

        painter.setPen(DIM)
        painter.setFont(_plot_font(8, bold=True, spaced=True))
        head = QRectF(10, 4, self.width() - 20, 14)
        painter.drawText(head, 0, self.title.upper())
        readout = self.readout_text()
        if readout:
            painter.drawText(head, int(Qt.AlignmentFlag.AlignRight), readout)

        grid = QColor(LINE)
        grid.setAlpha(90)
        painter.setPen(QPen(grid, 1.0))
        for k in range(1, 4):
            y = r.top() + k * r.height() / 4
            painter.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))

        painter.save()
        painter.setClipRect(r)
        fill = QColor(DETECT)
        fill.setAlpha(52)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        for span in self._gate_rects(r):
            painter.drawRect(span)
        self.paint_content(painter, r)
        painter.restore()
        # Outside the clip: v2 draws its frequency ticks inside `paint_content`,
        # where the plot-rect clip eats them. Here they get their own pass.
        self.paint_axis(painter, r)

        x = r.left() + r.width() * _PLAYHEAD_AT
        playhead = QColor(TEXT)
        playhead.setAlpha(130)
        painter.setPen(QPen(playhead, 1.0))
        painter.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))

        self._paint_handles(painter, r)
        painter.end()

    def paint_content(self, painter: QPainter, r: QRectF) -> None:
        """The surface itself, clipped to `r`. Subclasses override."""

    def paint_axis(self, painter: QPainter, r: QRectF) -> None:
        """Value-axis labels, in the left margin and so outside the clip."""

    def _gate_rects(self, r: QRectF) -> list[QRectF]:
        """Gate spans as rectangles, each floored to 1 px so one frame survives."""
        gate = self.gate()
        if not gate:
            return []
        step = r.width() / len(gate)
        rects: list[QRectF] = []
        start: int | None = None
        for i, on in enumerate([*gate, False]):
            if on and start is None:
                start = i
            elif not on and start is not None:
                x0 = r.left() + start * step
                rects.append(QRectF(x0, r.top(), max((i - start) * step, 1.0), r.height()))
                start = None
        return rects

    def _paint_handles(self, painter: QPainter, r: QRectF) -> None:
        band = self._band
        for which in ("lo", "hi"):
            y = self.handle_y(which)
            color = QColor(BAND)
            value = None if band is None else (band[0] if which == "lo" else band[1])
            if value is None or math.isinf(value):
                color.setAlpha(110)
            painter.setPen(QPen(color, 1.0))
            painter.drawLine(QPointF(r.left(), y), QPointF(r.right() + 22.0, y))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(r.right() + 22.0, y), 3.2, 3.2)
            painter.setPen(QPen(color, 1.0))
            painter.setFont(_plot_font(8))
            painter.drawText(
                QRectF(r.right() + 28.0, y - 8.0, _MARGIN_R - 30.0, 16.0),
                int(Qt.AlignmentFlag.AlignVCenter),
                "—" if value is None else self.format_value(value),
            )


class MockScalogram(MockBandPlot):
    """Pooled Morlet power on a log-frequency axis, the band drawn on top."""

    title = "scalogram"
    unbounded = False  # the bank has edges; handles clamp to them

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(height=116, key="morlet-1", parent=parent)
        self._cols, self._rows = 240, 64
        rng = random.Random(5)
        self._power = [
            [
                0.12 * rng.random()
                + 0.85
                * math.exp(-((y - (30 + 10 * math.sin(x / 24) + 6 * rng.random())) ** 2) / 60)
                + (0.5 * math.exp(-((y - 48) ** 2) / 30) if 90 < x < 130 else 0.0)
                for y in range(self._rows)
            ]
            for x in range(self._cols)
        ]
        # The COI fade: within an e-folding of either end the value decays.
        self._image = _heat_image(
            self._cols,
            self._rows,
            lambda x, y: self._power[x][y]
            * (0.35 + 0.65 * min(1.0, min(x, self._cols - 1 - x) / 28)),
            warm=True,
        )

    def _fwd(self, value: float) -> float:
        return math.log10(max(value, 1e-12))

    def _inv(self, t: float) -> float:
        return 10.0**t

    def _range(self) -> tuple[float, float]:
        return 0.25, 8.0

    def format_value(self, value: float) -> str:
        return f"{value:.2f}"

    def readout_text(self) -> str:
        """The truth line: what the bank does with the band, not what was dragged.

        The handle stays where the mouse left it and this says where the
        transform lands — the pair is the point, and collapsing them would hide
        the snap the guidance promises.
        """
        lo, hi = snap_to_bank(self._band)
        return f"{lo:.2f} – {hi:.2f} Hz snapped"

    def paint_content(self, painter: QPainter, r: QRectF) -> None:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(r, self._image)

    def paint_axis(self, painter: QPainter, r: QRectF) -> None:
        painter.setPen(DIM)
        painter.setFont(_plot_font(7))
        low, high = self._range()
        for f in (low, math.sqrt(low * high), high):
            painter.drawText(
                QRectF(r.left() - 42.0, self.y_of(f) - 7.0, 38.0, 14.0),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                f"{f:.3g} Hz",
            )


class MockDensity(MockBandPlot):
    """Band power by block: the whole population per frame, solo trace on top."""

    title = "band power by block"

    def __init__(self, parent: QWidget | None = None) -> None:
        # The lower handle is placed; the upper rests unbounded, dimmed.
        super().__init__(height=104, key="morlet-1/density", parent=parent)
        self._cols, self._rows = 240, 44
        rng = random.Random(11)
        centers = []
        c = 0.65
        for x in range(self._cols):
            c = max(0.15, min(0.9, c + (rng.random() - 0.5) * 0.06 - (0.012 if 90 < x < 130 else 0)))
            centers.append(c)
        self._centers = centers
        self._spread = [0.05 + 0.08 * rng.random() for _ in range(self._cols)]
        self._image = _heat_image(self._cols, self._rows, self._value, warm=False)

    def _value(self, x: int, y: int) -> float:
        frac = y / self._rows
        d = (frac - self._centers[x]) ** 2 / (2 * self._spread[x] ** 2)
        return 0.9 * math.exp(-d) + 0.25 * math.exp(-((frac - 0.92) ** 2) / 0.01)

    def band_changed(self) -> None:
        """The cells the canvas rings are the ones this handle just moved past."""
        notify_band_changed()

    def _range(self) -> tuple[float, float]:
        return 0.0, 1.0

    def format_value(self, value: float) -> str:
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.2f}"

    def paint_content(self, painter: QPainter, r: QRectF) -> None:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(r, self._image)
        cw = r.width() / self._cols
        painter.setPen(QPen(ACCENT, 1.4))
        painter.drawPolyline(
            QPolygonF(
                [
                    QPointF(
                        r.left() + x * cw + cw / 2,
                        r.top() + self._centers[x] * r.height() + 1.5,
                    )
                    for x in range(0, self._cols, 2)
                ]
            )
        )


# How much taller than the tallest thing on it the count axis runs: a peak drawn
# on the frame reads as clipped rather than as the maximum.
_HEADROOM = 1.06


class MockCountPlot(MockBandPlot):
    """Elements in band, windowed over D — count_plot.py's detection style.

    The axis is the data, not the region: a threshold of 30 blocks out of 4096
    on a 0..B axis is a line on the bottom pixel row with no handle travel above
    it, so the top is the tallest thing actually on the plot — the series peak,
    or a band edge above it — capped at B, and the title row says which ceiling
    that is. Unioning the band in is what keeps a threshold dragged above the
    peak reachable; freezing the axis for the gesture is what stops the handle
    chasing the rescale that union causes.
    """

    title = "elements in band"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(height=110, key="count-1", parent=parent)
        rng = random.Random(17)
        values = []
        v = 6.0
        for i in range(240):
            v = max(0.0, v + (rng.random() - 0.5) * 8 + (14 if 88 < i < 118 else 0) * rng.random() - (3 if i > 118 else 0))
            values.append(min(v, 96.0))
        self._values = values
        self._elements = 4096
        self._peak = max(values)
        # The axis a handle drag started in, held for its duration.
        self._frozen: tuple[float, float] | None = None

    def _range(self) -> tuple[float, float]:
        if self._frozen is not None:
            return self._frozen
        top = self._peak
        if self._band is not None:
            for edge in self._band:
                if math.isfinite(edge):
                    top = max(top, edge)
        top = min(top * _HEADROOM, float(self._elements))
        return 0.0, top if top > 0.0 else min(1.0, float(self._elements))

    def format_value(self, value: float) -> str:
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.0f}"

    def readout_text(self) -> str:
        """The scale label: the ceiling in force and the region it is part of.

        Both numbers always, plus `· full` where they meet — "0-7 of 4096
        blocks" and "0-4096 of 4096 blocks · full" are the same sentence with
        different numbers, and an axis that moved without saying so would draw
        two tunings two orders of magnitude apart identically.
        """
        top = self._range()[1]
        full = " · full" if top >= float(self._elements) else ""
        return f"0-{top:.0f} of {self._elements} blocks{full}"

    def gate(self) -> list[bool]:
        return [value >= self._band[0] for value in self._values]

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if self._drag in ("lo", "hi"):
            self._frozen = self._range()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self._drag is None and self._frozen is not None:
            self._frozen = None
            self.update()

    def paint_content(self, painter: QPainter, r: QRectF) -> None:
        step = r.width() / len(self._values)
        # Green is a status color, and this is the only plot that paints it as
        # a series: the trace carries it because a threshold is placed. A
        # disarmed detector still shows the signal it would count, dimmed.
        painter.setPen(QPen(DETECT if self._band is not None else DIM, 1.6))
        painter.drawPolyline(
            QPolygonF(
                [
                    QPointF(r.left() + i * step + step / 2, self.y_of(value))
                    for i, value in enumerate(self._values)
                ]
            )
        )


class ChainCard(QWidget):
    """One card of the stack: panel fill, hairline edge, accent when current.

    A card with `on_select` is the walk's target as well as its display: the
    click is the pointer's ↑/↓, so it moves the same selection the rail ticks
    and the step pane read, and does not touch the pin. `on_open` is the
    pointer's →: the second click of a double takes the selection forward.
    """

    def __init__(
        self,
        selected: bool,
        on_select=None,
        on_open=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._selected = selected
        self._on_select = on_select
        self._on_open = on_open
        self._hovered = False
        if on_select is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if self._on_select is not None:
            self._hovered = True
            self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if self._on_select is None or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        event.accept()
        self._on_select()

    def mouseDoubleClickEvent(self, event) -> None:
        if self._on_open is None or event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        event.accept()
        self._on_open()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL_HOT if self._hovered else PANEL)
        edge = LINE
        if self._selected:
            edge = ACCENT
        elif self._hovered:
            edge = QColor(ACCENT)
            edge.setAlpha(120)
        painter.setPen(QPen(edge, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()


def _dim_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"color: rgb({DIM.red()},{DIM.green()},{DIM.blue()}); font-size: 11px;")
    return label


def _select_source(index: int) -> None:
    global SELECTED_SOURCE
    SELECTED_SOURCE = index


def _source_chooser(on_change) -> QWidget:
    """The video the chain reads: the project's sources, or a file off disk.

    Browsing appends rather than replaces. A project is a set of replicates
    scored the same way, and the one-off file a user opens to compare against
    them is not a departure from the set — a picker that forgot the six would
    make every comparison a re-navigation.
    """
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    combo = QComboBox()
    combo.addItems(SOURCES)
    combo.setCurrentIndex(SELECTED_SOURCE)
    combo.setMinimumWidth(150)
    combo.currentIndexChanged.connect(
        lambda index: (_select_source(index), on_change())
    )

    browse = QToolButton()
    browse.setText("…")
    browse.setAutoRaise(True)
    browse.setToolTip("Open a video file")
    browse.setStyleSheet(f"color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()}); border: 0;")
    browse.clicked.connect(lambda: _browse_for_source(combo))

    layout.addWidget(combo)
    layout.addWidget(browse)
    return row


def _browse_for_source(combo: QComboBox) -> None:
    """Add the chosen file to the sources and select it; selecting is what applies it."""
    path, _filter = QFileDialog.getOpenFileName(
        combo, "Open a video", "", "Video (*.mp4 *.avi *.mov *.mkv);;All files (*)"
    )
    if not path:
        return
    name = Path(path).name
    if name not in SOURCES:
        SOURCES.append(name)
        combo.addItem(name)
    combo.setCurrentIndex(SOURCES.index(name))


_CROP_FIELDS = ("x", "y", "width", "height")


def _percent_box(value: float, tip: str) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setDecimals(1)
    box.setRange(0.0, 100.0)
    box.setSingleStep(1.0)
    box.setSuffix(" %")
    box.setValue(value * 100.0)
    box.setToolTip(tip)
    box.setFixedWidth(74)
    return box


def _crop_pair(first: int, second: int) -> QWidget:
    """Two of the crop's four numbers, typed — ADR 12's other editor of the box.

    Typing goes through `set_crop`, the same clamp the drag does, and then pulls
    every editor including this one: a number the clamp moved has to come back
    changed, or the field would keep claiming a crop the pipeline never had.
    Walking to another region arrives here as the same pull, which is what makes
    four boxes enough for a step with more than one rect: they are the editor of
    whichever region is selected, not of a region.
    Percentages rather than pixels because the value is normalized to the frame,
    and a source of another size would make a pixel field lie on load.
    """
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    fields = (first, second)
    boxes = tuple(
        _percent_box(crop()[i], f"Crop {_CROP_FIELDS[i]}, as a fraction of the frame")
        for i in fields
    )

    def push() -> None:
        rect = list(crop())
        for i, box in zip(fields, boxes):
            rect[i] = box.value() / 100.0
        set_crop(tuple(rect))

    def pull() -> None:
        for i, box in zip(fields, boxes):
            box.blockSignals(True)
            box.setValue(crop()[i] * 100.0)
            box.blockSignals(False)

    for box in boxes:
        box.valueChanged.connect(push)
        layout.addWidget(box)
    watch_crop(row, pull)
    return row


def _crop_count() -> QWidget:
    """How many regions the step cuts, and the two buttons that change it.

    The count is on the card and the regions themselves are in the fan below it:
    a step's card holds what its knobs are, and where its outputs go is the
    stack's to draw. Adding one selects it, because the region a user just made
    is the one they are about to place.
    """
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    count = _dim_label("")
    add = _mini_button("+", "Cut another region")
    drop = _mini_button("−", "Drop the selected region")

    def pull() -> None:
        count.setText(f"{len(CROPS)} · showing {SELECTED_CROP + 1}")
        drop.setEnabled(len(CROPS) > 1)

    add.clicked.connect(lambda: add_crop())
    drop.clicked.connect(lambda: remove_crop())
    pull()
    watch_crop(row, pull)

    layout.addWidget(count)
    layout.addWidget(add)
    layout.addWidget(drop)
    return row


def _mini_button(text: str, tip: str) -> QToolButton:
    button = QToolButton()
    button.setText(text)
    button.setAutoRaise(True)
    button.setToolTip(tip)
    button.setStyleSheet(f"color: rgb({DIM.red()},{DIM.green()},{DIM.blue()}); border: 0;")
    return button


def _writes_summary() -> str:
    """What the card says the output holds, in the room a knob has."""
    on = [product for _step, product, checked in WRITES if checked]
    return ", ".join(on) if on else "nothing ticked"


def _knobs_for(index: int, on_source_change=lambda: None) -> list[tuple[str, QWidget]]:
    """The knobs of one step. A thunk per index, not a widget per index.

    A dict of built widgets is evaluated whole before it is subscripted, so the
    stack would build every step's knobs seven times over and drop all but one
    — parentless, undeletable, and for the crop pair still registered against
    the value it edits, pulling into spin boxes nobody can see.
    """
    if index in RETOOLED:
        return []
    return {
        0: lambda: [("video", _source_chooser(on_source_change))],
        1: lambda: [
            ("regions", _crop_count()),
            ("origin", _crop_pair(0, 1)),
            ("size", _crop_pair(2, 3)),
        ],
        2: lambda: [("factor", _spin(0.5))],
        3: lambda: [("mode", _choice(["per-frame", "window"]))],
        4: lambda: [("estimator", _choice(["median", "mean", "minimum"]))],
        5: lambda: [("channel", _choice(["value", "saturation", "hue"]))],
        6: lambda: [("floor", _spin(0.05))],
        7: lambda: [
            ("block", _int_spin(16)),
            ("signal", _choice(["mean |diff|", "flow magnitude"])),
        ],
        8: lambda: [],
        9: lambda: [("D", _int_spin(12))],
        10: lambda: [("writes", _dim_label(_writes_summary()))],
        # An added step has none: the mock's knobs are written per position and
        # a step that arrived at run time was never one of them. The real form
        # is generated from the tool's params, so this is the one thing the
        # referent cannot show about a step it just made.
    }.get(index, list)()


def _plots_for(index: int) -> list[QWidget]:
    """Fresh instances every call: the stack and the pin cannot share a widget."""
    if index in RETOOLED:
        return []
    if index == _BLOCKS_INDEX:
        return [MockGraph()]
    if index == 8:
        return [MockScalogram(), MockDensity()]
    if index == 9:
        return [MockCountPlot()]
    return []


#: What a step with no plot says in the pinned slot. Crop has a surface — it is
#: the canvas above the slot, which is where a rect param's editor is drawn, and
#: the generic line would call that nothing.
NO_SURFACE_NOTE = {
    _CROP_INDEX: "the boxes on the canvas are this step's surface — drag them there, or type one here",
    _OUTPUT_INDEX: "the write list is this step's surface — tick it in the settings, and the edges follow",
}
_NO_SURFACE_DEFAULT = "this step has no surface — its knobs are the whole of it"


def _stage_of(index: int) -> tuple[str, str]:
    """The stage holding a step, and its type chip."""
    return next((stage, chip) for stage, chip, members in STAGES if index in members)


def _swap_button(index: int, on_swap) -> QToolButton:
    """Open the box over this card: what could stand where this step stands.

    Not a menu of its own. Adding and swapping are the same question asked of
    two kinds of position — a gap has no tool in it, a card has one — so the
    box that answers it for a gap answers it here, standing where the card is
    instead of between two. A second widget rendering the same shortlist would
    be the same derivation displayed twice.
    """
    _stage, chip = _stage_of(index)
    button = QToolButton()
    button.setText("⇄")
    button.setAutoRaise(True)
    button.setToolTip(f"Swap for another {chip} tool — the chain is unchanged until you pick")
    button.clicked.connect(lambda: on_swap(index))
    button.setStyleSheet(
        f"QToolButton {{ color: rgb({DIM.red()},{DIM.green()},{DIM.blue()}); border: 0; }}"
    )
    return button


def _settings_button(index: int, on_open) -> QToolButton:
    """Open this step's settings: the selection and the slide in one click.

    The walk's ←/→ move the position and its ↑/↓ move the selection, so reaching
    a step's form from its card is two gestures on the keyboard and the arrow is
    the one that is missing on the pointer. It points the way the pane travels.
    """
    button = QToolButton()
    button.setText("→")
    button.setAutoRaise(True)
    button.setToolTip("Open this step's settings")
    button.setStyleSheet(f"color: rgb({DIM.red()},{DIM.green()},{DIM.blue()}); border: 0;")
    button.clicked.connect(lambda: on_open(index))
    return button


def _pin_button(index: int, pinned: int, on_pin) -> QToolButton:
    button = QToolButton()
    button.setText("◆" if index == pinned else "◇")
    button.setAutoRaise(True)
    button.setToolTip("Already pinned below the canvas" if index == pinned else "Pin below the canvas")
    button.setEnabled(index != pinned)
    color = ACCENT if index == pinned else DIM
    button.setStyleSheet(f"color: rgb({color.red()},{color.green()},{color.blue()}); border: 0;")
    button.clicked.connect(lambda: on_pin(index))
    return button


def _remove_button(index: int, on_remove) -> QToolButton:
    """Drop this step: the chain closes over it rather than breaking at it.

    The source is offered as disabled rather than left off, so the position of
    the buttons is the same on every card — a chain with nothing to read is not
    a shorter chain, which is what the tooltip says instead.
    """
    removable = index != _SOURCE_INDEX
    button = QToolButton()
    button.setText("✕")
    button.setAutoRaise(True)
    button.setEnabled(removable)
    button.setToolTip(
        "Remove this step — what read it reads past it"
        if removable
        else "The chain has to read something"
    )
    button.setStyleSheet(f"color: rgb({DIM.red()},{DIM.green()},{DIM.blue()}); border: 0;")
    button.clicked.connect(lambda: on_remove(index))
    return button


# ---------------------------------------------------------------------------
# The outputs reaching down: the chain's edges, drawn under the cards.
#
# VISION's scene is a picture and not a diagram — an output leaves the bottom of
# the card that made it and arrives at the top of the card that reads it, and
# where the step in between reads neither, the line passes *behind* that card
# rather than around it. Occlusion is the whole of that: the cards paint an
# opaque panel, this widget paints before its children, so a line crossing a
# card is hidden for exactly as long as it is not that card's business. Routing
# a skip around the stack in a gutter would say the opposite — that the output
# left the chain and came back.
#
# The lines are geometry read off the cards at paint time rather than anything
# stored, because the stack is rebuilt on every walk move; an edge layer holding
# its own coordinates would draw the previous selection's stack.

#: The trunk's inset from a card's left edge, and the step out to the next lane.
_EDGE_STUB = 16.0
_EDGE_LANE = 34.0
_ARROW_W = 4.0
_ARROW_H = 6.0

#: Named only where a step has more than one input. Everywhere else the port is
#: the step above and a label would be a label saying "the step above".
PORT_NAMES = {(6, 5): "frames", (6, 4): "background"}


def _port_name(dst: int, src: int) -> str | None:
    """What to write at an arrowhead, or nothing where the port is obvious.

    The output's edges are named from the write list rather than from the table
    above, because what arrives there is a product and not a position: two of
    them can come off one step, and which they are is the thing the user ticked.
    """
    if dst == _OUTPUT_INDEX:
        return ", ".join(p for step, p, on in WRITES if on and step == src) or None
    return PORT_NAMES.get((dst, src))


def _sources_of(dst: int) -> list[int]:
    """What `dst` reads once the removed steps are read past.

    A removed step hands its inputs to whatever read it, so dropping the
    subtraction gives both of its ports to the step below rather than cutting
    the chain in two at the gap.
    """
    live: list[int] = []
    pending = list(INPUTS[dst])
    while pending:
        src = pending.pop(0)
        if src in REMOVED:
            pending = list(INPUTS[src]) + pending
        elif src not in live:
            live.append(src)
    return live


def _edges() -> list[tuple[int, int]]:
    return [(src, dst) for dst in live_nodes() for src in _sources_of(dst)]


def _lanes() -> dict[tuple[int, int], int]:
    """One x per edge, so every line is vertical and none is two lines' worth.

    An edge that changed x while it was hidden would come out the far side as
    something the eye has no reason to join to what went in. Vertical is what
    makes the occlusion read as one line behind a card rather than as two
    stubs, so the offset is spent on lanes rather than on the descent: an edge
    holds its lane the whole way down, and only edges whose spans overlap need
    different ones. Shortest span first hands the trunk to the steps that read
    the one above them, which is most of the chain.
    """
    def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] < b[1] and b[0] < a[1]

    lanes: dict[tuple[int, int], int] = {}
    for edge in sorted(_edges(), key=lambda e: (e[1] - e[0], e[0])):
        taken = {lane for other, lane in lanes.items() if overlaps(edge, other)}
        lane = 0
        while lane in taken:
            lane += 1
        lanes[edge] = lane
    return lanes


def _lane_x(left: float, lane: int) -> float:
    return left + _EDGE_STUB + _EDGE_LANE * lane


#: The fan's tile, the gap between tiles, the drop out of the card into the
#: junction the lines spread from, and the row's height.
_TILE = 24.0
_TILE_GAP = 12.0
_FAN_STUB = 12.0
_FAN_H = 56


class _CropFan(QWidget):
    """The crop step's outputs: one numbered square per region, in the gap.

    A step with one output needs nothing here — the arrow out of its card is the
    whole of it. Crop cuts a region per dish, so the branch is at the card and
    not further down, and this is where it is drawn: the arrows into the squares
    all leave the same card because that card made all of them, and the one
    arrow that continues down leaves the square the user selected. What the rest
    of the stack is drawn for is that region, so the picture and the walk say
    the same thing about which chain is on screen.

    It paints its squares and nothing else. The lines are `_ChainColumn`'s, drawn
    before its children, so they arrive behind these tiles the way an edge
    arrives behind a card.
    """

    def __init__(self, trunk_x: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trunk_x = trunk_x
        self._hover: int | None = None
        self.setFixedHeight(_FAN_H)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        watch_crop(self, self.update)

    def tile_rects(self) -> list[QRectF]:
        """One square per region, the first on the trunk and the rest to its right.

        Left-aligned off the trunk rather than centred in the row because a
        centred row sits wherever the count and the pane's width put it, and
        only a diagonal could reach it from the lane the chain descends in.
        """
        top = (self.height() - _TILE) / 2.0
        left = self._trunk_x - _TILE / 2.0
        return [
            QRectF(left + i * (_TILE + _TILE_GAP), top, _TILE, _TILE)
            for i in range(len(CROPS))
        ]

    def tile_at(self, pos: QPointF) -> int | None:
        for index, tile in enumerate(self.tile_rects()):
            if tile.adjusted(-4, -4, 4, 4).contains(pos):
                return index
        return None

    def mouseMoveEvent(self, event) -> None:
        hover = self.tile_at(event.position())
        if hover != self._hover:
            self._hover = hover
            self.update()

    def leaveEvent(self, event) -> None:
        del event
        self._hover = None
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() is not Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        index = self.tile_at(event.position())
        if index is not None:
            select_crop(index)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setFont(_plot_font(8, bold=True))
        for index, tile in enumerate(self.tile_rects()):
            chosen = index == SELECTED_CROP
            painter.fillRect(tile, PANEL)
            if chosen:
                fill = QColor(ACCENT)
                fill.setAlpha(70)
                painter.fillRect(tile, fill)
            painter.setPen(QPen(ACCENT if chosen else EDGE, 1.6 if chosen else 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(tile)
            if index == self._hover and not chosen:
                painter.setPen(QPen(ACCENT, 1.0))
                painter.drawRect(tile.adjusted(-3, -3, 3, 3))
            painter.setPen(QPen(TEXT if chosen else DIM))
            painter.drawText(tile, Qt.AlignmentFlag.AlignCenter, str(index + 1))
        painter.end()


#: The box's key in `_ChainColumn.cards`, so the two edge painters reach it the
#: way they reach a card. Negative because every real key is a position.
_ADD_SLOT = -2

#: How many offers stand in a row before the next one wraps. The stage with the
#: most of them is spatial prep, and a single row of those is wider than the
#: pane the stack is half of.
_OFFER_COLUMNS = 3


class _AddBox(ChainCard):
    """The step that is not one yet: where it would go, and what could fill it.

    Card-shaped and card-numbered, standing in the chain rather than beside it,
    because the question it is asking is *which position* — and a panel in the
    chrome asking that would have to name the position in words the stack is
    already drawing. Dashed for the same reason its edges are: nothing has been
    written, and the solid chain under it is still what the project holds.

    It does not build its own contents. The offer is the position's
    (`offer_after`), and which of them is lit is the pane's state, so the box
    is rebuilt as the site moves rather than holding a selection of its own —
    the same reason the cards are rebuilt when the walk does.

    A `ChainCard` so the column's edge painters reach it by the one path they
    reach everything: `cards[_ADD_SLOT].geometry()`. It takes no selection —
    the walk cannot stand on a step that does not exist.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(selected=False, parent=parent)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        fill = QColor(ACCENT)
        fill.setAlpha(14)
        painter.fillRect(self.rect(), PANEL)
        painter.fillRect(self.rect(), fill)
        pen = QPen(ACCENT, 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()


def _offer_button(name: str, lit: bool, on_take) -> QPushButton:
    """One offer. The chrome dress, with the lit one wearing the accent."""
    button = _chrome_button(name, f"Add {name} at this position")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    # Its own width, not a third of the box's: the offering is a set of names
    # and a grid of equal bars would be reading as a set of slots.
    button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    if lit:
        button.setStyleSheet(
            button.styleSheet()
            + f"""
            QPushButton {{
                border-color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
                color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
            }}
            """
        )
    button.clicked.connect(lambda: on_take(name))
    return button


def _add_box(site: int, number: int, offer: int, on_take, replaces: bool) -> _AddBox:
    """The box in either of its two positions: a gap, or the card at `site`.

    One widget because one question — what could stand here — and the only
    thing the two modes disagree about is what the caption says and whether
    ↑/↓ have anywhere to go. A box over a card is anchored: walking it into
    the gaps would flip it between replacing and inserting with nothing on
    screen saying which.
    """
    box = _AddBox()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(8, 6, 8, 8)
    layout.setSpacing(4)

    head = QHBoxLayout()
    title = _title_label(f"{number}. {NODES[site][1] if replaces else 'new step'}")
    title.setStyleSheet(f"color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});")
    head.addWidget(title)
    head.addStretch(1)
    if replaces:
        # The id is what the ticks and the edges hang on, so naming it is the
        # picture of what a swap keeps that removing and adding would not.
        note = f"{NODES[site][0]} keeps its edges · esc keeps its tool"
    else:
        # What the splice does, in the two names the picture cannot show until
        # it happens: the box reads one step and is read by whatever read past.
        readers = [NODES[dst][0] for dst in live_nodes() if site in _sources_of(dst)]
        note = f"after {NODES[site][0]}" + (
            f" · {', '.join(readers)} would read it" if readers else ""
        )
    head.addWidget(_dim_label(note))
    layout.addLayout(head)

    names = offer_at(site) if replaces else offer_after(site)
    grid = QGridLayout()
    grid.setContentsMargins(0, 2, 0, 0)
    grid.setSpacing(4)
    for position, name in enumerate(names):
        grid.addWidget(
            _offer_button(name, position == offer % len(names), on_take),
            position // _OFFER_COLUMNS,
            position % _OFFER_COLUMNS,
        )
    grid.setColumnStretch(_OFFER_COLUMNS, 1)
    layout.addLayout(grid)
    keys = "←→ the offer · enter takes it · esc cancels"
    layout.addWidget(_dim_label(keys if replaces else f"↑↓ move the box · {keys}"))
    return box


class _ChainColumn(QWidget):
    """The stack's column, with the chain's edges drawn under its cards.

    It fills its own background: the stack's sheet reaches plain `QWidget` and
    not a subclass — deliberately, so the scrollbars keep the platform's — and
    a column that inherited nothing would leave the edges on grey.
    """

    def __init__(self, current: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current = current
        # Read per stack rather than once at import: a removal changes which
        # spans overlap, and lanes held from before it would cross.
        self._lanes = _lanes()
        self.cards: dict[int, ChainCard] = {}
        self.fan: _CropFan | None = None
        #: The open box's position, or `-1` for no box, and whether it stands
        #: where that step's card is rather than in the gap under it.
        self.box_site = -1
        self.box_replaces = False
        # Which region is selected moves an arrowhead here, so this repaints on
        # the same notification the canvas and the spin boxes do.
        watch_crop(self, self.update)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _STACK_BG)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for src, dst in _edges():
            if src in self.cards and dst in self.cards:
                # The edges the box interrupts are not drawn while it stands
                # there: what is on screen has to be one chain, and a solid
                # line running past the box beside the dashed pair replacing
                # it would be the picture saying both. A box in a gap
                # interrupts what leaves that step; a box over a card
                # interrupts what enters it too.
                if src == self.box_site or (self.box_replaces and dst == self.box_site):
                    continue
                if src == _CROP_INDEX and self.fan is not None:
                    self._paint_fanned_edge(painter, src, dst)
                else:
                    self._paint_edge(painter, src, dst)
        if self.box_site >= 0:
            self._paint_provisional(painter)
        painter.end()

    def _paint_provisional(self, painter: QPainter) -> None:
        """The edges the box would be spliced on, dashed because it is not.

        In a gap: out of that step into the box, and out of the box into
        whatever read past the gap — `_sources_of` inverted, and the picture of
        what taking an offer would write. Over a card: what fed the card feeds
        the box, which is the picture of a swap keeping the edges it stands on.
        """
        for src in self._box_upstream():
            if src == _CROP_INDEX and self.fan is not None:
                self._paint_fanned_edge(painter, src, _ADD_SLOT, dashed=True)
            else:
                self._paint_edge(painter, src, _ADD_SLOT, dashed=True)
        for dst in self._box_downstream():
            self._paint_edge(painter, _ADD_SLOT, dst, dashed=True)

    def _box_upstream(self) -> list[int]:
        return _sources_of(self.box_site) if self.box_replaces else [self.box_site]

    def _box_downstream(self) -> list[int]:
        return [
            dst
            for dst in live_nodes()
            if dst in self.cards and self.box_site in _sources_of(dst)
        ]

    def hold_box(self, site: int, box: _AddBox, replaces: bool) -> None:
        """Give the box a position, so the edge painters reach it as a card.

        Its lanes are the ones the edges it interrupts already had, so the
        picture does not shift sideways when it opens: an edge that moved to
        enter the box would be saying the chain had been rerouted rather than
        interrupted, and the swap case would be saying it about edges the swap
        is specifically keeping.
        """
        self.box_site = site
        self.box_replaces = replaces
        self.cards[_ADD_SLOT] = box
        trunk = min((lane for (src, _), lane in self._lanes.items() if src == site), default=0)
        for src in self._box_upstream():
            self._lanes[(src, _ADD_SLOT)] = self._lanes.get((src, site), trunk)
        for dst in self._box_downstream():
            self._lanes[(_ADD_SLOT, dst)] = self._lanes.get((site, dst), trunk)

    def trunk_x(self, src: int) -> float:
        """Where `src`'s outgoing edge runs, in the x of any row beside its card.

        The cards and the fan are rows of one column layout, so a card's left is
        every row's left and a lane offset carries across unchanged.
        """
        lanes = [lane for (source, _), lane in self._lanes.items() if source == src]
        return _lane_x(0.0, min(lanes, default=0))

    def _pen_for(self, src: int, dst: int, dashed: bool = False) -> tuple[QColor, float]:
        live = dashed or self._current in (src, dst)
        return QColor(ACCENT if live else EDGE), 1.4 if live and not dashed else 1.0

    @staticmethod
    def _stroke(color: QColor, width: float, dashed: bool) -> QPen:
        pen = QPen(color, width)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    def _arrowhead(self, painter: QPainter, end: QPointF, color: QColor) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(end.x() - _ARROW_W, end.y() - _ARROW_H),
                    QPointF(end.x() + _ARROW_W, end.y() - _ARROW_H),
                    QPointF(end.x(), end.y()),
                ]
            )
        )

    def _paint_edge(self, painter: QPainter, src: int, dst: int, dashed: bool = False) -> None:
        above, below = self.cards[src].geometry(), self.cards[dst].geometry()
        x = _lane_x(above.left(), self._lanes[(src, dst)])
        start = QPointF(x, above.bottom() + 1)
        end = QPointF(x, below.top())

        color, width = self._pen_for(src, dst, dashed)
        painter.setPen(self._stroke(color, width, dashed))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(start, end)
        self._arrowhead(painter, end, color)

        name = _port_name(dst, src)
        if name is not None:
            painter.setPen(QPen(DIM))
            painter.setFont(_plot_font(8))
            painter.drawText(
                QPointF(end.x() + _ARROW_W + 3, end.y() - _ARROW_H + 1), name
            )

    def _paint_fanned_edge(
        self, painter: QPainter, src: int, dst: int, dashed: bool = False
    ) -> None:
        """Out of the crop card into every region, and on out of the one selected.

        One run across the gap and a vertical drop off it into each tile: what
        the picture has to say is that these all came from that card, and a
        shared segment says it while every arrowhead stays a descent, which is
        what an arrowhead means everywhere else in the stack. The way out
        mirrors it back onto the trunk, so the lane the rest of the stack is
        drawn in survives the branch.
        """
        above, below = self.cards[src].geometry(), self.cards[dst].geometry()
        fan = self.fan.geometry()
        tiles = [tile.translated(fan.topLeft()) for tile in self.fan.tile_rects()]
        x = _lane_x(above.left(), self._lanes[(src, dst)])
        bus = above.bottom() + 1 + _FAN_STUB

        color, width = self._pen_for(src, dst)
        dim = QColor(color)
        dim.setAlpha(150)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, width))
        painter.drawLine(QPointF(x, above.bottom() + 1), QPointF(x, bus))

        # The run is drawn twice so the reach to the selected region is lit and
        # the rest of it is not, the way the drops off it are.
        chosen_x = tiles[SELECTED_CROP].center().x()
        painter.setPen(QPen(dim, 1.0))
        painter.drawLine(QPointF(x, bus), QPointF(tiles[-1].center().x(), bus))
        painter.setPen(QPen(color, width))
        painter.drawLine(QPointF(x, bus), QPointF(chosen_x, bus))

        for index, tile in enumerate(tiles):
            chosen = index == SELECTED_CROP
            head = QPointF(tile.center().x(), tile.top())
            painter.setPen(QPen(color if chosen else dim, width if chosen else 1.0))
            painter.drawLine(QPointF(head.x(), bus), QPointF(head.x(), head.y() - _ARROW_H))
            self._arrowhead(painter, head, color if chosen else dim)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # Only the way out is provisional when the box is what it reaches: crop
        # cuts those regions whether or not a step is being added under them,
        # so the arrows into the tiles stay the solid ones they are.
        out = tiles[SELECTED_CROP]
        end = QPointF(x, below.top())
        rejoin = end.y() - _FAN_STUB
        if dashed:
            color, width = self._pen_for(src, dst, dashed)
        painter.setPen(self._stroke(color, width, dashed))
        painter.drawLine(
            QPointF(out.center().x(), out.bottom()), QPointF(out.center().x(), rejoin)
        )
        painter.drawLine(QPointF(out.center().x(), rejoin), QPointF(x, rejoin))
        painter.drawLine(QPointF(x, rejoin), QPointF(x, end.y() - _ARROW_H))
        self._arrowhead(painter, end, color)


def _card(
    index: int,
    number: int,
    current: int,
    title: str,
    knobs: list[tuple[str, QWidget]],
    plots: list[QWidget],
    pinned: int,
    on_pin,
    on_remove,
    on_select,
    on_open,
    on_swap,
) -> ChainCard:
    card = ChainCard(selected=index == current, on_select=lambda: on_select(index))
    layout = QVBoxLayout(card)
    layout.setContentsMargins(8, 6, 8, 8)
    layout.setSpacing(4)

    head = QHBoxLayout()
    # The number counts the steps that are there, not the positions the tables
    # are keyed by: what the user is being told is how far down the chain this
    # is, and a removal above it moves that.
    head.addWidget(_title_label(f"{number}. {title}"))
    head.addStretch(1)
    head.addWidget(_settings_button(index, on_open))
    head.addWidget(_swap_button(index, on_swap))
    head.addWidget(_pin_button(index, pinned, on_pin))
    head.addWidget(_remove_button(index, on_remove))
    layout.addLayout(head)

    for name, widget in knobs:
        row = QHBoxLayout()
        row.addWidget(_dim_label(name))
        row.addWidget(widget)
        row.addStretch(1)
        layout.addLayout(row)
    for plot in plots:
        layout.addWidget(plot)
    return card


def _stack_stylesheet() -> str:
    """The stack's own surface: every position that holds cards wears this.

    `.QWidget` — instances of exactly QWidget, not subclasses — is what keeps
    the background off the scrollbars. A plain `QWidget` selector reaches
    QScrollBar too, and any rule on a scrollbar makes Qt draw the whole complex
    control from the stylesheet: groove, arrows, and a handle no longer
    distinguishable from the track. v2 styles nothing there and gets the
    platform's, which is the one this is meant to match.
    """
    return f"""
        .QWidget {{ background: rgb({_STACK_BG.red()},{_STACK_BG.green()},{_STACK_BG.blue()}); }}
        QDoubleSpinBox, QSpinBox, QComboBox {{
            background: rgb({PANEL_HOT.red()},{PANEL_HOT.green()},{PANEL_HOT.blue()});
            color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()});
            border: 1px solid rgb({LINE.red()},{LINE.green()},{LINE.blue()});
            padding: 1px 3px;
        }}
        QScrollArea {{ border: 0; }}
    """


def _title_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()});")
    return label


def _stage_header(name: str, chip: str) -> QHBoxLayout:
    header = QHBoxLayout()
    # Indented past the trunk: a stage boundary is a gap the chain crosses like
    # any other, and the label sits beside that line rather than on it.
    header.setContentsMargins(round(_EDGE_STUB + 10), 0, 0, 0)
    header.addWidget(_dim_label(name.upper()))
    header.addStretch(1)
    header.addWidget(_dim_label(chip))
    return header


def _fixed_card(title: str, note: str) -> ChainCard:
    """The card that stands above a stack and does not scroll with it."""
    card = ChainCard(selected=False)
    row = QHBoxLayout(card)
    row.setContentsMargins(8, 6, 8, 6)
    row.addWidget(_title_label(title))
    row.addStretch(1)
    row.addWidget(_dim_label(note))
    return card


def _stack_scroll(column: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidget(column)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    return scroll


#: Left above and below a card brought into view, so what comes into view with
#: it is the gap the edges are drawn in rather than the neighbour's border
#: exactly. A revealed card that ended flush with the viewport would read as
#: the end of the stack.
_REVEAL_MARGIN = 20


class _StackPane(QWidget):
    """A position whose body is a scrolling stack of cards, one of them current.

    Both stacks are rebuilt whole on every move — the selection is drawn into
    the cards rather than pushed onto them — so the scroll offset is state the
    pane does not survive, and a pane that says nothing about where it was
    leaves the walk at the top of the chain after every keystroke. These two
    handles are what the window carries across a rebuild and what it aims at
    when a position is entered; a pane without a current card (the step form)
    is not one of these and is replaced without either.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scroll: QScrollArea | None = None
        self.current_card: QWidget | None = None

    def offset(self) -> int:
        return 0 if self.scroll is None else self.scroll.verticalScrollBar().value()

    def scroll_to(self, value: int) -> None:
        """Where the pane this one replaces was. Clamped by the bar itself,
        which is what makes a rebuild that shortened the stack land legally."""
        if self.scroll is not None:
            self.scroll.verticalScrollBar().setValue(value)

    def reveal_current(self) -> None:
        """Bring the selected card into view, moving as little as possible.

        Not `ensureWidgetVisible`: a card taller than the viewport is centred by
        that, and a card is read from its head — the number, the title and the
        buttons are all in the first line, and the accent edge only says which
        card is current if the card is recognisable. So a card that cannot fit
        is aligned to its top, and one that fits is scrolled to whichever edge
        it is past. A card already in view moves nothing, which is what keeps a
        click on a visible card from scrolling the stack under the pointer.
        """
        if self.scroll is None or self.current_card is None:
            return
        bar = self.scroll.verticalScrollBar()
        top = self.current_card.mapTo(self.scroll.widget(), QPoint(0, 0)).y()
        height = self.current_card.height()
        view = self.scroll.viewport().height()
        if height + 2 * _REVEAL_MARGIN >= view or top - _REVEAL_MARGIN < bar.value():
            bar.setValue(top - _REVEAL_MARGIN)
        elif top + height + _REVEAL_MARGIN > bar.value() + view:
            bar.setValue(top + height + _REVEAL_MARGIN - view)


def build_pipeline_pane(
    current: int,
    pinned: int,
    project: int,
    on_pin,
    on_remove,
    on_select,
    on_open,
    on_source_change,
    adding: int = -1,
    offer: int = 0,
    on_add: object = None,
    on_take: object = None,
    on_swap: object = None,
    replaces: bool = False,
) -> QWidget:
    pane = _StackPane()
    pane.setStyleSheet(_stack_stylesheet())

    # What stands above the stack is what the stack belongs to, not a step in
    # it: the project, as the library card is above the project list.
    name, holds, _opened = PROJECTS[project]
    project_card = _fixed_card(f"project — {name}", holds)
    # ADD STEP where NEW PROJECT is, and for the same reason: what mints into a
    # container sits on the container's own card, not at the foot of the list
    # it mints into. A gap is not a widget with a button on it, so the only
    # place that is always there to press is here.
    add = _chrome_button("ADD STEP", "Add a step to this chain — A")
    if on_add is not None:
        add.clicked.connect(on_add)
    project_card.layout().addWidget(add)

    column = _ChainColumn(current)
    stack = QVBoxLayout(column)
    stack.setContentsMargins(6, 6, 6, 6)
    # The gap between cards is the only place an edge between neighbours shows,
    # so it is sized for the arrowhead and the port name under it rather than
    # for the rhythm of the cards.
    stack.setSpacing(18)

    # The pinned step's plots are drawn once, below the canvas — its card keeps
    # the knobs and says where the surface went.
    order = live_nodes()
    # The box counts as a step for numbering: it is standing in the chain, and
    # the cards below it would move down by one if it were taken, so a number
    # that skipped it would be telling the user the position is free. A box
    # over a card takes that card's own number — nothing below it moves,
    # because a swap adds no step.
    below_box = order.index(adding) + 1 if adding >= 0 else len(order)
    shift = 0 if replaces else 1
    cards: dict[int, ChainCard] = {
        index: _card(
            index,
            number + (shift if number > below_box else 0),
            current,
            NODES[index][1],
            _knobs_for(index, on_source_change),
            [_dim_label("surface pinned below the canvas")]
            if index == pinned
            else _plots_for(index),
            pinned,
            on_pin,
            on_remove,
            on_select,
            on_open,
            on_swap,
        )
        for number, index in enumerate(order, start=1)
        # The card the box stands in place of is not built: a widget nothing
        # lays out is parentless for as long as the pane lives, and the edges
        # that would have asked for its geometry are the ones the box took.
        if not (replaces and index == adding)
    }
    column.cards = cards
    # A stage emptied by removals takes its header with it: the chip names a
    # signature nothing in the chain currently stands at.
    for stage, chip, members in STAGES:
        shown = [index for index in members if index not in REMOVED]
        if not shown:
            continue
        stack.addLayout(_stage_header(stage, chip))
        for index in shown:
            # A card the box is standing in place of gives up its slot, and its
            # fan with it: those regions are a param of the tool under offer,
            # so drawing them beside the offer would be drawing outputs of a
            # step the user is in the middle of replacing.
            swapping = replaces and index == adding
            if not swapping:
                stack.addWidget(cards[index])
                # The fan needs a gap to stand in, and it is the gap between
                # the crop card and whatever reads it — a row that stood
                # anywhere else would be a legend rather than the branch.
                if index == _CROP_INDEX and any(
                    _CROP_INDEX in _sources_of(dst) for dst in live_nodes()
                ):
                    column.fan = _CropFan(column.trunk_x(_CROP_INDEX))
                    stack.addWidget(column.fan)
            # In a gap: below the fan when there is one, since the box stands
            # in the gap this step's output crosses and the fan is the first
            # thing in it. Over a card: exactly where the card was.
            if index == adding:
                box = _add_box(index, below_box + shift, offer, on_take, replaces)
                stack.addWidget(box)
                column.hold_box(index, box, replaces)
    stack.addStretch(1)

    layout = QVBoxLayout(pane)
    layout.setContentsMargins(6, 6, 6, 0)
    layout.setSpacing(6)
    layout.addWidget(project_card)
    pane.scroll = _stack_scroll(column)
    # The box when there is one, and the current card otherwise: what the walk
    # is standing on is the thing that has to be on screen, and while the box
    # is open that is the box — the card it stands over is not even built.
    pane.current_card = cards.get(_ADD_SLOT) if adding >= 0 else cards.get(current)
    layout.addWidget(pane.scroll)
    return pane


# ---------------------------------------------------------------------------
# The project position: the same stack, one card per project.
#
# A project is chosen the way a step is — the card is the target and the accent
# edge is what "current" looks like — so the two positions read as one surface
# with different contents rather than two widgets that happen to slide past each
# other. The list widget this replaces wore the platform's palette, which made
# the first thing the user sees the one thing that doesn't look like SIEVE.


def _chrome_button(text: str, tip: str) -> QPushButton:
    """The timeline button's dress (HANDLES, ▶), carried inline: these live in
    panes whose stylesheet has no QPushButton rule, and the affordance should
    not differ by pane."""
    button = QPushButton(text)
    button.setToolTip(tip)
    button.setStyleSheet(
        f"""
        QPushButton {{
            background: rgb({PANEL_HOT.red()},{PANEL_HOT.green()},{PANEL_HOT.blue()});
            color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()});
            border: 1px solid rgb({LINE.red()},{LINE.green()},{LINE.blue()});
            padding: 2px 4px;
        }}
        QPushButton:hover {{
            border-color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
        }}
        """
    )
    return button


def _reveal_project(name: str) -> None:
    """The project's folder in the system's file manager — the sample path here."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(f"{LIBRARY_ROOT}/{name}"))


def _open_project_button(index: int, on_open) -> QToolButton:
    """The double click, offered to the pointer: select this project and slide.

    The same arrow as a step card's, for the same reason — opening a project is
    ↑/↓ then → on the keyboard and nothing at all on the mouse but a gesture the
    surface never says is there.
    """
    button = QToolButton()
    button.setText("→")
    button.setAutoRaise(True)
    button.setToolTip("Open this project's chain")
    button.setStyleSheet(f"color: rgb({DIM.red()},{DIM.green()},{DIM.blue()}); border: 0;")
    button.clicked.connect(lambda: on_open(index))
    return button


def _close_project_button(index: int, on_close) -> QToolButton:
    """Drop this project from the library. The folder on disk is not touched.

    The last one is offered disabled rather than left off, the way the source
    step is: every card carries the same two buttons in the same place. What
    stops it is that every pane past this one is drawn about a project, so a
    library the walk stands in front of has one.
    """
    closable = len(PROJECTS) > 1
    button = QToolButton()
    button.setText("✕")
    button.setAutoRaise(True)
    button.setEnabled(closable)
    button.setToolTip(
        "Remove from the library — the folder on disk stays"
        if closable
        else "The walk has to stand on a project"
    )
    button.setStyleSheet(f"color: rgb({DIM.red()},{DIM.green()},{DIM.blue()}); border: 0;")
    button.clicked.connect(lambda: on_close(index))
    return button


def _project_card(index: int, current: int, on_select, on_open, on_close) -> ChainCard:
    name, holds, opened = PROJECTS[index]
    card = ChainCard(
        selected=index == current,
        on_select=lambda: on_select(index),
        on_open=lambda: on_open(index),
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(8, 6, 8, 8)
    layout.setSpacing(4)

    head = QHBoxLayout()
    head.addWidget(_title_label(name))
    head.addStretch(1)
    head.addWidget(_open_project_button(index, on_open))
    head.addWidget(_close_project_button(index, on_close))
    layout.addLayout(head)

    layout.addWidget(_dim_label(holds))

    foot = QHBoxLayout()
    # Last opened sits under what the project holds rather than beside the name:
    # it is the one line on the card the user reads and never acts on, and the
    # head is now where the acting is.
    foot.addWidget(_dim_label(opened))
    foot.addStretch(1)
    # On the selected card alone: it acts on the selection, and the pane is
    # rebuilt when that moves, so the button travels with the highlight.
    if index == current:
        reveal = _chrome_button("OPEN LOCATION", "Open this project's folder on disk")
        reveal.clicked.connect(lambda: _reveal_project(name))
        foot.addWidget(reveal)
    layout.addLayout(foot)
    return card


def build_project_pane(current: int, on_select, on_open, on_new, on_close) -> QWidget:
    pane = _StackPane()
    pane.setStyleSheet(_stack_stylesheet())

    # The button is on the library card, not at the foot of the list: a new
    # project is added to the library, the way another region is added on the
    # crop card and not in the fan that shows them.
    library = _fixed_card(LIBRARY, f"{len(PROJECTS)} projects on disk")
    new = _chrome_button("NEW PROJECT", "New project — empty until sources are added")
    new.clicked.connect(on_new)
    library.layout().addWidget(new)

    column = QWidget()
    stack = QVBoxLayout(column)
    stack.setContentsMargins(6, 6, 6, 6)
    stack.setSpacing(6)
    stack.addLayout(_stage_header("projects", "project -> source"))
    cards = [
        _project_card(index, current, on_select, on_open, on_close)
        for index in range(len(PROJECTS))
    ]
    for card in cards:
        stack.addWidget(card)
    stack.addStretch(1)

    layout = QVBoxLayout(pane)
    layout.setContentsMargins(6, 6, 6, 0)
    layout.setSpacing(6)
    layout.addWidget(library)
    pane.scroll = _stack_scroll(column)
    pane.current_card = cards[current] if 0 <= current < len(cards) else None
    layout.addWidget(pane.scroll)
    return pane


class PinnedStep(QWidget):
    """The one step held under the canvas: its knobs and its plots, full width.

    Detection is the default, which is what puts the count plot under the
    footage the way v2's fixed layout did; any other step can take the slot.
    """

    def __init__(
        self, index: int, on_source_change=lambda: None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(_stack_stylesheet())
        _node_id, tool = NODES[index]

        head = QHBoxLayout()
        head.addWidget(_dim_label("PINNED"))
        head.addWidget(_title_label(f"{index + 1}. {tool}"))
        for name, widget in _knobs_for(index, on_source_change):
            head.addSpacing(8)
            head.addWidget(_dim_label(name))
            head.addWidget(widget)
        head.addStretch(1)

        self._column = QWidget()
        inside = QVBoxLayout(self._column)
        inside.setContentsMargins(8, 4, 8, 6)
        inside.setSpacing(4)
        inside.addLayout(head)
        plots = _plots_for(index)
        for plot in plots:
            inside.addWidget(plot)
        if not plots:
            inside.addWidget(_dim_label(NO_SURFACE_NOTE.get(index, _NO_SURFACE_DEFAULT)))
        inside.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_stack_scroll(self._column))

    def natural_height(self) -> int:
        """What the slot has to be for this step's surfaces to be whole.

        The stretch at the foot of the column is not counted in a size hint, so
        this is the knob row plus the plots and nothing else — a step with no
        surface asks for a strip, and the scalogram pair asks for the room two
        plots need. The scroll area stays for the case where the splitter
        cannot give it.
        """
        return self._column.sizeHint().height()


def _spin(value: float, decimals: int = 2, step: float = 0.01) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    return box


def _int_spin(value: int) -> QSpinBox:
    box = QSpinBox()
    box.setMaximum(100_000)
    box.setValue(value)
    return box


def _choice(options: list[str]) -> QComboBox:
    box = QComboBox()
    box.addItems(options)
    return box


def _restate(text: str) -> QLabel:
    """A value the form only reports: the plot below owns the gesture."""
    return _dim_label(text)


def _write_list(on_writes_change) -> QWidget:
    """The output step's list param: one row per product the chain can emit.

    A tick is an edge, so the callback is the stack's, not this widget's — the
    picture the user is looking at while they tick is the one that has to move.
    """
    column = QWidget()
    layout = QVBoxLayout(column)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    for row, (step, product, checked) in enumerate(WRITES):
        box = QCheckBox(f"{NODES[step][0]} — {product}")
        box.setChecked(checked)
        box.toggled.connect(
            lambda on, row=row: (set_written(row, on), on_writes_change())
        )
        layout.addWidget(box)
    return column


def _run_row() -> QWidget:
    """Run, where what it will write is: the button is the output step's."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 6, 0, 0)
    run = QPushButton("Run")
    run.setCursor(Qt.CursorShape.PointingHandCursor)
    layout.addWidget(run)
    layout.addStretch(1)
    return row


def build_step_form(node_id: str, on_source_change=lambda: None, on_writes_change=lambda: None) -> QWidget:
    """The generated form, mocked: one row per param, widget per kind."""
    form = QWidget()
    rows = QFormLayout(form)
    rows.setContentsMargins(4, 4, 4, 4)
    if node_id == "source-1":
        rows.addRow("video", _source_chooser(on_source_change))
        rows.addRow(
            "asset",
            _restate(f"{SOURCE_FRAMES:,} frames @ {SOURCE_FPS:g} fps · 512×512"),
        )
    elif node_id == "crop-1":
        rows.addRow("origin", _crop_pair(0, 1))
        rows.addRow("size", _crop_pair(2, 3))
        rows.addRow("region", _restate("or drag the box on the canvas — one value, two editors"))
    elif node_id == "rescale-1":
        rows.addRow("factor", _spin(0.5))
    elif node_id == "normalize-1":
        rows.addRow("mode", _choice(["per-frame", "window"]))
    elif node_id == "background-1":
        rows.addRow("estimator", _choice(["median", "mean", "minimum"]))
        rows.addRow("sample", _int_spin(120))
        rows.addRow("reads", _restate("normalize-1 — the same frames the threshold reads"))
    elif node_id == "threshold-1":
        rows.addRow("channel", _choice(["value", "saturation", "hue"]))
        rows.addRow("cut", _spin(0.42))
        rows.addRow("reads", _restate("normalize-1"))
    elif node_id == "subtract-1":
        rows.addRow("floor", _spin(0.05))
        # The one place a form states a port: everywhere else the reading is
        # the step above, and a row saying so would be a row saying nothing.
        rows.addRow("background", _restate("background-1 — reaching past the threshold"))
        rows.addRow("frames", _restate("threshold-1"))
    elif node_id == "blocks-1":
        rows.addRow("block", _int_spin(16))
        rows.addRow("signal", _choice(["mean |diff|", "flow magnitude"]))
    elif node_id == "morlet-1":
        lo, hi = snap_to_bank(BANDS["morlet-1"])
        rows.addRow("band", _restate(f"{lo:.2f} – {hi:.2f} Hz — dragged on the scalogram"))
    elif node_id == "count-1":
        rows.addRow("D", _int_spin(12))
        rows.addRow(
            "threshold",
            _restate(
                f"≥ {BANDS['count-1'][0]:.0f} of 4096 blocks — dragged on the count plot"
            ),
        )
    elif node_id == "output-1":
        rows.addRow("into", _restate("colony_04_stirred/outputs/"))
        rows.addRow("format", _choice(["csv", "parquet"]))
        rows.addRow("write", _write_list(on_writes_change))
        rows.addRow(_run_row())
    return form


#: A step the user added or swapped in has no written guidance here, and
#: inventing one per tool would be inventing the shelf. The real pane reads the
#: tool's own.
_ADDED_GUIDANCE = (
    "Chosen from what this position offered. Its params generate this form the "
    "way every other step's do — the mockup writes its knobs per position, so a "
    "position the user filled is the one place here whose form is empty rather "
    "than mocked."
)

_EXPANDER_BODY_HEIGHT = 200


class GuidanceExpander(QWidget):
    """expander.py: the arrow, and the capped scrolling body under it."""

    def __init__(self, guidance: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.arrow = QToolButton()
        self.arrow.setCheckable(True)
        self.arrow.setArrowType(Qt.ArrowType.RightArrow)
        self.arrow.toggled.connect(self._show_body)

        text = QLabel(guidance)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        text.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._body = QScrollArea()
        self._body.setWidget(text)
        self._body.setWidgetResizable(True)
        self._body.setMaximumHeight(_EXPANDER_BODY_HEIGHT)
        self._body.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.arrow)
        layout.addWidget(self._body)

    def _show_body(self, expanded: bool) -> None:
        self._body.setVisible(expanded)
        self.arrow.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )


def _form_stylesheet() -> str:
    """The stack's surface, plus the two things only a form puts on it.

    A bare `QLabel` rule is safe here and nowhere else in the control side: this
    position holds text, spin boxes and the expander, and no widget that paints
    itself. The form's row labels are Qt's, not ours — there is no
    constructor to reach them through — so the pane has to name the class.
    An inline stylesheet on a label still wins, which is what keeps
    `_dim_label` dim under this.

    The check box and the button are the output step's, and they are here rather
    than on a pane of their own because that is where the write list went. A
    check box carries its own text, so it needs the colour rule a `QLabel` gets;
    the button is the timeline's, since starting a run should not look like a
    different affordance depending on which side of the window it is on.
    """
    return _stack_stylesheet() + f"""
        QLabel {{ color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()}); }}
        QToolButton {{ border: 0; }}
        QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
        QCheckBox {{ color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()}); }}
        QPushButton {{
            background: rgb({PANEL_HOT.red()},{PANEL_HOT.green()},{PANEL_HOT.blue()});
            color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()});
            border: 1px solid rgb({LINE.red()},{LINE.green()},{LINE.blue()});
            padding: 4px 14px;
        }}
        QPushButton:hover {{
            border-color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
        }}
    """


def _stage_of(index: int) -> tuple[str, str]:
    for stage, chip, members in STAGES:
        if index in members:
            return stage, chip
    return "", ""


def build_step_pane(
    current: int, on_source_change=lambda: None, on_writes_change=lambda: None
) -> QWidget:
    """step_pane.py: caption, form, guidance, in one scrolling column."""
    node_id, tool = NODES[current]
    # A retooled step keeps its id, which is what its ticks and edges hang on —
    # and what would otherwise pull this pane the old tool's sampled rows. The
    # real form is generated from the params of whatever stands here now.
    sampled = "" if current in RETOOLED else node_id

    # What the form belongs to, standing where the library card and the project
    # card stand: the step is to its knobs what the project is to its chain.
    _stage, chip = _stage_of(current)
    step_card = _fixed_card(f"step — {current + 1}. {tool}", chip)

    column = QWidget()
    inside = QVBoxLayout(column)
    inside.setContentsMargins(6, 6, 6, 6)
    inside.addWidget(build_step_form(sampled, on_source_change, on_writes_change))
    inside.addWidget(GuidanceExpander(GUIDANCE.get(sampled, _ADDED_GUIDANCE)))
    inside.addStretch(1)

    scroll = QScrollArea()
    scroll.setWidget(column)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)

    pane = QWidget()
    pane.setStyleSheet(_form_stylesheet())
    layout = QVBoxLayout(pane)
    layout.setContentsMargins(6, 6, 6, 0)
    layout.setSpacing(6)
    layout.addWidget(step_card)
    layout.addWidget(scroll)
    return pane


# ---------------------------------------------------------------------------
# The control side: rail gutter + track, control.py's arrangement.


class Control(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._current_node = len(NODES) - 1
        self._current_project = 0
        self._pinned = PINNED_DEFAULT
        #: Where the box stands, or `-1`; whether it stands over that step's
        #: card rather than in the gap under it; and which offer is lit. Held
        #: here and not on the box: the box is rebuilt as the site moves, and a
        #: widget that owned the state would be rebuilding what it was told.
        self._adding = -1
        self._replaces = False
        self._offer = 0
        self.on_pinned_changed = lambda index: None
        self.on_current_changed = lambda index: None
        self.on_source_changed = lambda: None

        self._rail = self._build_rail()
        self._rail.setVisible(False)

        self._panes = _SlidingPanes(
            [
                self._build_project_pane(),
                self._build_pipeline_pane(),
                build_step_pane(
                    self._current_node, self.source_changed, self.writes_changed
                ),
            ]
        )

        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, self._rail.maximumWidth(), 0)
        self._layout.addWidget(self._rail)
        self._layout.addWidget(self._panes)

    def current_position(self) -> int:
        return self._panes.current_index()

    def current_node(self) -> int:
        return self._current_node

    def pinned_node(self) -> int:
        return self._pinned

    def pin(self, index: int) -> None:
        """One slot: pinning a step is what unpins whatever held it."""
        if index == self._pinned:
            return
        self._pinned = index
        self._rebuild_walk()
        self.on_pinned_changed(index)

    def source_changed(self) -> None:
        """A new video: the canvas now, the panes on the next turn of the loop.

        Deferred because this arrives from a combo box that lives in one of the
        panes being rebuilt, and deleting the sender inside its own signal is
        the crash that comes of it. A document would emit and the rebuild would
        land the same way — after the widget that asked for it has finished.
        """
        self.on_source_changed()
        QTimer.singleShot(0, self._rebuild_walk)

    def writes_changed(self) -> None:
        """A ticked product is an edge: the stack is what has to be redrawn.

        Deferred for the reason the source is — the check box that asked for
        this lives in one of the panes the rebuild replaces.
        """
        QTimer.singleShot(0, self._rebuild_walk)

    def go(self, position: int) -> None:
        self._rail.setVisible(position in (_POS_PIPELINE, _POS_STEP))
        self._panes.set_current(position)
        # Before the slide rather than after it: the pane travels with what it
        # will be showing when it arrives, so the correction is never something
        # the user watches happen to a pane already in front of them.
        self.reveal_current()

    def remove(self, index: int) -> None:
        """Drop a step; the walk and the pin land on the step above it.

        Above rather than on whatever slid into the gap: that neighbour is what
        the removed step read, so it is the nearest surviving thing to where the
        user was standing. The source is never removed, so there is always one.
        """
        if index == _SOURCE_INDEX or index in REMOVED:
            return
        order = live_nodes()
        above = order[order.index(index) - 1]
        REMOVED.add(index)
        unpinned = self._pinned == index
        unselected = self._current_node == index
        if unpinned:
            self._pinned = above
        if unselected:
            self._current_node = above
        self._rebuild_walk()
        if unpinned:
            self.on_pinned_changed(self._pinned)
        if unselected:
            self.on_current_changed(self._current_node)

    def adding(self) -> bool:
        """Whether a box is standing in the chain waiting to be filled."""
        return self._adding >= 0

    def _slots(self) -> list[int]:
        """The gaps a step can be added into: under every step but the last.

        Under the output is not a gap — nothing reads past the foot of the
        chain, so there is no position there to offer anything for. The refusal
        is the surface's, the way the source's un-removability is.
        """
        return live_nodes()[:-1]

    def add_here(self) -> None:
        """Open a box under the walk, or take back the one that is open."""
        if self.adding():
            self.cancel_add()
            return
        slots = self._slots()
        self._adding = self._current_node if self._current_node in slots else slots[-1]
        self._replaces = False
        self._offer = 0
        self._rebuild_walk()

    def swap_here(self, index: int) -> None:
        """A card's ⇄: the same box, standing where that card is.

        The offer opens on the tool already there, so what the box says first
        is what the position currently holds — which is the checked entry the
        menu this replaces used to carry, and the reason esc is a real answer
        rather than the only one.
        """
        if self.adding() and self._adding == index and self._replaces:
            self.cancel_add()
            return
        names = offer_at(index)
        self._adding = index
        self._replaces = True
        self._offer = names.index(NODES[index][1]) if NODES[index][1] in names else 0
        self._rebuild_walk()

    def cancel_add(self) -> None:
        """Esc: the box goes and the document is where it was.

        Nothing was written when it opened — a box is a picker, and the step it
        is standing over or the gap it is standing in is unchanged until an
        offer is taken. That is what makes this free.
        """
        if not self.adding():
            return
        self._adding = -1
        self._replaces = False
        self._rebuild_walk()

    def move_add(self, delta: int) -> None:
        """↑/↓ while a box is open move the box, not the walk.

        A box over a card does not move: it is standing at a position that
        exists, and walking it into the gaps would flip it between replacing
        and inserting with nothing on screen saying which.
        """
        if self._replaces:
            return
        slots = self._slots()
        position = slots.index(self._adding) + delta
        moved = slots[max(0, min(len(slots) - 1, position))]
        if moved == self._adding:
            return
        # The lit offer does not travel: the new position's offering is a
        # different list, and an index carried into it would light whatever
        # happened to be third.
        self._adding, self._offer = moved, 0
        self._rebuild_walk()

    def _offering(self) -> list[str]:
        """What the open box holds — of the card it covers, or of its gap."""
        return offer_at(self._adding) if self._replaces else offer_after(self._adding)

    def move_offer(self, delta: int) -> None:
        """←/→ while a box is open walk its offers, not the panes.

        The same keys in both modes: an anchored box has one fewer axis, not a
        second key map.
        """
        names = self._offering()
        if not names:
            return
        self._offer = (self._offer + delta) % len(names)
        self._rebuild_walk()

    def take_offer(self) -> None:
        names = self._offering()
        if names:
            self.fill_box(self._adding, names[self._offer % len(names)])

    def fill_box(self, site: int, tool: str) -> None:
        """Take an offer: the one mutation the whole gesture writes.

        Which mutation is the only thing the two modes disagree about below the
        surface, and it is the difference the surface cannot show: a swap keeps
        the node it is, so its ticks and its edges survive; an add mints one,
        and the chain reads through it. Doing a swap as a remove and an add
        would look identical here and lose everything the id is holding.
        """
        if self._replaces:
            retool(site, tool)
            index = site
        else:
            index = add_node(site, tool)
        self._adding = -1
        self._replaces = False
        # The walk lands on what was just filled, for the reason removal lands
        # on the step above: what the user did was put something there, and the
        # next thing they will do is set it up.
        self._current_node = index
        self._rebuild_walk()
        self.on_current_changed(index)

    def move_walk(self, delta: int) -> None:
        order = live_nodes()
        position = order.index(self._current_node) + delta
        self.select_node(order[max(0, min(len(order) - 1, position))])

    def move_project(self, delta: int) -> None:
        self.select_project(self._current_project + delta)

    def select_node(self, index: int) -> None:
        if index in REMOVED or index == self._current_node:
            return
        self._current_node = index
        self._rebuild_walk()
        self.on_current_changed(index)

    def open_settings(self, index: int) -> None:
        """A card's arrow: stand on that step, then slide to its form."""
        self.select_node(index)
        self.go(_POS_STEP)

    def open_project(self, index: int) -> None:
        """A project's double click: select it, then slide to its chain."""
        self.select_project(index)
        self.go(_POS_PIPELINE)

    def new_project(self) -> None:
        """The library card's +: mint an empty project and stand on it.

        Standing on it rather than opening it: the chain pane would show a
        chain the project does not have, and the next act — adding sources —
        is a knob on the card the selection just landed on.
        """
        add_project()
        self.select_project(len(PROJECTS) - 1)

    def close_project(self, index: int) -> None:
        """A project's ✕: out of the library, and the selection lands somewhere.

        Rebuilt rather than routed through `select_project`, which returns early
        when the index does not move — closing the card above the selected one
        leaves it selected and every card's text still has to be redrawn.
        """
        if len(PROJECTS) <= 1:
            return
        close_project(index)
        # Closing above the selection moves it up with the cards; closing the
        # selected one leaves the highlight where it stood, on whatever rose
        # into that slot, and only the last card has nothing below to rise.
        if index < self._current_project:
            self._current_project -= 1
        self._current_project = min(self._current_project, len(PROJECTS) - 1)
        self._replace_pane(_POS_PROJECT, self._build_project_pane())
        self._replace_pane(_POS_PIPELINE, self._build_pipeline_pane())

    def _build_project_pane(self) -> QWidget:
        return build_project_pane(
            self._current_project,
            self.select_project,
            self.open_project,
            self.new_project,
            self.close_project,
        )

    def select_project(self, index: int) -> None:
        index = max(0, min(len(PROJECTS) - 1, index))
        if index == self._current_project:
            return
        self._current_project = index
        self._replace_pane(_POS_PROJECT, self._build_project_pane())
        # The pipeline stack is headed by the project it belongs to, so moving
        # the selection moves what that header names.
        self._replace_pane(_POS_PIPELINE, self._build_pipeline_pane())

    def _replace_pane(self, index: int, pane: QWidget) -> None:
        old = self._panes._panes[index]
        pane.setParent(self._panes._track)
        self._panes._panes[index] = pane
        pane.show()
        self._panes._relayout()
        # Where the user had scrolled to, then the least move off it that puts
        # the selection back on screen. Both, and in this order: restoring alone
        # would leave an arrow key moving an accent the user cannot see, and
        # revealing alone would put every rebuild back at the top of the chain
        # — the stack is rebuilt when a knob is turned, not only when the walk
        # moves. Done here rather than deferred because the pane is laid out by
        # the show above, and a correction on the next turn of the loop is one
        # the user would watch happen.
        if isinstance(pane, _StackPane) and isinstance(old, _StackPane):
            pane.scroll_to(old.offset())
            pane.reveal_current()
        old.hide()
        old.setParent(None)
        old.deleteLater()

    def reveal_current(self) -> None:
        """Put the position's selection on screen, wherever the walk left it.

        The stacks keep their own offsets while the walk is away, so a position
        entered fresh can be showing anywhere in a chain — including, at launch,
        the top of one whose selection is the output card at its foot.
        """
        pane = self._panes._panes[self.current_position()]
        if isinstance(pane, _StackPane):
            pane.reveal_current()

    def _rebuild_walk(self) -> None:
        old_rail = self._rail
        self._rail = self._build_rail()
        self._layout.replaceWidget(old_rail, self._rail)
        self._rail.setVisible(old_rail.isVisible())
        old_rail.setParent(None)
        old_rail.deleteLater()

        for index, pane in (
            (_POS_PIPELINE, self._build_pipeline_pane()),
            (
                _POS_STEP,
                build_step_pane(
                    self._current_node, self.source_changed, self.writes_changed
                ),
            ),
        ):
            self._replace_pane(index, pane)

    def _build_pipeline_pane(self) -> QWidget:
        return build_pipeline_pane(
            self._current_node,
            self._pinned,
            self._current_project,
            self.pin,
            self.remove,
            self.select_node,
            self.open_settings,
            self.source_changed,
            self._adding,
            self._offer,
            self.add_here,
            lambda tool: self.fill_box(self._adding, tool),
            self.swap_here,
            self._replaces,
        )

    def _build_rail(self) -> NodeRail:
        order = live_nodes()
        rail = NodeRail(node_count=len(order), current=order.index(self._current_node))
        policy = rail.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        rail.setSizePolicy(policy)
        return rail


# ---------------------------------------------------------------------------
# The timeline: bar.py's strip and control row, painted from the sample.
#
# The strip is the tree's paint and hit test with the player and the bar's
# window replaced by the constants below, so the zones announce themselves and
# the bubble follows the cursor. The strip does write the window: a drag on the
# body carries the whole of it, and the boxes in the control row read back what
# the drag left. Nothing else downstream reads the span, so the band is unmoved.

# 200 s at 30 fps, and a window and a playhead on it. `_PLAYHEAD_AT` is the
# fraction the plots draw their playhead at, so the strip and they agree.
SOURCE_FRAMES = 6000
SOURCE_FPS = 30.0
WINDOW_SPAN = (1320, 3360)
PLAYHEAD_FRAME = round(SOURCE_FRAMES * _PLAYHEAD_AT)

STRIP_HEIGHT = 96
_TRACK = QColor(30, 30, 36)
_WINDOW = QColor(90, 170, 255, 70)
_WINDOW_EDGE = QColor(90, 170, 255)
_WINDOW_HEADER = QColor(90, 170, 255, 110)
_PLAYHEAD = QColor(240, 240, 245)
_BUBBLE = QColor(18, 18, 22, 235)
_BUBBLE_EDGE = QColor(80, 84, 96)
_BUBBLE_TEXT = QColor(232, 233, 238)
_BUBBLE_PAD = (8.0, 3.0)
_HEADER_HEIGHT = 9.0
_TRACK_INSET = 4.0
_EDGE_GRAB = 6.0
_MIN_BAND_PIXELS = 2.0
_MIN_BAND_FRAMES = 1


def format_timecode(seconds: float) -> str:
    """`M:SS.mmm`, or `H:MM:SS.mmm` past an hour."""
    seconds = max(seconds, 0.0)
    hours, remainder = divmod(int(seconds), 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    milliseconds = round((seconds - int(seconds)) * 1000) % 1000
    if hours:
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"
    return f"{minutes}:{whole_seconds:02d}.{milliseconds:03d}"


@dataclass(frozen=True, slots=True)
class Geometry:
    """geometry.py's frame↔column mapping, rebuilt per paint and per move."""

    frame_count: int
    width: float

    @property
    def is_empty(self) -> bool:
        return self.frame_count <= 0 or self.width <= 0.0

    def x_of_frame(self, frame: int) -> float:
        if self.is_empty:
            return 0.0
        return min(max(frame, 0), self.frame_count) / self.frame_count * self.width

    def centre_of_frame(self, frame: int) -> float:
        if self.is_empty:
            return 0.0
        return (min(max(frame, 0), self.frame_count - 1) + 0.5) / self.frame_count * self.width

    def span(self, start: int, end: int) -> tuple[float, float]:
        left = self.x_of_frame(start)
        return left, max(self.x_of_frame(end), left + _MIN_BAND_PIXELS)

    def frame_at(self, x: float) -> int:
        if self.is_empty:
            return 0
        return min(max(int(x / self.width * self.frame_count), 0), self.frame_count - 1)


class MockStrip(QWidget):
    """bar.py's band: the whole asset, the window on it, the playhead, the bubble.

    Two gestures, and the toggle decides which the edges answer to. The body
    always moves the whole window, keeping its length; the edges resize it only
    while HANDLES is pressed, so the common gesture cannot land on a handle by
    six pixels and stretch the window the user meant to slide.
    """

    def __init__(self, on_window_change=lambda span: None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._hover: int | None = None
        self._span = WINDOW_SPAN
        self._handles = False
        self._on_window_change = on_window_change
        # What the press grabbed — "lo", "hi", "move" — with the span and the
        # frame it began at, so every move reads from the press rather than
        # from the last one and a slow drag cannot accumulate the rounding.
        self._grab: str | None = None
        self._grab_from = 0
        self._grab_span = self._span
        self.setFixedHeight(STRIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setMouseTracking(True)

    def set_handles_enabled(self, on: bool) -> None:
        self._handles = on
        if not on and self._grab in ("lo", "hi"):
            self._grab = None
        self.update()

    def geometry_now(self) -> Geometry:
        return Geometry(frame_count=SOURCE_FRAMES, width=float(self.width()))

    def window_rect(self) -> QRectF:
        left, right = self.geometry_now().span(*self._span)
        return QRectF(left, _TRACK_INSET, right - left, self.height() - 2.0 * _TRACK_INSET)

    def header_rect(self) -> QRectF:
        window = self.window_rect()
        return QRectF(window.left(), window.top(), window.width(), _HEADER_HEIGHT)

    def bubble_text(self) -> str:
        if self._hover is None:
            return ""
        return f"{format_timecode(self._hover / SOURCE_FPS)}   frame {self._hover:,}"

    def bubble_rect(self) -> QRectF:
        if self._hover is None:
            return QRectF()
        pad_x, pad_y = _BUBBLE_PAD
        metrics = QFontMetricsF(self.font())
        width = metrics.horizontalAdvance(self.bubble_text()) + 2.0 * pad_x
        height = metrics.height() + 2.0 * pad_y
        centre = self.geometry_now().centre_of_frame(self._hover)
        left = max(min(centre - width / 2.0, self.width() - width), 0.0)
        return QRectF(left, _TRACK_INSET + _HEADER_HEIGHT, width, height)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(self.rect()).adjusted(0.0, _TRACK_INSET, 0.0, -_TRACK_INSET)
        painter.fillRect(track, _TRACK)

        window = self.window_rect()
        painter.fillRect(window, _WINDOW)
        painter.fillRect(self.header_rect(), _WINDOW_HEADER)
        painter.setPen(QPen(_WINDOW_EDGE, 1.0))
        painter.drawRect(window.adjusted(0.5, 0.5, -0.5, -0.5))
        if self._handles:
            painter.setPen(QPen(_WINDOW_EDGE, 3.0))
            for x in (window.left() + 1.0, window.right() - 1.0):
                painter.drawLine(QPointF(x, window.top()), QPointF(x, window.bottom()))

        painter.setPen(QPen(_PLAYHEAD, 1.0))
        x = self.geometry_now().centre_of_frame(PLAYHEAD_FRAME)
        painter.drawLine(QPointF(x, 0.0), QPointF(x, float(self.height())))

        box = self.bubble_rect()
        if not box.isEmpty():
            painter.setPen(QPen(_BUBBLE_EDGE, 1.0))
            painter.setBrush(_BUBBLE)
            painter.drawRoundedRect(box, 3.0, 3.0)
            painter.setPen(_BUBBLE_TEXT)
            painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), self.bubble_text())
        painter.end()

    def grab_at(self, position: QPointF) -> str | None:
        """What a press at `position` takes hold of.

        Edges before containment, as the hit test has it: an edge is inside too.
        With HANDLES up the edges are not there to be found, and a press six
        pixels inside the boundary is a move like any other.
        """
        window = self.window_rect()
        x = position.x()
        if self._handles:
            if abs(x - window.left()) <= _EDGE_GRAB:
                return "lo"
            if abs(x - window.right()) <= _EDGE_GRAB:
                return "hi"
        if window.left() <= x <= window.right():
            return "move"
        return None

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        position = event.position()
        self._grab = self.grab_at(position)
        self._grab_from = self.geometry_now().frame_at(position.x())
        self._grab_span = self._span
        self._follow_cursor(position)

    def mouseMoveEvent(self, event) -> None:
        position = event.position()
        self._hover = self.geometry_now().frame_at(position.x())
        if self._grab is not None:
            self._drag(position)
        self._follow_cursor(position)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        self._grab = None
        self._follow_cursor(event.position())

    def _drag(self, position: QPointF) -> None:
        frame = self.geometry_now().frame_at(position.x())
        start, end = self._grab_span
        if self._grab == "lo":
            span = (min(frame, end - _MIN_BAND_FRAMES), end)
        elif self._grab == "hi":
            span = (start, max(frame, start + _MIN_BAND_FRAMES))
        else:
            length = end - start
            moved = min(max(start + frame - self._grab_from, 0), SOURCE_FRAMES - length)
            span = (moved, moved + length)
        if span != self._span:
            self._span = span
            self._on_window_change(span)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if self._hover is not None:
            self._hover = None
            self.update()

    def _follow_cursor(self, position: QPointF) -> None:
        grab = self._grab if self._grab is not None else self.grab_at(position)
        if grab in ("lo", "hi"):
            shape = Qt.CursorShape.SizeHorCursor
        elif grab == "move":
            shape = (
                Qt.CursorShape.ClosedHandCursor
                if self._grab == "move"
                else Qt.CursorShape.OpenHandCursor
            )
        else:
            shape = Qt.CursorShape.PointingHandCursor
        self.setCursor(shape)


def _window_box(value: float, low: float, high: float) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setDecimals(2)
    box.setSingleStep(1.0)
    box.setSuffix(" s")
    box.setRange(low, high)
    box.setValue(value)
    return box


def build_seam() -> QWidget:
    """A splitter handle's line where there is no splitter.

    The timeline's height is the strip's plus one control row; nothing about it
    is the user's to trade against the panes, so the boundary reads like the
    other section dividers without answering the cursor.
    """
    seam = QWidget()
    seam.setObjectName("seam")
    seam.setFixedHeight(3)
    return seam


def build_timeline() -> QWidget:
    """The control row above the band, hard right, then the band."""
    duration = SOURCE_FRAMES / SOURCE_FPS
    start, end = WINDOW_SPAN

    play = QPushButton("▶")
    play.setFixedWidth(40)
    play.setToolTip("Play / pause (Space)")
    start_box = _window_box(start / SOURCE_FPS, 0.0, duration - 1.0 / SOURCE_FPS)
    start_box.setToolTip("Where the working window starts")
    length_box = _window_box((end - start) / SOURCE_FPS, 1.0 / SOURCE_FPS, duration)
    length_box.setToolTip("How long the working window is")

    timecode = QLabel(
        f"{format_timecode(PLAYHEAD_FRAME / SOURCE_FPS)} / {format_timecode(duration)}   "
        f"frame {PLAYHEAD_FRAME:,} / {SOURCE_FRAMES - 1:,}"
    )
    timecode.setTextFormat(Qt.TextFormat.PlainText)
    timecode.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    handles = QPushButton("HANDLES")
    handles.setCheckable(True)
    handles.setToolTip(
        "Arm the window's edges: pressed, an edge drag resizes;"
        " up, only the whole window moves"
    )

    def show_span(span: tuple[int, int]) -> None:
        for box, seconds in ((start_box, span[0]), (length_box, span[1] - span[0])):
            box.blockSignals(True)
            box.setValue(seconds / SOURCE_FPS)
            box.blockSignals(False)

    strip = MockStrip(on_window_change=show_span)
    handles.toggled.connect(strip.set_handles_enabled)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addStretch(1)
    row.addWidget(play)
    row.addWidget(QLabel("Window"))
    row.addWidget(start_box)
    row.addWidget(QLabel("+"))
    row.addWidget(length_box)
    row.addWidget(handles)
    row.addWidget(timecode)

    timeline = QWidget()
    timeline.setObjectName("timeline")
    column = QVBoxLayout(timeline)
    column.setContentsMargins(8, 2, 8, 4)
    column.setSpacing(2)
    column.addLayout(row)
    column.addWidget(strip)
    return timeline


# ---------------------------------------------------------------------------
# The window: layout.py's compose, hotkeys.py's four verbs.

_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540

# The footage is the thing being tuned against: no pin takes more than this
# share of the viewing column, however many surfaces the step has.
_PIN_MAX_SHARE = 60


def _chrome_stylesheet() -> str:
    """The surface the panes leave uncovered: splitter seams and the timeline.

    Every rule is anchored to the splitter or to `#timeline`, never to a bare
    widget class: a plain `QLabel` or `QWidget` selector set on the window
    reaches down into the stack and the plots, which paint themselves, and the
    two stylesheets would then fight over every card.
    """
    return f"""
        QMainWindow, QSplitter {{
            background: rgb({_STACK_BG.red()},{_STACK_BG.green()},{_STACK_BG.blue()});
        }}
        QSplitter::handle {{
            background: rgb({LINE.red()},{LINE.green()},{LINE.blue()});
        }}
        QSplitter::handle:horizontal {{ width: 3px; }}
        QSplitter::handle:vertical {{ height: 3px; }}
        QSplitter::handle:hover {{
            background: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
        }}
        #seam {{
            background: rgb({LINE.red()},{LINE.green()},{LINE.blue()});
        }}
        #timeline {{
            background: rgb({_STACK_BG.red()},{_STACK_BG.green()},{_STACK_BG.blue()});
        }}
        #timeline QLabel {{
            color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()});
        }}
        #timeline QPushButton {{
            background: rgb({PANEL_HOT.red()},{PANEL_HOT.green()},{PANEL_HOT.blue()});
            color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()});
            border: 1px solid rgb({LINE.red()},{LINE.green()},{LINE.blue()});
            padding: 2px 4px;
        }}
        #timeline QPushButton:hover {{
            border-color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
        }}
        #timeline QPushButton:checked {{
            color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
            border-color: rgb({ACCENT.red()},{ACCENT.green()},{ACCENT.blue()});
        }}
        #timeline QDoubleSpinBox {{
            background: rgb({PANEL_HOT.red()},{PANEL_HOT.green()},{PANEL_HOT.blue()});
            color: rgb({TEXT.red()},{TEXT.green()},{TEXT.blue()});
            border: 1px solid rgb({LINE.red()},{LINE.green()},{LINE.blue()});
            padding: 1px 3px;
        }}
    """


def _darken_title_bar(window: QWidget) -> None:
    """Ask DWM for the dark frame, since Qt does not carry the palette there.

    The title bar is the OS's, not Qt's: without this the window wears the
    system light frame over a dark app whatever the stylesheet says. Attribute
    20 is `DWMWA_USE_IMMERSIVE_DARK_MODE`; on anything that is not a recent
    Windows the call simply fails and the frame stays the platform's.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import byref, c_int, windll

        windll.dwmapi.DwmSetWindowAttribute(
            int(window.winId()), 20, byref(c_int(1)), 4
        )
    except (OSError, AttributeError, ImportError):
        pass


class MockWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE — mockup")
        self.setStyleSheet(_chrome_stylesheet())
        self.control = Control()
        self.control.on_pinned_changed = self._show_pinned
        self.control.on_current_changed = self._compose
        self.control.on_source_changed = self._source_changed

        # The solo the composite's gestures ask for. VISION has the document
        # hold it, and the mockup has no document, so the window does: the pane
        # emits, this applies, and the marker it draws is what was applied —
        # a pane that painted its own gesture would disagree with the density
        # plot for a frame every time.
        self._solo: int | None = None
        self._composite = MockComposite(self.control.current_node())
        self._composite.on_solo = self._apply_solo

        # A slot the splitter owns for good: the pinned step is swapped inside
        # it, and the slot is re-fitted to whatever now holds it, so the count
        # plot and the scalogram pair each get the height they need rather than
        # a third of the window each. A drag is the user's until the next pin.
        self._pin_slot = QWidget()
        self._pin_slot_layout = QVBoxLayout(self._pin_slot)
        self._pin_slot_layout.setContentsMargins(0, 0, 0, 0)
        self._pin_slot_layout.addWidget(
            PinnedStep(self.control.pinned_node(), self.control.source_changed)
        )

        self._viewing = QSplitter(Qt.Orientation.Vertical)
        self._viewing.addWidget(self._composite)
        self._viewing.addWidget(self._pin_slot)
        self._viewing.setStretchFactor(0, 1)
        self._viewing.setStretchFactor(1, 0)
        self._fit_pin(_WINDOW_HEIGHT)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self._viewing)
        split.addWidget(self.control)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        split.setSizes([_WINDOW_WIDTH // 2, _WINDOW_WIDTH // 2])

        stacked = QWidget()
        column = QVBoxLayout(stacked)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(split, 1)
        column.addWidget(build_seam())
        column.addWidget(build_timeline())
        self.setCentralWidget(stacked)

        for key, verb in (
            (Qt.Key.Key_Left, self.go_back),
            (Qt.Key.Key_Right, self.go_forward),
            (Qt.Key.Key_Up, self.go_up),
            (Qt.Key.Key_Down, self.go_down),
            (Qt.Key.Key_P, self.pin_current),
            (Qt.Key.Key_A, self.add_step),
            (Qt.Key.Key_Return, self.take_offer),
            (Qt.Key.Key_Enter, self.take_offer),
            (Qt.Key.Key_Escape, self.control.cancel_add),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setAutoRepeat(False)
            shortcut.activated.connect(verb)

        # Both, in this order, as v2's MainWindow has it: `resize` is what the
        # window restores down *to*, so dropping it would leave the restored
        # size — and with it whether the title bar can be grabbed at all — to
        # whatever Qt picks from the layout's size hint.
        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def _fit_pin(self, total: int | None = None) -> None:
        """Give the slot the height its step asks for, canvas keeps the rest."""
        sizes = self._viewing.sizes()
        height = total if total is not None else sum(sizes)
        pin = self._pin_slot_layout.itemAt(0).widget()
        wanted = min(pin.natural_height(), height * _PIN_MAX_SHARE // 100)
        self._viewing.setSizes([height - wanted, wanted])

    def _apply_solo(self, block: int | None) -> None:
        self._solo = block
        self._composite.set_solo(block)

    def _compose(self, index: int) -> None:
        self._composite.compose(index)

    def _source_changed(self) -> None:
        """A new video redraws whatever the canvas is showing of it.

        The pinned slot is refreshed only when it is the source step holding
        it, and on the next turn of the loop for the reason the panes are: the
        chooser that asked for this may be the one in that slot.
        """
        self._compose(self.control.current_node())
        if self.control.pinned_node() == _SOURCE_INDEX:
            QTimer.singleShot(0, lambda: self._show_pinned(_SOURCE_INDEX))

    def _show_pinned(self, index: int) -> None:
        old = self._pin_slot_layout.takeAt(0).widget()
        self._pin_slot_layout.addWidget(PinnedStep(index, self.control.source_changed))
        old.setParent(None)
        old.deleteLater()
        self._fit_pin()

    def pin_current(self) -> None:
        if self.control.current_position() in (_POS_PIPELINE, _POS_STEP):
            self.control.pin(self.control.current_node())

    def add_step(self) -> None:
        """A: open a box in the chain, or take back the one that is open.

        On the pipeline alone, where the box is a row of the stack. The other
        positions would be growing a chain out of sight — and P is bound on
        both because pinning is a step's property wherever you are standing,
        while a gap only exists in the picture of the gaps.
        """
        if self.control.current_position() == _POS_PIPELINE:
            self.control.add_here()

    def take_offer(self) -> None:
        if self.control.adding():
            self.control.take_offer()

    def go_back(self) -> None:
        if self.control.adding():
            self.control.move_offer(-1)
            return
        self.control.go(max(0, self.control.current_position() - 1))

    def go_forward(self) -> None:
        if self.control.adding():
            self.control.move_offer(+1)
            return
        self.control.go(min(_POS_LAST, self.control.current_position() + 1))

    def _move_selection(self, delta: int) -> None:
        """↑/↓ move whichever selection the position in view owns.

        An open box owns them outright: it is a position in the chain that the
        walk cannot stand on, so while it is up the arrows move it and nothing
        else — which is the same rule as the rest of this, one selection per
        pair of keys, with the box counted as the selection while it exists.
        """
        if self.control.adding():
            self.control.move_add(delta)
            return
        position = self.control.current_position()
        if position in (_POS_PIPELINE, _POS_STEP):
            self.control.move_walk(delta)
        elif position == _POS_PROJECT:
            self.control.move_project(delta)

    def go_up(self) -> None:
        self._move_selection(-1)

    def go_down(self) -> None:
        self._move_selection(+1)


def main() -> None:
    app = QApplication(sys.argv)
    window = MockWindow()
    _darken_title_bar(window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
