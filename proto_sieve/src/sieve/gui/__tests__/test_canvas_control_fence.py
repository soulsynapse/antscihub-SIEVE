"""canvas/ and control/ own the claim that the dependency between the two
slots runs one way: control mutates shared session/app state, canvas only
ever reads it back. Nothing under ``gui/canvas/`` may import from
``gui/control/`` — a canvas must never need to know a specific control
exists, even once it grows elements the user clicks or drags (a crop box on
the video, say). The reverse (control importing canvas) is not checked
here — nothing says it can't happen, only that canvas can't depend the
other way. Never observed red: this scans the tree as it stands, not a
chunk's before/after proof.
"""
import ast
from pathlib import Path

SIEVE_ROOT = Path(__file__).resolve().parents[2]
GUI_ROOT = SIEVE_ROOT / "gui"
CANVAS_ROOT = GUI_ROOT / "canvas"


def _imported_module_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_nothing_under_canvas_imports_control():
    violations = []
    for path in CANVAS_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for name in _imported_module_names(path):
            if "control" in name.split("."):
                violations.append(f"{path}: imports {name!r}")

    assert not violations, (
        "canvas depends on control, never the reverse — found canvas code "
        f"reaching into control: {violations}"
    )
