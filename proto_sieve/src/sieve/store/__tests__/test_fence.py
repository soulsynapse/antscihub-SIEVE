"""store/ owns the claim that nothing outside it touches a file directly —
every other module goes through ``store.py``'s name-to-file primitive
(``save_text``/``load_text``/``list_names``) rather than opening, reading,
writing, or listing a path itself. Calling those three functions from
elsewhere is the point of the interface and is not a violation; reaching
past them to ``open()``/``Path.write_text``/``Path.glob``/etc. is. Never
observed red: this scans the tree as it stands, not a chunk's before/after
proof.
"""
import ast
from pathlib import Path

SIEVE_ROOT = Path(__file__).resolve().parents[2]
STORE_ROOT = SIEVE_ROOT / "store"

_FORBIDDEN_METHODS = {
    "write_text",
    "read_text",
    "write_bytes",
    "read_bytes",
    "glob",
    "iterdir",
    "mkdir",
    "unlink",
    "rmdir",
    "rename",
    "replace",
}


def _file_io_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open":
            hits.append("open(...)")
        elif isinstance(func, ast.Attribute) and func.attr in _FORBIDDEN_METHODS:
            hits.append(f".{func.attr}(...)")
    return hits


def test_nothing_outside_store_touches_a_file_directly():
    violations = []
    for path in SIEVE_ROOT.rglob("*.py"):
        if STORE_ROOT in path.parents or "__pycache__" in path.parts or "__tests__" in path.parts:
            continue
        for call in _file_io_calls(path):
            violations.append(f"{path}: {call}")

    assert not violations, (
        "file I/O was reached from outside store/'s name-to-file primitive — "
        f"found: {violations}"
    )
