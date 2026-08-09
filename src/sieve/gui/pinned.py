"""The one step held under the canvas: which step it is, and what it shows.

VISION puts the detection's trace under the footage the way v2's fixed layout
did, and the mockup generalises that to a slot any step can be pinned into
(`MOCKUP-MAP.md`, row "The pinned step"). What that costs is an answer to two
questions the fixed layout never had to ask, and both are here.

**Which step has a plot is read off `ElementKind`, not off the tool.** A node
whose values are pixels emits a picture, and a picture is the canvas' business;
anything coarser than a pixel is one number per element per frame and is what a
trace is drawn from. That is the whole predicate — a branch on `tool_id` here
would be exactly what `adr/gui-knows-kinds-not-tools.md` forbids, and the
element kind is the declaration that makes the branch unnecessary. Whether a
`BLOCK` node's grid is coarse enough to leave *one* value per frame is a
question about a running graph rather than about a spec, so it is refused where
the series arrives (`graph_panel.py`) and not guessed at here.

Most tools declare a *relation* to the kind arriving rather than a kind, so the
answer is a fold down the chain and not a field: `element_kinds` is that fold,
over `walk.py`'s lenient order and `tool_base.node_element`'s conversion. It is
`Dag._elements` without the refusals — the same traversal, over a document the
window has to draw whether or not it would run, which is `app.resolved_specs`'
reason for not going through `Dag.build` either. The conversion is not
re-implemented; only the walk is.

**A step with no plot says where its surface went instead.** Every stereotype
whose editor is drawn somewhere else has a sentence naming that somewhere
(`kind_editors.py` binds two), and a step with none of them says that its knobs
are the whole of it. The alternative — an empty slot — reads as a surface that
failed to draw rather than as one that was never there, which is the same
honesty the graph's stale mark keeps.

The panel this holds is not its own: `tuning.py` fills one `GraphPanel` for the
window's lifetime, so the slot borrows it and hands it back when the pin moves.
That is why `surface` is passed in rather than built here, and why the mockup's
"fresh instances every call" cannot be copied.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from sieve.core.pipeline_model import Node, Pipeline
from sieve.core.tool_base import ElementKind, ParamStereotype, ToolSpec, node_element
from sieve.gui.chrome import DIM, TEXT, rgb, stack_stylesheet

#: What the slot says for a step whose surface is the viewport.
CANVAS_NOTE = "the boxes on the canvas are this step's surface — drag them there"
#: The same, for a step whose surface is the scrubber.
TIMELINE_NOTE = "the handles on the scrubber are this step's surface — drag them there"
#: And for a step that has none: its parameters are all there is to look at.
NO_SURFACE_NOTE = "this step has no surface — its knobs are the whole of it"

#: What the pinned step's own card carries in place of the surface, so that the
#: stack says where it went rather than drawing it a second time.
PINNED_ELSEWHERE_NOTE = "surface pinned below the canvas"

_ELSEWHERE = {
    ParamStereotype.REGION: CANVAS_NOTE,
    ParamStereotype.SPAN: TIMELINE_NOTE,
}


class EmptySlot(QWidget):
    """What holds the slot before a project is open.

    Not a label saying so: the window shows the project selector at that point
    and the canvas beside it is blank too, so a sentence here would be the one
    thing on screen explaining an emptiness the user has not asked about yet.
    """

    def natural_height(self) -> int:
        return 0


def element_kinds(
    order: Sequence[Node], pipeline: Pipeline, specs: Mapping[str, ToolSpec]
) -> dict[str, ElementKind | None]:
    """What one value of each step's output is a value of, folded from the source.

    `None` where nothing can say — a tool this install does not have, or one
    downstream of it. That is `node_element`'s own answer for an undeclarable
    input and it propagates the same way, so a missing spec costs the chain
    below it its plots and nothing else.

    Schema v1 refuses two edges into one node (`walk.py`), so there is never a
    parent to choose between; `order` is the walk's, which is topological, so a
    step's input is resolved by the time it is reached.
    """
    upstream_of = {edge.downstream: edge.upstream for edge in pipeline.edges}
    resolved: dict[str, ElementKind | None] = {}
    for node in order:
        parent = upstream_of.get(node.node_id)
        # A root reads the source, which is frames of pixels.
        arriving = ElementKind.PIXEL if parent is None else resolved.get(parent)
        spec = specs.get(node.node_id)
        resolved[node.node_id] = None if spec is None else node_element(spec.element, arriving)
    return resolved


def draws_a_trace(kind: ElementKind | None) -> bool:
    """Whether a step emitting `kind` has something the graph panel could draw."""
    return kind is not None and kind is not ElementKind.PIXEL


def surface_note(spec: ToolSpec | None) -> str:
    """The sentence a step with no trace puts in the slot.

    First stereotype in declaration order wins, which matters only for a tool
    declaring two surfaces at once; naming both would be a slot describing
    itself rather than the step.
    """
    stereotypes = () if spec is None else tuple(spec.param_stereotypes.values())
    return next(
        (_ELSEWHERE[kind] for kind in stereotypes if kind in _ELSEWHERE),
        NO_SURFACE_NOTE,
    )


def default_pinned(order: Sequence[Node], kinds: Mapping[str, ElementKind | None]) -> int | None:
    """Which step holds the slot before the user pins anything. `None` if empty.

    The detection, spelt as the last step whose values describe whole frames —
    the furthest downstream thing that has reduced the footage to a number, which
    is what a user opens a project to look at. A chain that reduces nothing that
    far gets its last step regardless: the slot exists either way, and the foot of
    the chain is the step the walk is heading for.
    """
    if not order:
        return None
    frames = [
        position
        for position, node in enumerate(order)
        if kinds.get(node.node_id) is ElementKind.FRAME
    ]
    return frames[-1] if frames else len(order) - 1


def _dim(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"color: {rgb(DIM)};")
    return label


class PinnedStep(QWidget):
    """One step's caption over its surface, at the full width of the canvas.

    In a scroll area for the case the splitter cannot give the slot the height
    `natural_height` asks for — a window dragged short, or a step asking for
    more than the share the footage keeps (`layout.PIN_MAX_SHARE`).
    """

    def __init__(
        self,
        position: int,
        node: Node,
        surface: QWidget | None,
        note: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(stack_stylesheet())
        self._node = node
        self._surface = surface

        head = QHBoxLayout()
        head.addWidget(_dim("PINNED"))
        caption = QLabel(f"{position + 1}. {node.tool_id}")
        caption.setStyleSheet(f"color: {rgb(TEXT)};")
        head.addWidget(caption)
        head.addStretch(1)

        self._column = QWidget()
        inside = QVBoxLayout(self._column)
        inside.setContentsMargins(8, 4, 8, 6)
        inside.setSpacing(4)
        inside.addLayout(head)
        if surface is None:
            inside.addWidget(_dim(note))
        else:
            inside.addWidget(surface)
            surface.show()
        inside.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(self._column)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    @property
    def node(self) -> Node:
        """The document's own value for the step in the slot."""
        return self._node

    @property
    def surface(self) -> QWidget | None:
        """The panel this step's trace is drawn on, or `None` if it has none."""
        return self._surface

    def natural_height(self) -> int:
        """What the slot has to be for this step's surface to be whole.

        The stretch at the foot of the column is not counted in a size hint, so
        this is the caption plus the surface and nothing else: a step with a
        sentence asks for a strip and one with a plot asks for the plot.
        """
        return self._column.sizeHint().height()
