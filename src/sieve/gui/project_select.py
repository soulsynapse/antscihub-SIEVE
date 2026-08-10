"""The project position: the library card above one card per project.

The same stack as the pipeline position, with projects where the steps go
(`chain_stack.py`, whose `ChainCard` this reuses rather than redraws). What it
replaces was a `QListWidget`, which wore the platform's palette and so made the
first thing a user sees the one surface that does not look like SIEVE — the
argument `chain_stack.py` makes about the pipeline pane, read at the position
that comes before it.

The first cut opens a project and mints an empty one; it does not build one from
a folder of videos (`PLAN.md`, Phase 7), so there is no file dialog here and
nothing asks for a name — `mint` writes a document naming no footage, and both
the name and the footage are knobs on the card the selection lands on.

**What the widget is handed is text, and `listings` is what reads the document
to produce it.** A card says what its project holds, and that is a fact about a
file on disk — so the widget holds no `Project`, for the reason it emits no
`Project`: reading the document is the session layer's, and a widget still
holding one it parsed at build time would be holding a value it is not the owner
of by the time anything asked it for one. `listings` reads, derives three
strings, and drops what it read; a document that will not parse becomes a row
that says so rather than a library that will not draw.

**The selection is not here either.** Which card wears the accent is the
window's, handed down on every rebuild, exactly as the walk's position is
(`app.py`) — so a click and an Up are two ways to move one number rather than
two numbers that have to be kept agreeing.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml
from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import PROJECT_SUFFIX, Project
from sieve.gui.chain_stack import ChainCard, fixed_card, note_label, title_label
from sieve.gui.chrome import chrome_button, stack_stylesheet

#: Beyond this many days the relative phrasing stops being read as a duration
#: and starts being counted, so the card gives the date instead.
_RELATIVE_DAYS = 30


#: The library is a folder, not the directory the process happened to start in.
#: Named here because two callers need the same answer and a second spelling of
#: it would be a second library the day one of them was edited.
LIBRARY_FOLDER = "projects"


def library_root(launched_in: Path) -> Path:
    """The folder a mint lands in, given where the app was launched.

    A function rather than a line inside `main`, so a caller that is not opening
    a `QApplication` can ask the same question — which is the only reason the
    default is reachable from a test at all.

    Created if it is not there. The alternative is a library that cannot be
    minted into until someone makes a folder by hand, and the pane's one gesture
    would fail on a fresh checkout for a reason no message could usefully give.

    Where the launch directory is the repository, this is what keeps a user's
    document out of the source tree: a mint is not a fixture, and a scan of the
    launch directory would otherwise draw the repository as the library.
    """
    folder = launched_in / LIBRARY_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def projects_in(directory: Path) -> tuple[Path, ...]:
    """Every project file directly in `directory`, in a stable order.

    Not recursive: a scan that descended would put the same list in front of a
    user whichever folder they picked, and the folder they picked is the answer
    they gave. Sorted, because the order a filesystem returns entries in is not
    a property anyone chose, and a list that reshuffled between launches would
    make the same keystrokes open different projects.
    """
    return tuple(sorted(directory.glob(f"*{PROJECT_SUFFIX}")))


def library_folder(paths: Sequence[Path]) -> Path | None:
    """The folder the projects came out of, where they came out of one.

    `projects_in` scans a single directory, so they do — but a caller may hand
    the pane any sequence, and one assembled from two folders has no single
    answer to name or to mint into. Read twice for that reason: it is what the
    library card is titled with and what a new project is written to.
    """
    folders = {path.parent for path in paths}
    if len(folders) != 1:
        return None
    return folders.pop()


def mint(directory: Path) -> Path:
    """Write an empty project into `directory` and say where it landed.

    Empty is the whole of it: no sources, no chain (`adr/a-document-may-name-no-
    footage.md`, which exists because this document could not otherwise be
    built). No name is asked for — the name is a knob like any other and a modal
    at mint time would be the one form in the surface that blocks the walk — so
    the file is named after the first `untitled_N` the folder does not already
    hold. Numbered against the folder rather than against a count of cards,
    because a library the user has minted into before already holds the low
    numbers and reusing one would open the earlier project rather than make a
    new one.

    Written immediately rather than held pending in the window: a row that
    existed only in memory would vanish on the next launch, having been counted
    as a project in the meantime.

    Raises:
        OSError: if the file cannot be written.
    """
    taken = {path.name for path in directory.iterdir()} if directory.is_dir() else set()
    number = 1
    while f"untitled_{number}{PROJECT_SUFFIX}" in taken:
        number += 1
    path = directory / f"untitled_{number}{PROJECT_SUFFIX}"
    Project().save(path)
    return path


def reveal(project: Path) -> None:
    """Show the project's folder in whatever the system uses to browse files.

    The folder and not the file, because there is no cross-platform way to ask
    a file manager to open with one entry selected — `QDesktopServices` opens
    a location, and selecting would be a subprocess per platform. The folder is
    also what a project *is* on disk: the document sits beside the footage it
    names and above the child folders holding what a run wrote
    (`core/pipeline_model.PROJECT_SUFFIX`), so the folder is the whole of the
    thing and the file is one entry in it.

    Nothing is reported back. The one failure a caller could act on — the folder
    is gone — is the same news the file manager gives, and the alternative to
    letting it say so is a second check here that could disagree with it.
    """
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(project.parent)))


@dataclass(frozen=True)
class Listing:
    """One card's worth of what a project file says about itself.

    The three lines the mockup's project card carries, already derived: a card
    is built from this and reads nothing.
    """

    path: Path
    name: str
    #: What is in the document — its chain and the footage that chain reads.
    holds: str
    #: When the file was last written.
    when: str


def _holds(path: Path) -> str:
    """The chain and the footage, or that neither could be read.

    A file that cannot be read, one that is not YAML, and one that is YAML but
    not a project are one thing to the person looking at the shelf, so they get
    one word. Caught at all because the alternative is that one bad file in a
    folder takes the whole library down and none of the others draw.
    """
    try:
        project = Project.load(path)
    except (OSError, ValueError, yaml.YAMLError):
        return "unreadable"
    steps = len(project.pipeline.nodes)
    chain = "no chain yet" if steps == 0 else f"{steps} step{'' if steps == 1 else 's'}"
    # The file and not the path it is spelt with: a card is a card wide, and the
    # folder is the same for every project in a library often enough that
    # showing it would spend that width on the part that never differs.
    footage = "no footage yet" if project.source is None else Path(project.source.path).name
    return f"{chain} · {footage}"


def _when(path: Path, now: datetime) -> str:
    """How long ago the file was written, in the words a glance wants.

    Written, not opened — the mockup's card says "opened" and nothing in the
    tree records an open, so this says what the filesystem actually knows.
    Saying "opened" off an mtime would be a claim about the user's history that
    the number cannot support.

    Compared by calendar day in the reader's own zone, which is the unit "today"
    is said in: a file written at 23:50 is yesterday's at 00:10 and not "an hour
    ago", and an elapsed-hours count would say the opposite of what the user
    remembers doing.
    """
    try:
        saved = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).astimezone()
    except OSError:
        return ""
    days = (now.date() - saved.date()).days
    if days <= 0:
        return "saved today"
    if days == 1:
        return "saved yesterday"
    if days <= _RELATIVE_DAYS:
        return f"saved {days} days ago"
    return f"saved {saved.date().isoformat()}"


def listings(paths: Sequence[Path], now: datetime | None = None) -> tuple[Listing, ...]:
    """Read each project and say what a card for it should carry.

    `now` is a parameter because "today" is the whole of what half the answer
    means, and a clock read inside would leave the wording assertable only by a
    test that owned the machine's date. Local time, aware: the comparison is
    against a file's mtime, which is an instant, and the answer is a calendar
    day, which is only a day in some zone.
    """
    at = datetime.now(tz=UTC).astimezone() if now is None else now
    return tuple(
        Listing(
            path=path,
            name=path.name.removesuffix(PROJECT_SUFFIX),
            holds=_holds(path),
            when=_when(path, at),
        )
        for path in paths
    )


def _library_title(folder: Path | None) -> str:
    """What the card above the shelf is called."""
    return "library" if folder is None else f"library — {folder}"


def _project_card(
    index: int,
    listing: Listing,
    current: int,
    on_select: Callable[[int], None],
    on_open: Callable[[int], None],
    on_reveal: Callable[[int], None],
) -> ChainCard:
    """One project's card. Takes its own index because a card knows what it is
    and not where it stands, and binding here is what gives each closure a
    scope of its own."""
    card = ChainCard(
        selected=index == current,
        on_select=lambda: on_select(index),
        on_open=lambda: on_open(index),
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(8, 6, 8, 8)
    layout.setSpacing(4)

    head = QHBoxLayout()
    head.addWidget(title_label(listing.name))
    head.addStretch(1)
    head.addWidget(note_label(listing.when))
    layout.addLayout(head)

    foot = QHBoxLayout()
    foot.addWidget(note_label(listing.holds))
    foot.addStretch(1)
    # On the selected card alone: it acts on the selection, and the pane is
    # rebuilt when that moves, so the button travels with the highlight. A
    # labelled button rather than a glyph beside the note, which was tried in
    # the referent and read as nothing.
    if index == current:
        button = chrome_button("OPEN LOCATION", "Open this project's folder on disk")
        button.clicked.connect(lambda: on_reveal(index))
        foot.addWidget(button)
    layout.addLayout(foot)
    return card


class ProjectSelect(QWidget):
    """The library it is a library of, then the projects in it.

    The library card is outside the scroll for the pipeline pane's reason
    (`chain_stack.PipelinePane`): scrolling a long shelf must not take away the
    answer to which folder is being looked at.

    **The two verbs leave as signals, where the pipeline pane's leave as
    callbacks handed in.** The difference is not taste. This pane is built in
    `MainWindow.__init__` and, for a window nobody navigates, is never replaced
    — so a closure over a bound method of the window is a strong Python
    reference from a child the window destroys back into the window being
    destroyed, and the process aborts at interpreter exit with an access
    violation. Measured, bisected, and left with one open question in
    `findings/2026.08.09-a-pane-closure-back-into-the-window-aborts-at-exit.md`.
    A bound-method slot is held weakly by PySide and dropped with the
    connection, which is the whole of the fix.
    """

    #: The accent moves to this card. Not "a project was chosen": entering is
    #: the other one, and the pane says which gesture happened rather than
    #: deciding what either means.
    selected = Signal(int)
    #: This card was double-clicked — enter it.
    opened = Signal(int)
    #: The selected card's OPEN LOCATION was pressed — show it on disk. A third
    #: signal and not a call to `reveal` from the button, for the reason the
    #: other two are signals: which project an index means is the window's
    #: answer, and a pane that answered it would be holding the selection twice.
    revealed = Signal(int)
    #: The library card's NEW PROJECT was pressed. Carries nothing: minting is
    #: an act on the library, which is the card the button sits on, and the
    #: selection it lands on afterwards is the window's to move.
    minted = Signal()

    def __init__(
        self,
        rows: Sequence[Listing],
        current: int,
        library: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(stack_stylesheet())

        self.library_card = fixed_card(_library_title(library))
        if library is not None:
            # On the library card and not at the foot of the list: a new project
            # is added to the library, the way another region is added on the
            # crop card and not in the fan that shows them. Absent where there is
            # no one folder to write into, which is the only honest alternative
            # to a button that would refuse whenever it was pressed.
            new = chrome_button("NEW PROJECT", "New project — empty until sources are added")
            new.clicked.connect(self.minted.emit)
            self.library_card.layout().addWidget(new)
        self.cards = tuple(
            _project_card(
                index,
                row,
                current,
                self.selected.emit,
                self.opened.emit,
                self.revealed.emit,
            )
            for index, row in enumerate(rows)
        )

        # Plain `QWidget`, so the stack's sheet reaches it: a subclass here would
        # leave the gaps between the cards on the platform's grey.
        column = QWidget()
        stack = QVBoxLayout(column)
        stack.setContentsMargins(6, 6, 6, 6)
        stack.setSpacing(6)
        for card in self.cards:
            stack.addWidget(card)
        stack.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 0)
        layout.setSpacing(6)
        layout.addWidget(self.library_card)
        layout.addWidget(scroll)
