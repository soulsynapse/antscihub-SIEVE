"""Secret: the strip of one tick per step, on the left edge of the pipeline
panel, marking which step is current — the "halo" treatment: a small dot
for every step, and a soft rounded backdrop behind whichever one is
current. Not which step that is — ``pipeline.py`` owns and passes
``current_index``. Not what a tick or the halo look like — ``gui/style.py``
owns those roles' colors. This module only ever lays the ticks out, one
per step, vertical, and never hides — nothing here depends on which of
``pipeline.py``'s tabs is showing.
"""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from proto_sieve.src.sieve.gui import style

_TICK_SIZE = 8
_HALO_PADDING = 4


class StepRail(QWidget):
    def __init__(
        self, step_count: int, current_index: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for i in range(step_count):
            layout.addWidget(self._build_current() if i == current_index else self._build_tick())
        layout.addStretch(1)

    def _build_tick(self) -> QWidget:
        tick = QWidget(self)
        tick.setFixedSize(_TICK_SIZE, _TICK_SIZE)
        style.tag(tick, style.ROLE_STEP_TICK)
        return tick

    def _build_current(self) -> QWidget:
        halo = QWidget(self)
        style.tag(halo, style.ROLE_STEP_HALO)

        halo_layout = QVBoxLayout(halo)
        halo_layout.setContentsMargins(_HALO_PADDING, _HALO_PADDING, _HALO_PADDING, _HALO_PADDING)
        tick = QWidget(halo)
        tick.setFixedSize(_TICK_SIZE, _TICK_SIZE)
        style.tag(tick, style.ROLE_STEP_TICK_CURRENT)
        halo_layout.addWidget(tick)

        return halo


if __name__ == "__main__":
    # Standalone smoke test: this widget must show something on its own,
    # with no app.py, no layout.py, no pipeline.py in the loop.
    import sys
    from pathlib import Path

    def _find_repo_root(start: Path) -> Path:
        # Walks up to the marker (pyproject.toml) instead of counting
        # parents — a fixed index breaks the moment this file moves depth.
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate
        raise RuntimeError(f"no pyproject.toml found above {start}")

    _repo_root = _find_repo_root(Path(__file__).resolve())
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

    from PySide6.QtWidgets import QApplication

    from proto_sieve.src.sieve.gui.style import apply as apply_style

    app = QApplication(sys.argv)
    apply_style(app)
    rail = StepRail(step_count=6, current_index=3)
    rail.resize(40, 200)
    rail.show()
    sys.exit(app.exec())
