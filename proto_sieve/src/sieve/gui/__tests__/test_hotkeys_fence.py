"""hotkeys/ owns the claim that no keyboard shortcut lives outside it —
nothing outside ``gui/hotkeys/`` may import ``QShortcut``/``QKeySequence``
or define ``keyPressEvent``. Never observed red: this scans the tree as it
stands, not a chunk's before/after proof.
"""
import ast
from pathlib import Path

SIEVE_ROOT = Path(__file__).resolve().parents[2]
GUI_ROOT = SIEVE_ROOT / "gui"
HOTKEYS_ROOT = GUI_ROOT / "hotkeys"

_FORBIDDEN_IMPORTS = {"QShortcut", "QKeySequence"}


def _violations_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in _FORBIDDEN_IMPORTS:
                    hits.append(alias.name)
        elif isinstance(node, ast.FunctionDef) and node.name == "keyPressEvent":
            hits.append("keyPressEvent")
    return hits


def test_nothing_outside_hotkeys_defines_a_shortcut():
    violations = []
    for path in GUI_ROOT.rglob("*.py"):
        if HOTKEYS_ROOT in path.parents or "__pycache__" in path.parts:
            continue
        for name in _violations_in(path):
            violations.append(f"{path}: uses {name!r}")

    assert not violations, (
        "a hotkey was defined outside gui/hotkeys/ — found: "
        f"{violations}"
    )
