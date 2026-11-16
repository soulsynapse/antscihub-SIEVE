"""Print, for each Python file under the folders given, its lines, the modules of
the tree it imports, and each top-level name with the lines it spans; with
--members, each class's members too. The lines between names are counted as the
module's own, so a file's figures sum to its length.

    python -X utf8 docs/findings/experiments/2026-11-16-what-a-module-holds.py sieve_player
    python -X utf8 docs/findings/experiments/2026-11-16-what-a-module-holds.py --members sieve_player/window.py
"""
import ast
import sys
from pathlib import Path

ROOTS = ("sieve_player", "tools", "utilities")


def span(node):
    first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return first, node.end_lineno


def imports(tree):
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            if node.level or base.split(".")[0] in ROOTS:
                for alias in node.names:
                    seen.add(f"{base}:{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in ROOTS:
                    seen.add(alias.name)
    return sorted(seen)


def report(path, members):
    text = path.read_text(encoding="utf-8")
    total = len(text.splitlines())
    tree = ast.parse(text)
    print(f"\n== {path.as_posix()}  {total} lines")
    print("   imports:", ", ".join(imports(tree)) or "none of the tree")
    named = 0
    for node in tree.body:
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        first, last = span(node)
        named += last - first + 1
        kind = "class" if isinstance(node, ast.ClassDef) else "def"
        print(f"   {first:5}-{last:<5} {last - first + 1:5}  {kind} {node.name}")
        if members and isinstance(node, ast.ClassDef):
            inner = 0
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    a, b = span(child)
                    inner += b - a + 1
                    print(f"        {a:5}-{b:<5} {b - a + 1:5}  {child.name}")
            print(f"        {'':11} {last - first + 1 - inner:5}  (the class's own lines)")
    print(f"   {'':11} {total - named:5}  (the module's own lines)")


def main(argv):
    members = "--members" in argv
    for arg in (a for a in argv if a != "--members"):
        root = Path(arg)
        files = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in files:
            report(path, members)


if __name__ == "__main__":
    main(sys.argv[1:])
