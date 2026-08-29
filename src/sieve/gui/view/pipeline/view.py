"""The chain as a view: the head over it, and the room its steps will stand in.

The chassis and not the chain. What lands here is `primitives/view.py`'s head and
the room under it, which is what the position on the track was missing: a blank
position has nowhere to put the pair of arrows the frame hands its views, so the
only way off it was a key, and a screen whose only way onward is a key reads as a
screen with no way onward at all (`frame/swipe.py` on why the pair exists).

`View` and not `CardStack`, though the mockup draws the chain as a column of step
cards with the edges descending between them (`mockup/paper_cards.py`). A stack
is a claim about what fills the room — that it is cards, in one scrolling column,
at the gap the ground sets — and that claim is worth making the day the steps
arrive and not the day the head does. The swap is a base class and an import here
and nothing anywhere else, because the head is the same head either way.

The title is `Pipeline` for now, on `view/project_list/view.py`'s terms: what a
head says is the view's own claim, and the head this file wants to carry is the
project's name (`primitives/view.py` says so). There is no project document to
read one off, so the view says the one thing it can stand behind, and the name
lands when there is a name.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Empty, View
from sieve.gui.primitives.view import PAD_X


class Pipeline(View):
    """The chain in the open project, and nothing standing in it yet.

    What it holds is the sentence saying so and the room around it. The sentence
    is `primitives/empty.py`'s rather than a dim label of this file's, for that
    file's reason — an empty chain and a chain that failed to load look identical,
    and naming the move that ends it is what tells them apart.

    The move is named and not offered. Adding a step is a verb on the whole pane
    and the head is where a pane's verbs go; a button inside the box would be the
    action in a second place, and the copy that disappears the moment it works.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Pipeline", parent)

        # Centred in the room by a stretch either side, which is what `Empty`
        # asks of a caller that wants it centred in a pane. The margin is the
        # head's own inset, read off it, so the box stands on the title's x.
        room = self.body()
        room.setContentsMargins(PAD_X, PAD_X, PAD_X, PAD_X)
        room.addStretch(1)
        room.addWidget(
            Empty("No steps yet", "Add the first one to start the chain.")
        )
        room.addStretch(1)
