"""Shows a pipeline's steps. For now: step index and tool name, nothing else —
no params, no selection, no wiring to the executor."""

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

from PySide6.QtWidgets import QListWidget, QVBoxLayout, QWidget

from proto_sieve.src.sieve.pipeline import Pipeline


class PipelinePanel(QWidget):
    def __init__(self, pipeline: Pipeline, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._list = QListWidget(self)
        for i, step in enumerate(pipeline.steps, start=1):
            self._list.addItem(f"{i}. {step.tool}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)


if __name__ == "__main__":
    # Standalone smoke test: this widget must show something on its own,
    # with no app.py, no layout.py, no video in the loop.
    from PySide6.QtWidgets import QApplication

    from proto_sieve.src.sieve.pipeline import Step

    pipeline = Pipeline(
        source="rep3_intermittent_crop",
        steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
    )

    app = QApplication(sys.argv)
    panel = PipelinePanel(pipeline)
    panel.resize(300, 400)
    panel.show()
    sys.exit(app.exec())
