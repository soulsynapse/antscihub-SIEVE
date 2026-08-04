"""Secret: how a single step is displayed — the box for one (tool, params)
entry in the pipeline list. Not the list itself — ``pipeline.py`` owns
ordering and which step is selected, this module only ever draws one entry,
given the step and its position.
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
    # Same reasoning as pipeline.py: makes running this file directly
    # work the same as running it via -m.
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from proto_sieve.src.sieve.pipeline import Step


class StepBox(QWidget):
    def __init__(self, index: int, step: Step, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        label = QLabel(f"{index}. {step.tool}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(label)


if __name__ == "__main__":
    # Standalone smoke test: this widget must show something on its own,
    # with no app.py, no layout.py, no pipeline.py in the loop.
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    box = StepBox(1, Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}))
    box.show()
    sys.exit(app.exec())
