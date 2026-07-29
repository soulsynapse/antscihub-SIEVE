













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


_UNBOUNDED = 1_000_000


def param_rows(
    node: Node,
    hidden: frozenset[str],
    on_edit: Callable[[str, object], None],
) -> list[QWidget]:






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


    return None


def _bounds(metadata: list[Any], *, integer: bool) -> tuple[float, float]:

    low, high = float(-_UNBOUNDED), float(_UNBOUNDED)
    nudge = 1.0 if integer else 1e-6
    for constraint in metadata:
        if isinstance(constraint, annotated_types.Ge):
            low = float(constraint.ge)
        elif isinstance(constraint, annotated_types.Gt):
            low = float(constraint.gt) + nudge
        elif isinstance(constraint, annotated_types.Le):
            high = float(constraint.le)
        elif isinstance(constraint, annotated_types.Lt):
            high = float(constraint.lt) - nudge
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
