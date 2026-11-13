"""The fourth deliverable of docs/spec/stream-seams.md: every module under sieve_player but ledger.py
read for a run taken by position and for a walk's identity built by hand, beside the same reading of
catalogue.py as it was at a7ceace5, so the reading is seen to find what was there; and a history
written in the shape before this one handed to `saved`. Prints each and exits 1 where one is not as built.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-the-ledgers-records-have-names.py
"""
import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from sieve_player.ledger import Node, Total, Under, View, Walk, save, saved  # noqa: E402

BEFORE = "a7ceace5"


def runs_in(node):
    return any(isinstance(n, ast.Attribute) and n.attr == "runs" for n in ast.walk(node))


def indexed(node, names):
    return (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int)
            and (runs_in(node.value) or isinstance(node.value, ast.Name) and node.value.id in names))


def read(src):
    """(lines taking a run or its key by position, lines building (lane, t0)) in `src`."""
    by_position, by_hand = set(), set()
    for node in ast.walk(ast.parse(src)):
        loops = [node] if isinstance(node, ast.For) else getattr(node, "generators", [])
        for loop in loops:
            if runs_in(loop.iter):
                if any(isinstance(n, ast.Tuple) for n in ast.walk(loop.target) if n is not loop.target):
                    by_position.add(loop.iter.lineno)      # unpacked where the runs are iterated
                names = {n.id for n in ast.walk(loop.target) if isinstance(n, ast.Name)}
                by_position |= {n.lineno for n in ast.walk(node) if indexed(n, names)}
        if indexed(node, ()):
            by_position.add(node.lineno)
        if isinstance(node, ast.Tuple) and [getattr(e, "attr", None) for e in node.elts] == ["lane", "t0"]:
            by_hand.add(node.lineno)
    return sorted(by_position), sorted(by_hand)


ok = True
was = read(subprocess.run(["git", "show", f"{BEFORE}:sieve_player/catalogue.py"], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout)
print(f"catalogue.py at {BEFORE}: a run by position on {len(was[0])} lines, (lane, t0) by hand on {len(was[1])}")
ok = ok and bool(was[0]) and bool(was[1])
for path in sorted((ROOT / "sieve_player").rglob("*.py")):
    if path.name == "ledger.py":
        continue
    by_position, by_hand = read(path.read_text(encoding="utf-8"))
    if by_position or by_hand or path.name in ("catalogue.py", "timeview.py"):
        print(f"{path.relative_to(ROOT).as_posix()}: a run by position on lines {by_position or 'none'}, (lane, t0) by hand on lines {by_hand or 'none'}")
    ok = ok and not by_position and not by_hand

walk = Walk("window", 0, 8, None, None, 1.0, 2.0, done=8, nodes={"a": Node(runs={Under("run", "walk", "a"): Total(8, 8.0, 64)})})
view = View(0.25, 0, [], [walk])
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "history.json"
    save(view, path)
    back, _ = saved(path)
    same = back.view() == view and back.view().walks[0].id == ("window", 1.0)
    print("a view saved and read back is equal to itself, its walk's id (lane, t0):", same)
    d = json.loads(path.read_text(encoding="utf-8"))
    d["walks"][0]["nodes"]["a"]["runs"] = [["run", "walk", "a", 8, 8.0, 64]]      # as save wrote a run before
    path.write_text(json.dumps(d), encoding="utf-8")
    try:
        saved(path)
        refused = None
    except ValueError as e:
        refused = str(e).replace(str(path), "history.json")
    print("a history of the shape before is refused:", refused)
    ok = ok and same and refused is not None
sys.exit(0 if ok else 1)
