"""Secret: what keyboard shortcuts exist and what each does.

Not the window itself — ``app.py`` owns the window, this module only ever
attaches shortcuts to it. Not playback itself — ``video_player.py`` owns
what "play" and "pause" mean, this module only ever calls it. Adding or
rebinding a hotkey must not touch app.py or video_player.py; changing what
the window or the player is otherwise made of must never touch this file.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow

from proto_sieve.src.sieve.gui.representation.video_player import VideoPlayer


def bind_hotkeys(window: QMainWindow, video_player: VideoPlayer) -> None:
    play_pause = QShortcut(QKeySequence(Qt.Key_Space), window)
    play_pause.setAutoRepeat(False)
    play_pause.activated.connect(video_player.toggle_play_pause)


if __name__ == "__main__":
    # Standalone smoke test: this binding must play/pause something on its
    # own, with no app.py, no layout.py, no pipeline in the loop.
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

    from PySide6.QtWidgets import QApplication, QMainWindow

    from proto_sieve.src.sieve.gui.hotkeys import bind_hotkeys
    from proto_sieve.src.sieve.gui.representation.video_player import VideoPlayer

    video_path = _repo_root / "video-test" / "rep3_intermittent_crop.MP4"

    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.open(video_path)

    window = QMainWindow()
    window.setCentralWidget(player)
    bind_hotkeys(window, player)
    window.resize(640, 480)
    window.show()
    sys.exit(app.exec())
