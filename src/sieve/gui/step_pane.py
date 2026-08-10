"""The step position: one node's caption, its parameters, and its guidance.

07.5 through 07.10 each landed a widget for this position and left where it sits
to whoever assembled the whole pane. That is here, and the arrangement is two
decisions rather than a layout.

**Order is what the user does with it.** The caption says which step this is,
the generated form is what they came to change, and the arrow is a question they
ask occasionally about a control they can already see. Reading order is the
order of use, so the guidance goes last — above the form it would push the
controls down the pane for a thing most sessions never open.

**Opening the guidance scrolls; it does not push the controls out.** The pane
scrolls as a whole, so the form stays exactly where it was and the prose appears
under it. That is why the expander caps its body (`expander._BODY_HEIGHT`) *and*
sits in a scroll area: the cap keeps a wordy tool from setting the pane's height
for every other one, and the scroll keeps a tall form and an open expander from
being a choice between them.

The kind editors are not here and cannot be. A region is drawn on the viewport
and a span on the band (`kind_editors.py`), so what this position holds for those
parameters is the form's read-only restatement of the value, with the gesture
happening on the surface the value is about.

**A band's surface is the exception, and it is here because there is nowhere
else it could be.** The viewport and the scrubber are the window's own furniture
and were already on screen; a display surface exists only while a step that
declares one is being looked at, so it belongs to the step. Above the form,
against the pane's own reading-order rule: the picture is what the band's
handles are dragged on, and a control the user has to scroll past its own plot to
reach is two gestures where the pane promises one. Nothing here fills them — the
tuning loop does (`tuning.py`), which is the same split the graph under the
canvas is on.
"""

from __future__ import annotations

from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from sieve.core.pipeline_model import Node
from sieve.core.tool_base import ToolSpec
from sieve.gui.expander import GuidanceExpander
from sieve.gui.node_list import NodeBox
from sieve.gui.param_form import ParamForm
from sieve.gui.surface_panel import SurfacePanel
from sieve.session.session import Session


class StepPane(QWidget):
    """Everything the walk's current node shows, in one scrolling column.

    The spec is handed in rather than looked up, for `param_form.py`'s reason:
    nothing under `gui/` learns which tool it is drawing.
    """

    def __init__(
        self,
        position: int,
        node: Node,
        session: Session,
        spec: ToolSpec,
        parent: QWidget | None = None,
        *,
        replicate_id: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._box = NodeBox(position, node)
        self.form = ParamForm(session, node.node_id, spec, replicate_id=replicate_id)
        self.expander = GuidanceExpander(spec)
        #: One panel per surface the tool declares, in the spec's own order so
        #: two steps of the same tool stack their pictures the same way. Empty
        #: for every tool with no band, which is every tool but `detect`.
        self.surfaces = {
            surface: SurfacePanel(surface)
            for surface in dict.fromkeys(spec.param_surfaces.values())
        }

        column = QWidget()
        inside = QVBoxLayout(column)
        inside.setContentsMargins(0, 0, 0, 0)
        inside.addWidget(self._box)
        for panel in self.surfaces.values():
            inside.addWidget(panel)
        inside.addWidget(self.form)
        inside.addWidget(self.expander)
        inside.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setWidget(column)
        # Without this the column keeps its own size hint inside the viewport
        # and the form scrolls sideways instead of filling the pane's width.
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)

    @property
    def node(self) -> Node:
        """The document's own value for the node on screen."""
        return self._box.node
