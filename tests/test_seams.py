"""The seams: which modules under sieve_player may import which, and how much a module header may say."""
import ast
import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "sieve_player"
TOOLS = PKG.parent / "tools"
HEADER_LINES = 10   # a module docstring states the module and its seams; past this it is a changelog, see CLAUDE.md
MAY_IMPORT = {
    "document": set(),
    "plan": {"document"},
    "graph": {"document", "density", "plan"},     # Graph.density folds planes; sync holds a plan
    "canvas": {"document", "theme"},
    "pane": {"document", "theme", "widgets"},
    "widgets": {"density", "theme"},
}


def imports_of(name):
    """The sieve_player modules `name` imports, at any depth of the file."""
    tree = ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8"))
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            out |= {a.name for a in node.names} if node.module is None else {node.module.split(".")[0]}
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("sieve_player."):
            out.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            out |= {a.name.split(".")[1] for a in node.names if a.name.startswith("sieve_player.")}
    return out


def test_imports_run_one_way():
    for name, allowed in MAY_IMPORT.items():
        assert imports_of(name) <= allowed, f"{name} imports {imports_of(name) - allowed}"


def test_canvas_and_pane_never_name_the_runtime():
    for name in ("canvas", "pane"):
        src = (PKG / f"{name}.py").read_text(encoding="utf-8")
        assert not re.search(r"\bGraph\b|\.graph\b|sieve_player\.graph", src), name


def test_a_tool_imports_what_tools_share_and_never_another_tool():
    """A stem beginning with `_` under tools/ is what tools share, as the registry's skip says; a
    tool's `__main__` block, which runs it alone beside its neighbours, is the one place a tool may
    name another."""
    def imports(path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        body = [n for n in tree.body if not (isinstance(n, ast.If) and "__main__" in ast.unparse(n.test))]
        out = set()
        for node in (n for stmt in body for n in ast.walk(stmt)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tools":
                out |= {node.module.split(".")[1]} if "." in node.module else {a.name for a in node.names}
            elif isinstance(node, ast.Import):
                out |= {a.name.split(".")[1] for a in node.names if a.name.startswith("tools.")}
        return out

    bad = {p.name: sorted(peers) for p in TOOLS.glob("*.py") if (peers := {m for m in imports(p) if not m.startswith("_")})}
    assert not bad, bad


def test_a_module_header_states_the_module_not_its_history():
    def header_lines(path):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")), clean=False) or ""
        return len(doc.splitlines())

    long = {str(p.relative_to(PKG)): n for p in PKG.rglob("*.py") if (n := header_lines(p)) > HEADER_LINES}
    assert not long, long
