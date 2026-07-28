"""Parameter rows for a node, built from its registered params model.

The five parity steps have hand-built card bodies in `gui/filter_tab.py`; this
is for everything else the wizard can insert (`downsample`, `background_ema`,
whatever arrives on the shelf later). One widget per model field, bounds from
the field's own constraints, so a filter's settings surface exists the moment
the filter does — no per-filter GUI code, which is non-negotiable #3's "one
class + one markdown" holding at the widget layer.

Edits flow one way: widget → `on_edit(name, value)` → the tab rewrites the
chain value and the caption restates it. Nothing here reads the chain back;
a rebuilt form is how new values arrive, exactly like the stack's cards.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

import annotated_types
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

from sieve.core.filter_registry import REGISTRY
from sieve.core.pipeline_model import Node
from sieve.gui.band_plot import DIM
from sieve.gui.commit_combo import CommitCombo

#: What a numeric field spans when it declares no bounds of its own.
_UNBOUNDED = 1_000_000


def param_rows(
    node: Node,
    hidden: frozenset[str],
    on_edit: Callable[[str, object], None],
) -> list[QWidget]:
    """One labelled row per editable field of `node`'s params model.

    `hidden` names fields that mirror chain state rather than user intent
    (the catalog entry's `hidden_params`); they get no widget at all rather
    than a disabled one, because a knob the user must not touch is noise.
    """
    spec = REGISTRY.get(node.filter_id, node.version)
    rows: list[QWidget] = []
    for name, field in spec.params_model.model_fields.items():
        if name in hidden:
            continue
        current = node.params.get(name, field.default)
        widget = _widget_for(field.annotation, current, field.metadata, name, on_edit)
        if widget is not None:
            rows.append(_row(name.replace("_", " "), widget))
    return rows


def _widget_for(
    annotation: object,
    current: object,
    metadata: list[Any],
    name: str,
    on_edit: Callable[[str, object], None],
) -> QWidget | None:
    if isinstance(annotation, type) and issubclass(annotation, StrEnum):
        combo = CommitCombo()
        combo.addItems([member.value for member in annotation])
        combo.setCurrentText(str(current))

        def text_edited(text: str) -> None:
            on_edit(name, text)

        # `textActivated`, not `currentTextChanged`: this is a filter parameter,
        # so every value the user merely passes through would be a re-plan, a
        # new cache key, and a render. `CommitCombo` is what makes the signal a
        # complete statement of intent — see its module docstring.
        combo.textActivated.connect(text_edited)
        return combo
    if annotation is bool:
        box = QCheckBox()
        box.setChecked(bool(current))

        def bool_edited(checked: bool) -> None:
            on_edit(name, checked)

        box.toggled.connect(bool_edited)
        return box
    if annotation is int:
        low, high = _bounds(metadata, integer=True)
        spin = QSpinBox()
        spin.setRange(int(low), int(high))
        spin.setValue(current if isinstance(current, int) else int(float(str(current))))

        def int_edited(value: int) -> None:
            on_edit(name, value)

        spin.valueChanged.connect(int_edited)
        return spin
    if annotation is float:
        low, high = _bounds(metadata, integer=False)
        dspin = QDoubleSpinBox()
        dspin.setDecimals(3)
        dspin.setRange(low, high)
        dspin.setSingleStep(0.05 if high - low <= 2.0 else 1.0)
        dspin.setValue(current if isinstance(current, float) else float(str(current)))

        def float_edited(value: float) -> None:
            on_edit(name, value)

        dspin.valueChanged.connect(float_edited)
        return dspin
    # A field the form cannot express (nested model, tuple) simply has no
    # row; the filter's own card can grow one when a real filter needs it.
    return None


def _bounds(metadata: list[Any], *, integer: bool) -> tuple[float, float]:
    """The field's declared range, or a wide-open one."""
    low, high = float(-_UNBOUNDED), float(_UNBOUNDED)
    nudge = 1.0 if integer else 1e-6
    for constraint in metadata:
        if isinstance(constraint, annotated_types.Ge):
            low = float(constraint.ge)  # type: ignore[arg-type]
        elif isinstance(constraint, annotated_types.Gt):
            low = float(constraint.gt) + nudge  # type: ignore[arg-type]
        elif isinstance(constraint, annotated_types.Le):
            high = float(constraint.le)  # type: ignore[arg-type]
        elif isinstance(constraint, annotated_types.Lt):
            high = float(constraint.lt) - nudge  # type: ignore[arg-type]
    return low, high


def _row(label: str, widget: QWidget) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    tag = QLabel(label)
    tag.setStyleSheet(f"color: {DIM.name()};")
    layout.addWidget(tag)
    layout.addWidget(widget)
    layout.addStretch(1)
    return row
