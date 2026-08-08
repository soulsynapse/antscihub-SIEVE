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

The four composite kinds have no editor yet, only a restatement of the value
they hold: `region` wants the canvas, `span` the timeline, and `band` an axis
the spec does not yet name (`todo/composite-kinds-get-their-editors.md`). They
are in the map rather than absent from it because a kind with no entry is a
refusal, and these are declared by tools on the shelf today.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import partial
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
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
        spin = QSpinBox()
        spin.setRange(int(low), int(high))
        spin.setValue(int(value))
        # After `setValue`, so building a form is not an edit of the document
        # it was built from.
        spin.valueChanged.connect(on_edit)
        return spin

    low, high = _bounds(described, nudge=_NUDGE)
    real = QDoubleSpinBox()
    real.setDecimals(_DECIMALS)
    real.setRange(low, high)
    # A tenth of the range, to two significant figures, so a bounded fraction
    # and a frame rate are both reachable by arrow key. Unbounded fields keep
    # the default step of 1.
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
    key and a render. It is not the whole of that claim — Qt activates a
    *closed* combo on arrow keys too, which is the pass-through v2 removed with
    a combo of its own
    (`todo/the-generated-controls-commit-on-intent-not-on-pass-through.md`).
    """
    combo = QComboBox()
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
}


class ParamForm(QWidget):
    """The parameters of one node, generated from its tool's spec.

    The spec is handed in rather than looked up: this module never learns which
    tool it is drawing, and a registry lookup here would be the one import that
    made a `tool_id` branch possible to write.
    """

    def __init__(
        self,
        session: Session,
        node_id: str,
        spec: ToolSpec,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._node_id = node_id
        self._widgets: dict[str, QWidget] = {}

        properties: Mapping[str, Mapping[str, Any]] = resolved_schema(spec.params_model)[
            "properties"
        ]
        values = session.project.params_for(node_id)
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
        issue(self._session, SetParam(node_id=self._node_id, param=name, value=value))
