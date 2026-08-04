"""Secret: what the step list looks like — the ordered rows (one
``StepBox`` per step) that fill the "Step" position of ``control.py``'s
three-pane track. Not the rail (``rail.py``), not the "Pipeline" pane
(nothing designed there yet — not stubbed to look designed), not which
position is current or how switching between them looks — all
``control.py``'s secret now, one level up from where this module used to
own it directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

def _find_repo_root(start: Path) -> Path:
    # Walks up to the marker (pyproject.toml) instead of counting parents —
    # a fixed index breaks the moment this file moves to a different depth.
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"no pyproject.toml found above {start}")


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(_REPO_ROOT) not in sys.path:
    # Same reasoning as app.py: makes running this file directly work the
    # same as running it via -m.
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

from proto_sieve.src.sieve.gui.control.pipeline.step import StepBox
from proto_sieve.src.sieve.pipeline import Pipeline


def build_step_list(pipeline: Pipeline) -> QWidget:
    step_list = QListWidget()
    for i, step in enumerate(pipeline.steps, start=1):
        box = StepBox(i, step)
        item = QListWidgetItem(step_list)
        item.setSizeHint(box.sizeHint())
        step_list.addItem(item)
        step_list.setItemWidget(item, box)
    return step_list


if __name__ == "__main__":
    # Standalone smoke test: this widget must show something on its own,
    # with no app.py, no control.py, no video in the loop.
    from PySide6.QtWidgets import QApplication

    from proto_sieve.src.sieve.pipeline import Step

    pipeline = Pipeline(
        source="rep3_intermittent_crop",
        steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
    )

    app = QApplication(sys.argv)
    widget = build_step_list(pipeline)
    widget.resize(300, 400)
    widget.show()
    sys.exit(app.exec())
