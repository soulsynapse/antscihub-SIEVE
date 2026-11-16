"""Print, for each Python file under tools/, its lines by what they are for, and the sums over the
tools, over the files tools share (a stem beginning with `_`) and over tools/retired. A top-level
statement's lines go whole to one column: `doc` the module docstring, `import`, `declared` an
assignment (the facets and the constants), `settings` a function named settings or widget, `draw` one
named draw, `launch` the `if __name__ == "__main__"` block, `compute` every other function, class or
statement; `blank` is what is left, blank lines and comments between statements, so a row sums to
its file. A median is of its own column, so a median row does not sum to the median file.

    python -X utf8 docs/findings/experiments/2026-11-16-what-a-tool-spends-its-lines-on.py
"""
import ast
import statistics
from pathlib import Path

COLUMNS = ("doc", "import", "declared", "settings", "draw", "launch", "compute", "blank")
WIDGET = ("settings", "widget")


def column(node, first):
    if first and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return "doc"
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return "import"
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return "declared"
    if isinstance(node, ast.FunctionDef):
        return "settings" if node.name in WIDGET else "draw" if node.name == "draw" else "compute"
    if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
        return "launch"
    return "compute"


def spent(path):
    text = path.read_text(encoding="utf-8")
    out = dict.fromkeys(COLUMNS, 0)
    body = ast.parse(text).body
    for i, node in enumerate(body):
        first = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
        out[column(node, i == 0)] += node.end_lineno - first + 1
    out["blank"] = len(text.splitlines()) - sum(out.values())
    return out


def show(name, row, lines=None):
    print(f"{name:<28}" + "".join(f"{row[c]:>9}" for c in COLUMNS) + f"{sum(row.values()) if lines is None else lines:>8}")


def total(title, rows):
    print()
    show(f"{title}, {len(rows)} files", {c: sum(r[c] for r in rows) for c in COLUMNS})
    show("  median", {c: statistics.median(r[c] for r in rows) for c in COLUMNS}, statistics.median(sum(r.values()) for r in rows))


def main():
    print(f"{'':<28}" + "".join(f"{c:>9}" for c in COLUMNS) + f"{'lines':>8}")
    groups = {"tools": [], "shared": [], "retired": []}
    for path in sorted(Path("tools").rglob("*.py")):
        row = spent(path)
        show(path.as_posix(), row)
        group = "retired" if path.parent.name == "retired" else "shared" if path.name.startswith("_") else "tools"
        groups[group].append(row)
    for title, rows in groups.items():
        total(title, rows)


if __name__ == "__main__":
    main()
