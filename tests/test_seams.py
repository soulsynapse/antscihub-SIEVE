"""The seams: which modules under sieve_player may import which, and how much a module header may say."""
import ast
import importlib
import re
import subprocess
import sys
from pathlib import Path

from sieve_player import stream

PKG = Path(__file__).resolve().parents[1] / "sieve_player"
TOOLS = PKG.parent / "tools"
UTILITIES = PKG.parent / "utilities"
HEADER_LINES = 10   # a module docstring states the module and its seams; past this it is a changelog, see CLAUDE.md
MAY_IMPORT = {
    "document": {"registry"},                     # what a tool declares is the registry's to read, and the registry imports nothing of the player
    "wire": set(),                                # what a wire carries; a tool reads it too, see TOOLS_MAY_IMPORT
    "cut": set(),                                 # a cut's record; the plan builds it and every reader of an extent takes it from there
    "plan": {"cut", "document", "registry", "wire"},
    "stream": set(),                              # the Event, the kinds and the Emitter; a reader of a dump loads nothing else
    "stats": {"stream"},                          # a reader of the stream; the Graph it is made on is handed to it
    "graph": {"cut", "decoder", "document", "density", "plan", "registry", "stream", "wire"},     # a value is memoized by what it read of its cut; Graph.density folds planes; sync holds a plan; it emits through an Emitter; a served file is read by a Decoder
    "canvas": {"document", "menu", "registry", "theme", "wire"},
    "menu": {"theme"},
    "pane": {"document", "registry", "theme", "widgets"},
    "widgets": {"theme"},
    "plot": {"density", "document", "theme"},       # document.shown is the one statement of what is drawn
    "timeline": {"theme"},
    "decoder": set(),
    "held": {"cut"},                              # a pickle and a stamp, and what a walk read of its cut; the window writes and reads it
    "walk": {"density", "graph", "registry", "stream", "wire"},         # of the stream, the words a begin says what began it by; no Qt, see below
    "worker": {"decoder", "graph", "stream", "walk"},
    "heldwalks": {"held", "walk", "wire"},       # the held runs as the walks take them; no Qt, so a one-off drives them without a window
    "bare": {"decoder", "document", "graph", "registry", "walk"},      # the clip walk's own process: no window, no stream's reader, no Qt
    "density": set(),
    "recent": set(),
    "theme": set(),
    "filemenu": {"document", "theme"},
    "trace": {"stream"},
    "ledger": {"stream", "trace"},                # the span kinds and a dump's reader; no graph is held and no Qt reached
    "catalogue": {"ledger", "stream"},            # a detector reads a view, by the stream's names for a kind, and nothing else
    "report": {"catalogue", "ledger"},            # the catalogue's findings as text; the catalogue renders none and never imports it
    "machine": set(),                             # psutil and the system's counters; the player is not imported
    "pace": set(),                                # the worker's signals and a clock; the control and the monitor's header both read it
    "store": {"recent"},                          # where the user's files are kept is where the store's default and its choice are
    "storecontrol": {"held", "store", "theme"},   # the store as the header draws it, in the units a held size is said in
    "pacecontrol": {"pace", "theme"},             # the control the player's header and the monitor's both draw; it is neither's
}
ROOTS = {"__init__", "__main__", "window"}        # what composes the rest and may import any of it


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


def jobs_tree():
    """The worker's ladder and the walk it turns, parsed as one module: what is asserted of a job holds across both files."""
    return ast.parse("\n".join((PKG / f"{name}.py").read_text(encoding="utf-8") for name in ("worker", "walk")))


def test_imports_run_one_way():
    for name, allowed in MAY_IMPORT.items():
        assert imports_of(name) <= allowed, f"{name} imports {imports_of(name) - allowed}"
    unsaid = {p.stem for p in PKG.glob("*.py")} - set(MAY_IMPORT) - ROOTS
    assert not unsaid, f"neither in MAY_IMPORT nor a root: {sorted(unsaid)}"


def test_the_registry_alone_reads_what_a_tool_declares():
    """Outside the registry no module of the player finds out what a tool declares: none names a
    facet to getattr or hasattr, reads a facet that is data as an attribute, or calls the
    registry's probe. Each asks the registry by a name that says what is asked; calling a facet the
    registry answered for is no reading. The registry itself imports nothing of the player."""
    from sieve_player.registry import FACETS

    data = {f for f in FACETS if f.isupper()}
    bad = []
    for path in PKG.rglob("*.py"):
        where = str(path.relative_to(PKG))
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if path.parent.name == "registry":
            took = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                    and ("sieve_player" in ast.unparse(n) or (isinstance(n, ast.ImportFrom) and n.level > 1))]
            bad += [(where, ast.unparse(n)) for n in took]
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("getattr", "hasattr") and len(n.args) > 1 \
                    and isinstance(n.args[1], ast.Constant) and n.args[1].value in FACETS:
                bad.append((where, ast.unparse(n)))
            elif isinstance(n, ast.Attribute) and n.attr in data and ast.unparse(n.value) != "self":
                bad.append((where, ast.unparse(n)))
            elif isinstance(n, ast.Attribute) and n.attr == "probe" and "registry" in ast.unparse(n.value):
                bad.append((where, ast.unparse(n)))
            elif isinstance(n, ast.ImportFrom) and (n.module or "").endswith("registry") and any(a.name == "probe" for a in n.names):
                bad.append((where, ast.unparse(n)))
    assert not bad, bad


def test_nothing_under_dev_imports_the_window():
    """The window opens what is under dev and never the reverse, so a dev module loads without the
    player and what both draw is in a module of neither."""
    bad = []
    for path in (PKG / "dev").rglob("*.py"):
        package = ["sieve_player", *path.relative_to(PKG).parts[:-1]]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                base = package[:len(package) - node.level + 1] if node.level else []
                names = [[*base, *(node.module or "").split("."), a.name] for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name.split(".") for a in node.names]
            else:
                continue
            bad += [str(path.relative_to(PKG)) for n in names if [p for p in n if p][:2] == ["sieve_player", "window"]]
    assert not bad, bad


def test_a_reader_of_the_stream_loads_no_graph():
    """A dump replays, and a view is judged, in an interpreter that has loaded no graph, plan or document."""
    code = ("import sys, sieve_player.ledger, sieve_player.catalogue; "
            "print(sorted(m for m in sys.modules if m in {'sieve_player.' + n for n in ('graph', 'plan', 'document')}))")
    out = subprocess.run([sys.executable, "-c", code], cwd=PKG.parent, capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "[]", out.stdout + out.stderr


def test_the_graph_names_no_span_no_node_ran_and_nothing_of_the_selection():
    """A thread's turn, a reader's own work and the player's selection are said by whoever holds the
    Emitter, never through the compute core."""
    named = re.findall(r"(slot|paint|monitor|selected)", (PKG / "graph.py").read_text(encoding="utf-8"))
    assert not named, named


NOT_A_KIND = {      # the words that spell a kind and are another thing's name where a reader writes them
    "catalogue": {"fold", "monitor"},           # a demand; the name the monitor's own slots and paints carry
    "report": {"monitor", "dump"},              # that name again; a dump's path among what a text is handed
}


def test_a_reader_spells_no_kind():
    """A kind is said once, in stream.py: what reads the stream or a ledger's view names a kind by
    the module's value. A string that spells one is another thing's name, of NOT_A_KIND, and is
    never what a kind is compared with."""
    def spelled(node):
        return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in stream.KINDS}

    for name in ("trace", "ledger", "catalogue", "report"):
        tree = ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8"))
        assert spelled(tree) <= NOT_A_KIND.get(name, set()), (name, spelled(tree))
        beside = [ast.unparse(c) for c in ast.walk(tree) if isinstance(c, ast.Compare) and spelled(c)
                  and any(ast.unparse(o).split(".")[-1] == "kind" for o in (c.left, *c.comparators))]
        assert not beside, (name, beside)


TAKES = {"ledger": "_fold", "stats": "event"}       # where each reader of the stream takes an event by its kind
PASSED_OVER = {     # the kinds a reader takes as nothing, by decision; one added to stream.py is taken or is written here
    "ledger": set(),
    # the means are the tool's: a fold is not, nor a turn of the GUI thread's; an error is passed over as it was before
    "stats": {stream.SYNC, stream.WATCH, stream.EVICT, stream.UNCACHE, stream.BEGIN, stream.ERROR, stream.FOLD,
              *stream.TURNS, *stream.OWN, stream.REST, stream.WAKE},
}


def test_a_reader_classifies_every_kind():
    """Where a reader takes an event by its kind, the kinds it compares that with, alone or by a set
    they are in, and the kinds PASSED_OVER says it leaves are every kind once: one added to
    stream.py that a reader neither takes nor is said to pass over is red here, and is taken as
    nothing meanwhile."""
    for name, where in TAKES.items():
        module = importlib.import_module(f"sieve_player.{name}")
        tree = ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8"))
        taken = set()
        for c in ast.walk(next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == where)):
            if isinstance(c, ast.Compare) and ast.unparse(c.left).endswith(".kind"):
                for value in (getattr(module, n.id) for o in c.comparators for n in ast.walk(o) if isinstance(n, ast.Name)):
                    taken |= {value} if isinstance(value, str) else set(value)
        assert not taken & PASSED_OVER[name], (name, taken & PASSED_OVER[name])
        assert taken | PASSED_OVER[name] == set(stream.KINDS), (name, set(stream.KINDS) ^ (taken | PASSED_OVER[name]))


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


TOOLS_MAY_IMPORT = {"decoder", "held", "store", "theme", "wire"}    # the player's modules a tool may name, beside what the package hands out
TOOLS_MAY_TAKE = {"ParamWidget", "play", "document"}        # and the names a tool may take of the package itself


def test_a_tool_reaches_the_player_through_the_modules_named_here():
    """What a tool imports of sieve_player is the player's surface to tools: a module or a name
    not listed is one the player cannot change without a tool breaking, so it is added here first."""
    bad = {}
    for path in TOOLS.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").split(".")[0] == "sieve_player":
                parts = node.module.split(".")
                took = {parts[1]} - TOOLS_MAY_IMPORT if len(parts) > 1 else {a.name for a in node.names} - TOOLS_MAY_TAKE - TOOLS_MAY_IMPORT
            elif isinstance(node, ast.Import):
                took = {a.name for a in node.names if a.name.split(".")[0] == "sieve_player"}
            else:
                continue
            if took:
                bad.setdefault(str(path.relative_to(TOOLS)), set()).update(took)
    assert not bad, bad


def test_a_tool_names_types_of_the_wire_table():
    """What a tool produces or expects, on its first input or one of its INPUTS, and what the video
    node hands out and reads, is a type of wire.TYPES, so a new type is added there first; and
    wire.py, which a tool imports, loads no Qt."""
    from sieve_player import document, registry, wire

    tools = [e.module for e in registry.discover(str(TOOLS)) if e.ok]
    tools += [importlib.import_module(f"tools.retired.{p.stem}") for p in (TOOLS / "retired").glob("*.py") if not p.stem.startswith("_")]
    bad = {}
    for t in tools:
        named = {registry.produces(t), *(registry.expects(t) or ()), *(x for types in registry.inputs(t).values() for x in types)}
        if named - {None, "same", *wire.TYPES}:
            bad[registry.name(t)] = sorted(named - {None, "same", *wire.TYPES})
    assert tools and not bad, bad
    assert {document.PATH, *("gray" if out == "luma" else out for out in document.VIDEO_OUTPUTS)} <= set(wire.TYPES)
    assert "PySide6" not in (PKG / "wire.py").read_text(encoding="utf-8")


UNIT_UNSAID = {"resolve.py": {"tables_of"}}     # where a dtype is made outside _table.py: of a csv read back, which says no column's unit


def test_no_column_is_added_under_tools_with_its_unit_unsaid():
    """A table's dtype is made in tools/_table.py, which takes a unit for every column, and a
    column is added by with_column handed one, wire.NONE being a unit said: under tools/ nothing
    else makes a dtype but what UNIT_UNSAID names, no with_column is short of a unit or handed
    None written out, and _table.py refuses a unit the wire table does not have."""
    import numpy as np
    import pytest

    from tools import _table

    bad = []
    for path in TOOLS.rglob("*.py"):
        where = path.relative_to(TOOLS).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        let = {id(n) for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name in UNIT_UNSAID.get(where, ()) for n in ast.walk(f)}
        for n in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
            made = (isinstance(n.func, ast.Attribute) and n.func.attr == "dtype" and ast.unparse(n.func.value) in ("np", "numpy")) \
                or any(k.arg == "dtype" and isinstance(k.value, ast.List) for k in n.keywords)
            if made and where != "_table.py" and id(n) not in let:
                bad.append((where, ast.unparse(n)))
            if ast.unparse(n.func).split(".")[-1] == "with_column":
                unit = n.args[3] if len(n.args) > 3 else next((k.value for k in n.keywords if k.arg == "unit"), None)
                if unit is None or (isinstance(unit, ast.Constant) and unit.value is None):
                    bad.append((where, ast.unparse(n)))
    assert not bad, bad
    with pytest.raises(ValueError):
        _table.dtype_of([("x", np.int32, "metres")])
    with pytest.raises(ValueError):
        _table.dtype_of([("x", np.int32, None)])


def test_a_tools_computing_is_never_handed_a_param_declared_to_change_nothing():
    """A param declared to change nothing is withheld from the computing, so no result can follow
    it: nowhere in the player is a computing facet called with a node's or an entry's whole params,
    and every tool under tools/ that declares one computes, by run and by step, of the params
    without it. A marked param of a tool that cuts or selects, or that expects a type no row below
    is made of, is red until this seam is extended for it."""
    import numpy as np

    from sieve_player import registry, wire
    from sieve_player.graph import Series
    from tools import blobs, track

    facets = {"run", "step", "key_params", "cut_extents", "cut_file", "cut_files", "select", "matches"}
    whole = [(path.name, ast.unparse(n)) for path in PKG.glob("*.py") for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
             if isinstance(n, ast.Call) and isinstance(n.func, (ast.Attribute, ast.Name)) and ast.unparse(n.func).split(".")[-1] in facets | {"facet"}
             and any(re.search(r"\.params\b", ast.unparse(a)) and "computed(" not in ast.unparse(a) for a in n.args)]
    assert not whole, whole
    chains = [f for name in ("graph", "walk") for f in ast.walk(ast.parse((PKG / f"{name}.py").read_text(encoding="utf-8")))
              if isinstance(f, ast.FunctionDef) and f.name in ("series_chain", "chain_of")]
    assert [f.name for f in chains] == ["chain_of"] and ".params" not in ast.unparse(chains[0])     # what the walk runs and steps a chain node with

    plane = np.zeros((40, 60), np.uint8)
    plane[5:15, 5:20], plane[22:34, 30:50] = 200, 255
    table = blobs.find(plane, 1)
    row_of = {"mask": plane, "gray": plane, "bgr": np.dstack([plane] * 3), "blobs": table, "signal": np.float32(2.0)}
    row_of["tracks"] = track.run(Series([table] * 3, "k", 0, 30.0), registry.computed(track, registry.defaults(track)))["rows"][0]
    for tool in (e.module for e in registry.discover(str(TOOLS)) if e.ok and registry.changes_nothing(e.module)):
        where = registry.name(tool)
        first = next((t for t in registry.expects(tool) or () if t in row_of), None)
        assert first is not None and registry.kind(tool) in ("frame", "series"), where
        assert not registry.cuts(tool) and not registry.is_selector(tool), where
        params = registry.computed(tool, registry.defaults(tool))
        if registry.kind(tool) == "frame":
            tool.run(lambda row, name=None: row_of[first] if name is None
                     else next((row_of[t] for t in registry.inputs(tool)[name] if t in row_of), None), 0, params)
            continue
        fold = registry.fold_of(tool)
        rows = [row_of[first] if fold is None else fold(row_of[first])] * 3
        if wire.is_table(first) and fold is None:
            data = np.empty(3, object)
            for i, r in enumerate(rows):
                data[i] = r
        else:
            data = np.stack(rows)
        tool.run(Series(data, "k", 0, 30.0), params)
        state = None
        for i, r in enumerate(data if registry.steps(tool) else ()):
            state, _ = tool.step(state, r, i, params)


def test_a_settings_widget_is_told_and_says_by_the_registrys_names_alone():
    """The pane and the window find what a settings widget has by name, so a name one side spells
    its own way is never called: every name they look for, and every `set_`, `show_` or signal a
    class under tools/ has, is one of registry.WIDGET_FACETS."""
    from sieve_player.registry import WIDGET_FACETS

    known = {*WIDGET_FACETS, "changed", "set_params"}
    sought = {name for part in ("pane", "window")
              for name in re.findall(r'hasattr\(w, "(\w+)"\)', (PKG / f"{part}.py").read_text(encoding="utf-8"))}
    assert sought == set(WIDGET_FACETS), sought ^ set(WIDGET_FACETS)
    bad = {}
    for path in TOOLS.glob("*.py"):
        for cls in (n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.ClassDef)):
            has = {n.name for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith(("set_", "show_"))}
            has |= {t.id for n in cls.body if isinstance(n, ast.Assign) and "Signal(" in ast.unparse(n.value)
                    for t in n.targets if isinstance(t, ast.Name)}
            if has - known:
                bad[path.name] = sorted(has - known)
    assert not bad, bad


def test_a_utility_imports_neither_the_player_nor_a_tool():
    """A utility runs as its own process on what its command line hands it, so it can be run,
    copied or replaced without the player."""
    def roots(path):
        out = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                out.add(node.module.split(".")[0])
            elif isinstance(node, ast.Import):
                out |= {a.name.split(".")[0] for a in node.names}
        return out

    files = list(UTILITIES.rglob("*.py"))
    assert files
    bad = {str(p.relative_to(UTILITIES)): sorted(m) for p in files if (m := roots(p) & {"sieve_player", "tools"})}
    assert not bad, bad


def test_the_worker_walks_the_clip_with_no_twin_of_a_window_field_or_method():
    """One _Walk serves the window and the clip; a private worker name beside its `_c` or `_clip`
    prefixed twin is the second copy of the walk coming back."""
    tree = jobs_tree()
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

    files = [*PKG.rglob("*.py"), *UTILITIES.rglob("*.py")]
    long = {str(p.relative_to(PKG.parent)): n for p in files if (n := header_lines(p)) > HEADER_LINES}
    assert not long, long


def test_the_scheduler_alone_begins_a_job_and_nothing_compares_a_generation():
    """A job's reset is its begin(), called once per job and only by the ladder: from _turn, or by
    a lane's _Legs in a step its due() hands _turn; an ask is a flag the ladder takes under the
    lock, so no generation counter is compared, by a job or by anyone. A job's due-ness is read in
    one place, _turn, which is both what the loop waits on and what it serves: no job answers
    `pending`, and nothing outside _turn reads an ask or a `due`."""
    tree = jobs_tree()
    turn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_turn")
    legs = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "_Legs")

    def begins(node):
        return [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "begin"]

    assert {id(n) for n in begins(tree)} == {id(n) for n in [*begins(turn), *begins(legs)]}
    assert sorted(ast.unparse(n.func.value) for n in begins(turn)) == ["clip", "self._clip_legs", "self._window_legs", "win"]
    assert [ast.unparse(n.func.value) for n in begins(legs)] == ["w"]
    compared = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Compare)
                and any(isinstance(o, ast.Attribute) and o.attr in ("gen", "asked") for o in [n.left, *n.comparators])]
    assert not compared, compared
    assert not [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "pending"]

    def reads(node):
        return {id(n) for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr in ("asked", "due") and isinstance(n.ctx, ast.Load)}

    assert reads(tree) == reads(turn)


def test_the_worker_reads_the_plan_off_one_snapshot_a_turn():
    """What the plan says is read off the Plan _turn took, never off the graph, whose accessors
    each answer for whatever plan is current as they are called: two of them in one turn are two
    graphs once a sync lands between. What the graph computes or lists for a job it is handed that
    Plan to do under. invalidate() is the GUI thread's, one read."""
    tree = jobs_tree()
    says = {"heads", "chain", "entry", "key", "walk", "fold", "fed", "shown", "over", "series", "source"}
    theirs = {id(n) for f in ast.walk(tree) if isinstance(f, ast.FunctionDef) and f.name == "invalidate" for n in ast.walk(f)}
    read = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in says
            and ast.unparse(n.value) in ("g", "graph", "self.graph") and id(n) not in theirs]
    assert not read, read
    under = {"compute", "density", "drawing", "folded", "walk_row"}     # Graph's methods that take the Plan they answer under
    bare = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in under and not any(ast.unparse(a) in ("p", "self.plan") for a in [*n.args, *(k.value for k in n.keywords)])]
    assert not bare, bare
    takes = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "snapshot"]
    turn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_turn")
    assert {id(n) for n in takes} - {id(n) for n in ast.walk(turn)} == {id(n) for f in ast.walk(tree)
            if isinstance(f, ast.FunctionDef) and f.name == "run_chain" for n in ast.walk(f) if n in takes}


def test_a_job_holds_what_it_reads_and_emits_and_reaches_nothing_through_the_worker():
    """A job is built from the graph, the cadence and the signals it is handed, named, so a test can
    drive one with a graph and a few signals and no QThread: no field or attribute of a job names the
    worker, the chain run is a function over a graph, and a _Walk is
    constructed with every field past the graph named."""
    tree = jobs_tree()
    jobs = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in ("_Scrub", "_Walk")]
    assert len(jobs) == 2
    for job in jobs:
        named = {n.attr for n in ast.walk(job) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self"}
        named |= {n.target.id for n in job.body if isinstance(n, ast.AnnAssign)}
        assert not named & {"w", "worker"}, (job.name, named & {"w", "worker"})
        assert "Worker" not in ast.unparse(job), job.name
    functions = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "run_chain" in functions
    assert "PySide6" not in (PKG / "walk.py").read_text(encoding="utf-8")   # bare.py drives a walk in a process that loads no Qt
    walks = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == "_Walk"]
    assert walks and all(len(n.args) <= 1 for n in walks), [ast.unparse(n) for n in walks]
