"""Secret: what keyboard shortcuts exist and what each does.

Not the window itself — ``app.py`` owns the window, this module only ever
attaches shortcuts to it. Not playback itself — ``video_player.py`` owns
what "play" and "pause" mean, this module only ever calls it. Adding or
rebinding a hotkey must not touch app.py or video_player.py; changing what
the window or the player is otherwise made of must never touch this file.

Two entry points, bound at different times because their targets have
different lifetimes. ``bind_hotkeys`` targets a specific ``VideoPlayer``
instance (Space — play/pause) and is re-called every time the workspace is
rebuilt, once per fresh player; it retires its own previous shortcut first
so a stale one bound to an already-deleted player never lingers to fire
(and error) alongside the new one. ``bind_navigation_hotkeys`` targets
stable methods on the window itself (Left/Right — ``go_back``/
``go_forward``) and is meant to be bound once, at window construction — the
methods it calls stay valid across every screen swap, so nothing about it
needs rebinding. What "back" and "forward" mean (project info, the Pipeline
tab, the Step tab) is entirely ``app.py``'s secret; this module only ever
wires the two keys to the two verbs.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow

from proto_sieve.src.sieve.gui.canvas.video_player import VideoPlayer

_PLAY_PAUSE_SHORTCUT_ATTR = "_play_pause_shortcut"


def bind_hotkeys(window: QMainWindow, video_player: VideoPlayer) -> None:
    stale = getattr(window, _PLAY_PAUSE_SHORTCUT_ATTR, None)
    if stale is not None:
        stale.setParent(None)
        stale.deleteLater()

    play_pause = QShortcut(QKeySequence(Qt.Key_Space), window)
    play_pause.setAutoRepeat(False)
    play_pause.activated.connect(video_player.toggle_play_pause)
    setattr(window, _PLAY_PAUSE_SHORTCUT_ATTR, play_pause)


def bind_navigation_hotkeys(window: QMainWindow) -> None:
    back = QShortcut(QKeySequence(Qt.Key_Left), window)
    back.setAutoRepeat(False)
    back.activated.connect(window.go_back)

    forward = QShortcut(QKeySequence(Qt.Key_Right), window)
    forward.setAutoRepeat(False)
    forward.activated.connect(window.go_forward)


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
    from proto_sieve.src.sieve.gui.canvas.video_player import VideoPlayer

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
