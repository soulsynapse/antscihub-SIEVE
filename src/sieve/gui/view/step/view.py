"""The walked step as a view: the head over it, and the room its knobs will fill.

The chassis and not the form, on `view/pipeline/view.py`'s terms and for its
reason: the position on the track had no head, so it had nowhere to stand the
pair of arrows the frame hands its views, and the only way off it was a key.

`View` and not `SectionCard` or `CardStack`. What a step's surface is — knobs in
a row under a header, a figure below them, the cost at the foot
(`mockup/paper_cards.py`) — is settled for the card in the chain, and whether the
screen that opens onto one step is that card at full pane width or a form of its
own is not settled anywhere. The head is the same head under either answer, which
is what makes it the part that can land first.

The title is `Step` for now and not the tool's name, on
`view/project_list/view.py`'s terms: there is no chain to be standing in, so
there is no step to be named after, and a head that read `crop` would be this
file inventing one.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from sieve.gui.primitives import Empty, View
from sieve.gui.primitives.view import PAD_X


class Step(View):
    """The step the user is standing on, with none to stand on yet.

    The sentence is `primitives/empty.py`'s and names the move that ends it,
    which here is a move made on the position before this one: what fills this
    room is chosen in the pipeline, not here. That is the honest thing to say and
    the reason there is no verb on the box — the action is one screen back along
    the same line ← and → walk.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Step", parent)

        # A stretch either side, and the head's own inset for the margin — see
        # `view/pipeline/view.py`, the same room saying the same kind of thing;
        # the two heads are read down the same x.
        room = self.body()
        room.setContentsMargins(PAD_X, PAD_X, PAD_X, PAD_X)
        room.addStretch(1)
        room.addWidget(
            Empty("No step open", "Open one from the pipeline to tune it here.")
        )
        room.addStretch(1)
