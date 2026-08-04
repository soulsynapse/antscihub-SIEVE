"""video_player/ owns the claim that nothing outside it touches playback
machinery — nothing outside ``gui/canvas/video_player/`` may import
``QMediaPlayer`` or ``QVideoWidget``. Calling ``VideoPlayer``'s own public
methods (``open``, ``toggle_play_pause``) from elsewhere is the point of the
interface and is not a violation; reaching past it into the Qt classes it
wraps is. Never observed red: this scans the tree as it stands, not a
chunk's before/after proof.
"""
import ast
from pathlib import Path

SIEVE_ROOT = Path(__file__).resolve().parents[2]
GUI_ROOT = SIEVE_ROOT / "gui"
VIDEO_PLAYER_ROOT = GUI_ROOT / "canvas" / "video_player"

_FORBIDDEN_NAMES = {"QMediaPlayer", "QVideoWidget"}


def _forbidden_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in _FORBIDDEN_NAMES:
                    hits.append(alias.name)
    return hits


def test_nothing_outside_video_player_touches_playback_machinery():
    violations = []
    for path in GUI_ROOT.rglob("*.py"):
        if VIDEO_PLAYER_ROOT in path.parents or "__pycache__" in path.parts:
            continue
        for name in _forbidden_imports(path):
            violations.append(f"{path}: imports {name!r}")

    assert not violations, (
        "playback machinery was reached from outside "
        "gui/canvas/video_player/ — "
        f"found: {violations}"
    )
