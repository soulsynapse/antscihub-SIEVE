"""gui owns the claim that nothing outside it depends on it — gui may import
the domain, the domain must never import gui. Never observed red: this scans
the tree as it stands, not a chunk's before/after proof.
"""
import ast
from pathlib import Path

SIEVE_ROOT = Path(__file__).resolve().parents[2]
GUI_ROOT = SIEVE_ROOT / "gui"


def _imported_module_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_nothing_outside_gui_imports_gui():
    violations = []
    for path in SIEVE_ROOT.rglob("*.py"):
        if GUI_ROOT in path.parents or "__pycache__" in path.parts:
            continue
        for name in _imported_module_names(path):
            if "gui" in name.split("."):
                violations.append(f"{path}: imports {name!r}")

    assert not violations, (
        "gui depends on the domain, never the reverse — found domain code "
        f"reaching into gui: {violations}"
    )
