"""The GUI sitting, per docs/AGENTS.md: not a chunk, no cheap proof.

PySide6. Video on the left (``VideoPlayer``, owns what's played), pipeline
steps on the right (``PipelinePanel``, step/tool only for now). The pipeline
here is hardcoded — nothing yet feeds it from a saved file or the resolver.
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
    # Makes `python app.py` work the same as `python -m ...gui.app` — the
    # package-style imports below need the repo root on sys.path, which a
    # direct script launch (VSCode's "Run Python File", etc.) doesn't add.
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from proto_sieve.src.sieve.gui.layout import compose, size_window
from proto_sieve.src.sieve.gui.menu import build_menu_bar
from proto_sieve.src.sieve.gui.pipeline_panel import PipelinePanel
from proto_sieve.src.sieve.gui import style
from proto_sieve.src.sieve.gui.style import apply as apply_style
from proto_sieve.src.sieve.gui.style import apply_title_bar
from proto_sieve.src.sieve.gui.video_player import VideoPlayer
from proto_sieve.src.sieve.pipeline import Pipeline, Step
from proto_sieve.src.sieve.preferences import appearance as appearance_prefs

VIDEO_PATH = _REPO_ROOT / "video-test" / "rep3_intermittent_crop.MP4"

PIPELINE = Pipeline(
    source="rep3_intermittent_crop",
    steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("proto_sieve")

        self._video_player = VideoPlayer()
        self._pipeline_panel = PipelinePanel(PIPELINE)

        self._top_bar = QLabel("top")
        self._top_bar.setFixedHeight(style.bar_height())
        style.tag(self._top_bar, style.ROLE_BAR)
        self._bottom_bar = QLabel("bottom")
        self._bottom_bar.setFixedHeight(style.bar_height())
        style.tag(self._bottom_bar, style.ROLE_BAR)

        self.setCentralWidget(
            compose(self._top_bar, self._video_player, self._pipeline_panel, self._bottom_bar)
        )

        build_menu_bar(self)

        self._video_player.open(VIDEO_PATH)

        size_window(self)


def main() -> None:
    app = QApplication(sys.argv)
    apply_style(app)
    window = MainWindow()
    window.show()
    apply_title_bar(window)
    appearance_prefs.subscribe(lambda: apply_style(app))
    appearance_prefs.subscribe(lambda: apply_title_bar(window))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
