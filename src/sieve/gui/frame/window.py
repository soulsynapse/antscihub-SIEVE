"""The window: a menu bar, three panes, and the boundaries between them.

The panes are named for where they sit, not for what they will hold; the reason
is `panes.py`'s, and the same word doing both jobs is why this file says "the
left pane" and "the left side" and never just "left".

Two of the three boundaries are different in kind and the frame is where that
difference is stated. Left against right is a splitter — how much room the
footage gets against the chain is the user's, and it is the trade they make
most often. The bottom against both is a seam: the strip is a fixed height,
because what it will draw is the whole asset at a size the layout does not get
a say in. The menu bar sits above all three and is a boundary of neither kind —
it acts on the window, not on what any pane holds.

A subpane adds a boundary of the seam's kind one level in, and on the axis its
pane's outer boundary left alone — the top and bottom sides in the left and
right panes, the left and right sides in the bottom one, each side stacking two
strips on that one axis. Which sides those are and how deep they stack is the
pane's own and stated there; the window opens none of them, and the resting
frame is the three panes and the two boundaries between them.

Two of the three panes stand something at rest, and they stand it differently.
The left pane holds one view, the canvas — the footage and what is drawn over
it — put in whole, because there is nothing to choose between there. The right
pane holds a swipe, which is the three screens that pane houses laid side by
side on a track it slides along. A swipe is a view in a pane like any other and
not a fourth pane — what it changes is the right pane's occupant, never how many
panes there are. Which keys walk it is `hotkeys.py`'s; the verbs they call are
here, because the swipe is the window's to hold and the keyboard is not the
frame's to interpret twice.

Neither view names the pane it is in. The canvas is a view (ADR-0001) and would
house on the right or on the swipe unchanged; the left pane holding it is this
file's answer, and moving it is an edit here and nowhere else.

The first of those positions houses the project list, which is the first view to
land. The window is what puts it there and hands it what to show — the view
names no pane and no position, so where it stands is the frame's answer and
changing it is an edit here.

One view stands in neither a pane nor a position. Preferences are about the
application rather than about the project, so they are put on an overlay over
the panes (`overlay.py`) — which takes no room from them, and is why the count
of panes is unchanged by there being a fourth thing the window can show. The
frame's keys are held while it is up: they are the window's and fire wherever
focus is, which is what makes them frame-wide and exactly what must not walk a
track the user cannot currently see.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from sieve.gui.frame.chrome import stylesheet
from sieve.gui.frame.hotkeys import bind_hotkeys, suspend_hotkeys
from sieve.gui.frame.menu import build_menu_bar, preferences_anchor, show_about
from sieve.gui.frame.overlay import Overlay
from sieve.gui.frame.panes import (
    build_bottom,
    build_left,
    build_right,
    build_seam,
)
from sieve.gui.frame.swipe import POSITIONS, build_swipe
from sieve.relaunch import relaunch
from sieve.gui.view.canvas import Canvas
from sieve.gui.view.preferences import Preferences
from sieve.gui.view.project_list import ProjectList

#: What the window restores down *to*. Kept even though it opens maximized:
#: without it the restored size — and with it whether the title bar can be
#: grabbed at all — is whatever Qt picks from the layout's size hint.
_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")
        self.setStyleSheet(stylesheet())

        self.left = build_left()
        self.right = build_right()
        self.bottom = build_bottom()

        # The canvas stands in the left pane's core, for the same reason the
        # swipe stands in the right pane's: `body` is the core's, so the pane
        # can still anchor a strip top or bottom without the canvas being what
        # gets cut. It goes in whole rather than on a track — the left pane
        # shows one thing and the choice of which is not the user's to walk.
        self.canvas = Canvas()
        self.left.body.addWidget(self.canvas)

        # The swipe goes in the core's layout, which is what `body` is, so the
        # right pane can still take a subpane on either side without the track
        # being what gets cut — a strip is anchored to the pane and the swipe
        # is standing in it, and the two never trade room.
        self.swipe = build_swipe("right")
        self.right.body.addWidget(self.swipe)

        # The library stands in the first position, which is where the swipe's
        # order already put it. Housed by adding it to that position's own
        # layout rather than by the swipe building it: a position is a space
        # like a pane is, and a track that knew which view belonged at index 0
        # would be the file where "the project list is the right pane's" had
        # been decided — which ADR-0001 says is nowhere.
        self.projects = ProjectList()
        self.swipe.position(POSITIONS.index("project")).body.addWidget(self.projects)
        # Opening a project is a move inward along the same line ← and → walk,
        # so it is the swipe's step and not a second kind of navigation.
        self.projects.opened.connect(lambda _project: self.swipe_forward())

        # No subpane is opened on the way up. Which sides each pane offers and
        # how many each stacks is still the pane's claim and still checkable by
        # asking it, but a strip standing blank in every slot costs room in all
        # three panes and shows boundaries where the resting frame has none.
        # They are attached where a view asks for one — the resting frame is
        # three panes, not fifteen.

        # Even stretch, and an even split to start: neither view is the
        # window's main one. The chain is tuned by reading a plot against the
        # footage, so a frame that gave either the remainder of a resize would
        # be answering a question the user answers by dragging.
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.addWidget(self.left)
        self.split.addWidget(self.right)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)
        self.split.setChildrenCollapsible(False)
        self.even_split()

        stacked = QWidget()
        column = QVBoxLayout(stacked)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.split, 1)
        column.addWidget(build_seam())
        column.addWidget(self.bottom)
        self.setCentralWidget(stacked)
        #: Held rather than reached for through `menuBar()`, because the frame
        #: asks it where its preferences title was drawn every time it stands
        #: them up.
        self.bar = build_menu_bar(self)
        self.setMenuBar(self.bar)
        #: Held rather than dropped so the bindings are reachable by name, not
        #: only by walking the window's children.
        self.hotkeys = bind_hotkeys(self)

        # Preferences stand over the panes rather than in one, and the overlay
        # covers what the central widget covers — the three panes and the two
        # boundaries between them, and not the bar the user asked from. Built
        # here and hidden: it takes no room, so the resting frame is still three
        # panes, and there is nothing to construct on the way to showing it.
        self.overlay = Overlay(stacked)
        self.preferences = Preferences()
        self.overlay.body.addWidget(self.preferences)
        self.preferences.closed.connect(self.close_preferences)
        self.overlay.dismissed.connect(lambda: suspend_hotkeys(self.hotkeys, False))

        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def even_split(self) -> None:
        """Hand the panes the same width, whatever the window is now.

        Halving the splitter's own width rather than the window's: by the time
        a user asks for this the window has been resized and the two numbers
        have parted, and the sizes are read back against the splitter.
        """
        half = max(self.split.width(), _WINDOW_WIDTH) // 2
        self.split.setSizes([half, half])

    def swipe_back(self) -> None:
        """←: one position out along the right pane's track."""
        self.swipe.step(-1)

    def swipe_forward(self) -> None:
        """→: one position in."""
        self.swipe.step(+1)

    def reload(self) -> None:
        """Ctrl+R: start the application over on the code as it is now.

        The window is closed first so what the user sees go away is the old run
        and not a frame that stopped answering: the process is replaced without
        unwinding, so nothing after the call runs and Qt is never asked to shut
        down. What replacing it means is `relaunch.py`'s.
        """
        self.close()
        relaunch()

    def toggle_full_screen(self) -> None:
        """Full screen and back, without deciding what 'back' is.

        `showNormal` would restore *down*, losing a maximized window's state;
        the frame opens maximized, so leaving full screen has to put back the
        state the window was actually in.
        """
        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowFullScreen)
        else:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)

    def open_preferences(self) -> None:
        """Stand the preferences over the panes, and hold the frame's keys.

        Asking again while they are already up is a re-raise and not a second
        card: the bar's title stays clickable under nothing, and Ctrl+, is the
        same request from the keyboard.

        Dropped from under the bar's own title rather than centred, so what is
        on screen is read as having come from what was clicked — the title
        stays visible above it, and Ctrl+, arrives at the same place, which is
        what keeps the keyboard's route and the pointer's showing one thing.
        """
        suspend_hotkeys(self.hotkeys, True)
        self.overlay.raise_over(preferences_anchor(self.bar))

    def close_preferences(self) -> None:
        """Uncover the panes. The keys come back with the overlay's own signal,
        so the two ways the user closes this and the one the frame does all
        restore them in the same place."""
        self.overlay.dismiss()

    def about(self) -> None:
        show_about(self)
