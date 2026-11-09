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
    "decoder": set(),
    "writers": {"decoder"},                       # a baked clip reads back through the Decoder
    "store": {"document", "writers"},             # where files land knows what a Bake is and which kinds write; never the reverse
    "worker": {"decoder", "density", "document", "graph", "store"},
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


def test_the_worker_walks_the_clip_with_no_twin_of_a_window_field_or_method():
    """One _Walk serves the window and the clip; a private worker name beside its `_c` or `_clip`
    prefixed twin is the second copy of the walk coming back."""
    tree = ast.parse((PKG / "worker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
    twins = {n for n in names if n.startswith("_") and (f"_c{n[1:]}" in names or f"_clip{n}" in names)}
    assert not twins, twins


def test_a_module_header_states_the_module_not_its_history():
    def header_lines(path):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")), clean=False) or ""
        return len(doc.splitlines())

    long = {str(p.relative_to(PKG)): n for p in PKG.rglob("*.py") if (n := header_lines(p)) > HEADER_LINES}
    assert not long, long


def test_the_scheduler_alone_begins_a_job_and_nothing_compares_a_generation():
    """A job's reset is its begin(), called once per job and only from _turn, the ladder; an ask is
    a flag the ladder takes under the lock, so no generation counter is compared, by a job or by
    anyone. A job's due-ness is read in one place, _turn, which is both what the loop waits on and
    what it serves: no job answers `pending`, and nothing outside _turn reads an ask or a `due`."""
    tree = ast.parse((PKG / "worker.py").read_text(encoding="utf-8"))
    turn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_turn")

    def begins(node):
        return [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "begin"]

    assert {id(n) for n in begins(tree)} == {id(n) for n in begins(turn)}
    assert sorted(ast.unparse(n.func.value) for n in begins(turn)) == ["bake", "clip", "win"]
    compared = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Compare)
                and any(isinstance(o, ast.Attribute) and o.attr in ("gen", "asked") for o in [n.left, *n.comparators])]
    assert not compared, compared
    assert not [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "pending"]

    def reads(node):
        return {id(n) for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr in ("asked", "due") and isinstance(n.ctx, ast.Load)}

    assert reads(tree) == reads(turn)
