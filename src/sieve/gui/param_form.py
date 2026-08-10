"""One control per parameter, chosen by how the parameter is populated.

The reader `param_stereotypes` was declared for. A tool arrives on the shelf
with a stereotype per field and gets its whole settings surface from the map
below — no GUI code of its own, and no `if tool_id ==` anywhere in this module
(`adr/gui-knows-kinds-not-tools.md`). What a tool *can* add is a kind, and the
map is what makes that a deliberate cost: an unmapped kind is refused by name
here, the same refusal `ToolSpec` makes at registration, now at the surface that
would otherwise draw a panel with a parameter silently missing from it.

Bounds come from the params model's own JSON Schema through
`core.tool_base.resolved_schema`, which is also what `sieve inspect` prints. A
second description of the parameter space in this module would be free to drift
from the model that actually validates the value.

Edits flow one way. A widget emits `SetParam` and nothing here reads the
document back: a rebuilt form is how new values arrive, which is the same rule
the session layer's whole-value history runs on — a form that patched itself in
place would be a second writer of the value it is showing.

And they flow on intent. Every value a control emits is a re-plan, a cache key
and a window render on the GUI thread, so *when* a widget counts as edited is a
product question rather than a Qt detail: Qt's obvious signals commit a value
scrolled past, arrowed past, and half typed. `_CommittedSpin` and
`_ChoiceCombo` are where the three are answered, and the answers are the
generator's rather than a widget's written beside it because they are rules
about what a control is.

The four composite kinds have no editor yet, only a restatement of the value
they hold: `region` wants the canvas, `span` the timeline, and `band` an axis
the spec does not yet name (`todo/composite-kinds-get-their-editors.md`). They
are in the map rather than absent from it because a kind with no entry is a
refusal, and these are declared by tools on the shelf today.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QToolButton,
    QWidget,
)

from sieve.core.tool_base import ParamStereotype, ToolSpec, resolved_schema
from sieve.session.intents import SetParam, issue
from sieve.session.session import Session

#: What a numeric field spans when it declares no bound of its own. v2's
#: number, and its reason: a spin box has to have a range, and a value this far
#: outside anything a tool means is one the model will refuse on the way in
#: rather than one this module has to talk a user out of.
_UNBOUNDED = 1_000_000

#: Digits a real-valued control shows, and therefore the smallest value it can
#: hold. v2's seed nudged an exclusive bound by 1e-6 while displaying three
#: decimals, so `gt=0` became a minimum of 0.000 and the control's own floor was
#: a value the model refuses — every `fps` on the shelf. The step out of an
#: exclusive bound is the control's resolution or it is not a step at all.
_DECIMALS = 3
_NUDGE = 10.0**-_DECIMALS

_Edit = Callable[[Any], None]
_Builder = Callable[[Mapping[str, Any], Any, Mapping[str, str], _Edit], QWidget]

#: The keys `QComboBox` walks a *closed* list with. Each steps the value and
#: emits `activated` on the way past; each opens the popup here instead.
_NAVIGATION_KEYS = frozenset(
    {
        Qt.Key.Key_Up,
        Qt.Key.Key_Down,
        Qt.Key.Key_PageUp,
        Qt.Key.Key_PageDown,
        Qt.Key.Key_Home,
        Qt.Key.Key_End,
    }
)


def _keep_focus_off_the_wheel(control: QWidget) -> None:
    """Stop a wheel from *granting* the focus that licenses it.

    Both spin boxes and combos default to `Qt.WheelFocus`, and Qt gives focus
    by policy inside `QApplication.notify`, before the event reaches any
    handler below. Left alone, the first notch over an unfocused control would
    focus it and then arrive already focused, and the rules here would be true
    and useless.

    Only the exact default is rewritten: `WheelFocus` on a knob is Qt's choice
    rather than an author's, which is what makes it a default to replace rather
    than a preference to honour.
    """
    if control.focusPolicy() is Qt.FocusPolicy.WheelFocus:
        control.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class _CommittedSpin:
    """A number that reaches the document on intent, not on the way past.

    Two of the three pass-through cases the generated controls have, both
    re-derived from v2 (`gui/wheel_steps.py`, `gui/block_spin.py`) rather than
    ported:

    A **wheel** over an unfocused knob is a scroll, not an edit. Qt's own
    `wheelEvent` steps without consulting focus, so a flick down the panel
    commits every control it passes — each one a re-plan, a cache key and a
    synchronous window render (`gui/tuning.py`). Declining is enough to hand
    the gesture on: `step_pane.py` puts every generated form inside a
    `QScrollArea`, so the enclosing thing a wheel could mean instead always
    exists, and v2's event hook had to forward by hand only because it sat
    above the `wheelEvent` it was replacing rather than inside it.

    **Keyboard tracking** is off, so an edit runs from the first keystroke to a
    commit and nothing in between reaches the document. With it on, typing
    `120` into a frame count commits `1`, then `12`, then `120` — two of those
    for values the user was in the middle of typing.

    Programmatic `setValue` still emits, which is what the construction rule
    relies on being ordered around rather than screened out.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _keep_focus_off_the_wheel(self)
        self.setKeyboardTracking(False)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class _IntegerSpin(_CommittedSpin, QSpinBox):
    pass


class _RealSpin(_CommittedSpin, QDoubleSpinBox):
    pass


class _ChoiceCombo(QComboBox):
    """A drop list whose value changes when the user says it does.

    The third pass-through case, and the one with a decision in it. `activated`
    is Qt's "the user chose this", but Qt counts arrowing a *closed* combo as
    an act of selection, so holding Down through a tool's mode list commits
    every mode on the way past. v2 removed the case rather than screening the
    signal (`gui/commit_combo.py`), and that is what is re-derived here:
    navigation keys open the popup, where highlighting and selecting are
    distinct states, and `activated` becomes a complete statement of intent.

    Screening it was the alternative, and it costs a pending-value display — a
    combo that has chosen something it has not committed must *show* that, or
    it looks more live than it is.

    A wheel is declined outright rather than gated on focus like a spin box's.
    A knob still has to step for someone who means to step it; a combo has no
    step that is not a commit.

    Type-to-search is left alone: a keystroke naming an entry says *which*
    entry rather than walking past the ones between.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        _keep_focus_off_the_wheel(self)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in _NAVIGATION_KEYS and not self.view().isVisible():
            self.showPopup()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


def _scalar_range(
    described: Mapping[str, Any], value: Any, labels: Mapping[str, str], on_edit: _Edit
) -> QWidget:
    """A spin box over the field's declared range, integer or real.

    Which of the two is the schema's `type` rather than the stored value's:
    a float parameter left at a whole-numbered default is still a float
    parameter, and reading the value would give it an integer control for as
    long as it stayed there.
    """
    if described.get("type") == "integer":
        low, high = _bounds(described, nudge=1)
        spin = _IntegerSpin()
        spin.setRange(int(low), int(high))
        spin.setValue(int(value))
        # After `setValue`, so building a form is not an edit of the document
        # it was built from.
        spin.valueChanged.connect(on_edit)
        return spin

    low, high = _bounds(described, nudge=_NUDGE)
    real = _RealSpin()
    real.setDecimals(_DECIMALS)
    real.setRange(low, high)
    # A range a step of 1 would cross in one press needs a finer one, or a
    # bounded fraction is unreachable by arrow key. Wide and unbounded fields
    # keep Qt's default step.
    real.setSingleStep(0.05 if high - low <= 2.0 else 1.0)
    real.setValue(float(value))
    real.valueChanged.connect(on_edit)
    return real


def _bounds(described: Mapping[str, Any], *, nudge: float) -> tuple[float, float]:
    """The field's inclusive range, `_UNBOUNDED` on the side it declares none.

    An exclusive bound becomes the inclusive one a step inside it: a spin box
    has no way to express "greater than zero", and `nudge` is that step in the
    units of the control — one frame for an integer, `_NUDGE` for a real.
    """
    low, high = float(-_UNBOUNDED), float(_UNBOUNDED)
    if "minimum" in described:
        low = float(described["minimum"])
    elif "exclusiveMinimum" in described:
        low = float(described["exclusiveMinimum"]) + nudge
    if "maximum" in described:
        high = float(described["maximum"])
    elif "exclusiveMaximum" in described:
        high = float(described["exclusiveMaximum"]) - nudge
    return low, high


def _enum(
    described: Mapping[str, Any], value: Any, labels: Mapping[str, str], on_edit: _Edit
) -> QWidget:
    """A drop list of the choices the field admits, labelled by the tool.

    The stored value rides on the item rather than being parsed back out of its
    text: `param_value_labels` exists so `anti_alias: True` can read as
    "average", and a label that could be read backwards would be a label the
    tool was not free to write.

    `activated` is Qt's "the user chose this", and a parameter edit has to be
    exactly that: every value merely passed through is a re-plan, a new cache
    key and a render. `_ChoiceCombo` is what makes the signal say the whole of
    that.
    """
    combo = _ChoiceCombo()
    for choice in described.get("enum", (True, False)):
        combo.addItem(labels.get(str(choice), str(choice)), choice)
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)
    combo.activated.connect(lambda position: on_edit(combo.itemData(position)))
    return combo


def _stated_value(
    described: Mapping[str, Any], value: Any, labels: Mapping[str, str], on_edit: _Edit
) -> QWidget:
    """What a composite parameter holds, until the editor that populates it.

    Read-only rather than a disabled editor: the surfaces these kinds are
    populated from are the canvas, the timeline and the graph panel, and a
    stand-in control shaped like a text field would be teaching the user a
    gesture that is not the one arriving.
    """
    return QLabel(str(value))


#: What a path field reads as while the document holds none. A sentence rather
#: than a blank row: a source nobody has chosen a file for is the state VISION's
#: minted project starts in, so it is a state the surface names.
UNCHOSEN = "nothing chosen"


def ask_for_file(parent: QWidget | None = None) -> Path | None:
    """Which file this parameter should name, or nothing if the ask was cancelled.

    The dialog narrows by nothing. What a tool can read is not something this
    module can know — the map below is keyed on a population kind and never on a
    tool (`adr/gui-knows-kinds-not-tools.md`) — and a pattern written here would
    be a second, guessed answer to a question the reader one step down already
    refuses concretely.
    """
    chosen, _pattern = QFileDialog.getOpenFileName(parent, "Choose a file")
    return Path(chosen) if chosen else None


def ask_for_folder(parent: QWidget | None = None) -> Path | None:
    """Which folder this parameter should name, or nothing if the ask was cancelled.

    A second ask rather than one dialog admitting both: Qt's file dialog selects
    files or directories and not either, and the two are different questions
    anyway — VISION's user picks a video and then changes their mind and names
    the folder it came out of, which is a decision about what the source *is*.
    """
    chosen = QFileDialog.getExistingDirectory(parent, "Choose a folder")
    return Path(chosen) if chosen else None


class PathChooser(QWidget):
    """What a path parameter holds, and the two verbs that rewrite it.

    The value and not what it resolved to. A path naming a folder stands for
    every file in it, and the ordering that produces is a filesystem read with a
    lifetime (`pipeline/resolve_source.resolved_sources`) — so it is drawn where
    the window can invalidate it, on the card (`chain_stack.Step.sources`), and
    a chooser showing it here would be offering a stale reading as the document's
    own value.

    A label rather than a line edit. A path typed a character at a time would
    reach `SetParam` naming files nobody meant on the way to the one they did,
    which is the pass-through the generated controls exist to refuse; the ask is
    the commit, exactly as a combo's `activated` is.
    """

    def __init__(self, value: str, on_edit: _Edit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.shown = QLabel(value or UNCHOSEN)
        self.shown.setToolTip(value or UNCHOSEN)
        # The two asks are named inside a lambda rather than handed over, so the
        # module attribute is read when the button is pressed: a caller standing
        # in front of the dialog does so after the form was built, and a button
        # holding the function it was constructed with would open the real one.
        self.browse_file = _browse_button(
            "file…", "Choose a file", lambda: ask_for_file(self), on_edit, self
        )
        self.browse_folder = _browse_button(
            "folder…",
            "Choose a folder, read as everything in it",
            lambda: ask_for_folder(self),
            on_edit,
            self,
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.shown)
        layout.addStretch(1)
        layout.addWidget(self.browse_file)
        layout.addWidget(self.browse_folder)


def _browse_button(
    text: str, tip: str, ask: Callable[[], Path | None], on_edit: _Edit, parent: QWidget
) -> QToolButton:
    """One verb of the chooser: ask, and edit only where the ask was answered.

    A cancelled ask is the one answer that must not reach the document, which is
    the same rule a new project's location runs on (`project_select.ask_where`)
    and for the same reason: the alternative to declining is a value nobody
    chose.

    What is written is the path as the dialog gave it, which is absolute — the
    resolution takes an absolute pattern as it stands and resolves a relative
    one against the process's directory (`core.tool_base.named_files`), so a
    chooser that stored a relative one would name a different file from the next
    launch.
    """
    button = QToolButton(parent)
    button.setText(text)
    button.setAutoRaise(True)
    button.setToolTip(tip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(lambda: None if (got := ask()) is None else on_edit(str(got)))
    return button


def _path(
    described: Mapping[str, Any], value: Any, labels: Mapping[str, str], on_edit: _Edit
) -> QWidget:
    """The chooser, over whatever the document holds for this field."""
    del described, labels
    return PathChooser(str(value or ""), on_edit)


#: Kind to control, and the whole of this module's tool knowledge. Total over
#: `ParamStereotype`, which `tests/gui/test_param_generator.py` holds: a kind
#: minted without an entry here is a parameter no panel can show, and the
#: refusal in `ParamForm` is what keeps that loud rather than blank.
_BUILDERS: dict[ParamStereotype, _Builder] = {
    ParamStereotype.SCALAR_RANGE: _scalar_range,
    ParamStereotype.ENUM: _enum,
    ParamStereotype.SPAN: _stated_value,
    ParamStereotype.BAND: _stated_value,
    ParamStereotype.REGION: _stated_value,
    ParamStereotype.POINT: _stated_value,
    ParamStereotype.PATH: _path,
}


class ParamForm(QWidget):
    """The parameters of one node, generated from its tool's spec.

    The spec is handed in rather than looked up: this module never learns which
    tool it is drawing, and a registry lookup here would be the one import that
    made a `tool_id` branch possible to write.

    `replicate_id` is the tail of every address the form reads and writes, and
    it is the caller's answer rather than one derived here — which region the
    window is standing on is view state and nothing in the document records it
    (`gui/app.py`). `None` is the baseline, which is what a project with no
    regions has and the only thing a form over one could mean. No control
    branches on it: a spin box on region 2 and a spin box on a project that has
    none are the same widget emitting the same kind at a longer or shorter
    address (`session/intents.SetParam`).
    """

    #: The document has just been written to. Carries nothing: what changed is
    #: already in the session, and a payload here would be a second description
    #: of the edit for a listener to disagree with.
    edited = Signal()

    def __init__(
        self,
        session: Session,
        node_id: str,
        spec: ToolSpec,
        parent: QWidget | None = None,
        *,
        replicate_id: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._node_id = node_id
        self._replicate_id = replicate_id
        self._widgets: dict[str, QWidget] = {}

        properties: Mapping[str, Mapping[str, Any]] = resolved_schema(spec.params_model)[
            "properties"
        ]
        values = session.project.params_for(node_id, replicate_id)
        layout = QFormLayout(self)
        for name, described in properties.items():
            kind = spec.param_stereotypes[name]
            build = _BUILDERS.get(kind)
            if build is None:
                raise ValueError(
                    f"{spec.tool_id}: parameter {name!r} declares population kind {kind}, which "
                    "no widget is generated for — a kind is minted with the editor that "
                    "populates it (adr/gui-knows-kinds-not-tools.md)"
                )
            widget = build(
                described,
                values.get(name, described.get("default")),
                spec.param_value_labels.get(name, {}),
                partial(self._edit, name),
            )
            self._widgets[name] = widget
            layout.addRow(name.replace("_", " "), widget)

    def widget(self, name: str) -> QWidget:
        """The control generated for parameter `name`."""
        return self._widgets[name]

    def _edit(self, name: str, value: Any) -> None:
        if issue(
            self._session,
            SetParam(
                node_id=self._node_id,
                param=name,
                value=value,
                replicate_id=self._replicate_id,
            ),
        ):
            self.edited.emit()
