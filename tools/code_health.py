"""A report on the shape of the codebase. Signals worth a second look, not a gate.

[INTENT] Gates answer "is this allowed?" and are already covered -- Ruff for
style, Pyright for types, import-linter for the layer contract. This answers a
different question: "what has grown in a direction nobody decided?" A module
that doubled in size, a helper that half the tree now depends on, a test that
grew six patches -- none of those are violations, and all of them are worth
seeing before they become the reason a refactor is expensive.

It therefore exits zero on every finding. A report that can fail becomes a
gate, a gate accumulates suppressions, and suppressed signals are the thing
this is trying to surface. It exits non-zero only when it cannot do its job:
an unparseable file means the report is silently incomplete, which is worse
than no report.

[ASSUMPTION] The thresholds below are guesses. They are stated as constants
with their reasoning rather than buried, because the useful values are not
knowable before the tree has enough code to have a distribution. Tune them
against what they actually surface; a threshold nobody has ever tuned is a
threshold nobody reads the output of.

Stdlib only, and deliberately outside `src/`. This analyzes the package; it is
not part of it, and shipping a repo-shape analyzer inside the wheel would make
`sieve` depend on its own source layout.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import tomllib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "sieve"
TESTS = ROOT / "tests"
PYPROJECT = ROOT / "pyproject.toml"

# The layer model from ARCHITECTURE.md section 3, top to bottom. Depth is what
# makes "reaches past its neighbours" measurable: import-linter enforces the
# direction, and nothing enforces the distance, because distance is a design
# smell rather than a violation.
LAYER_DEPTH = {
    "gui": 0,
    "cli": 0,
    "review": 0,
    "bench": 1,
    "workers": 2,
    "pipeline": 3,
    "backends": 4,
    "io": 4,
    "core": 5,
}

# A module past this is not wrong, but it is past the size at which one file
# holds one responsibility -- the placement rule ARCHITECTURE.md section 14
# states. Set where the existing benchmark harness lands above it, because that
# file is a genuine instance of the thing worth flagging.
LARGE_MODULE_LOC = 400

# Fan-in past this makes a module a de facto interface whether or not it was
# designed as one, which is the point at which changing it stops being cheap.
HIGH_FAN_IN = 5

# Fan-out past this is a module that knows about a lot of the tree. Often a
# coordinator, which is fine; occasionally a module that grew responsibilities.
HIGH_FAN_OUT = 8

# A test asserting more than this is usually several tests, and reports the
# first failure only -- the others stay hidden until the first is fixed.
MANY_ASSERTS = 8

# Patching is how a test couples to an implementation rather than to a
# contract. A few are normal; a pile of them means the test breaks on refactors
# that change nothing observable.
MANY_PATCHES = 3

SLEEP_CALLS = {"sleep", "wait", "processEvents"}

# `sieve.<layer>.<module>` is a layer's own surface. Anything longer that is
# imported from a different layer has reached past what that layer published.
LAYER_SURFACE_DEPTH = 3


@dataclass
class ModuleFacts:
    dotted: str
    path: Path
    layer: str | None
    loc: int
    internal_imports: set[str] = field(default_factory=set)
    max_layer_reach: int = 0
    deep_imports: list[str] = field(default_factory=list)
    suppressions: list[str] = field(default_factory=list)


@dataclass
class TestFacts:
    path: Path
    name: str
    line: int
    asserts: int
    patches: int
    sleeps: int


def _layer_of(dotted: str) -> str | None:
    parts = dotted.split(".")
    return parts[1] if len(parts) > 1 and parts[1] in LAYER_DEPTH else None


def _dotted_name(path: Path, root: Path, prefix: str) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = [part for part in relative.parts if part != "__init__"]
    return ".".join([prefix, *parts]) if parts else prefix


def _imported_modules(tree: ast.AST) -> set[str]:
    """Absolute dotted names of every import in the file.

    Relative imports are skipped rather than resolved. Resolving them correctly
    needs the importing module's own package context, and getting it subtly
    wrong would put a module in the wrong layer -- a wrong signal is worse than
    a missing one in a report meant to be trusted without verification.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
    return found


def _suppressions(source: str) -> list[str]:
    marks: list[str] = []
    for number, line in enumerate(source.splitlines(), start=1):
        for token in ("# type: ignore", "# noqa", "# pyright: ignore", "# pragma: no cover"):
            if token in line:
                marks.append(f"{number}: {token}")
    return marks


def _collect_modules() -> tuple[list[ModuleFacts], list[str]]:
    modules: list[ModuleFacts] = []
    errors: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        dotted = _dotted_name(path, PACKAGE, "sieve")
        layer = _layer_of(dotted)
        facts = ModuleFacts(
            dotted=dotted,
            path=path,
            layer=layer,
            # Blank lines and comment-only lines are excluded. This codebase
            # writes long explanatory comments on purpose, and counting them as
            # size would flag exactly the files that are the best documented.
            loc=sum(
                1
                for line in source.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ),
            suppressions=_suppressions(source),
        )
        own_depth = LAYER_DEPTH.get(layer or "", -1)
        for imported in _imported_modules(tree):
            if not imported.startswith("sieve"):
                continue
            facts.internal_imports.add(imported)
            target_layer = _layer_of(imported)
            if target_layer is None or own_depth < 0:
                continue
            reach = LAYER_DEPTH[target_layer] - own_depth
            facts.max_layer_reach = max(facts.max_layer_reach, reach)
            # sieve.core.filters.motion.flow, imported from pipeline/, reaches
            # past core/'s own surface into a module core/ did not publish.
            if len(imported.split(".")) > LAYER_SURFACE_DEPTH and target_layer != layer:
                facts.deep_imports.append(imported)
        modules.append(facts)
    return modules, errors


def _collect_tests() -> tuple[list[TestFacts], list[str]]:
    tests: list[TestFacts] = []
    errors: list[str] = []
    for path in sorted(TESTS.rglob("test_*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not node.name.startswith("test_"):
                continue
            asserts = patches = sleeps = 0
            for inner in ast.walk(node):
                if isinstance(inner, ast.Assert):
                    asserts += 1
                elif isinstance(inner, ast.Call):
                    label = ast.unparse(inner.func) if hasattr(ast, "unparse") else ""
                    tail = label.rsplit(".", 1)[-1]
                    if "patch" in label or "MagicMock" in label or "Mock" in label:
                        patches += 1
                    if tail in SLEEP_CALLS:
                        sleeps += 1
            tests.append(
                TestFacts(
                    path=path,
                    name=node.name,
                    line=node.lineno,
                    asserts=asserts,
                    patches=patches,
                    sleeps=sleeps,
                )
            )
    return tests, errors


def _config_exemptions() -> list[str]:
    """Files a gate has been told to skip, read from `pyproject.toml`.

    An inline `# noqa` is visible to anyone reading the line it sits on. A
    per-file ignore is visible only to someone who opens the config, so the
    file itself looks clean while a rule is switched off across all of it.
    That asymmetry is why these are counted alongside inline suppressions
    rather than trusted to be remembered -- `NOTES.md` currently tracks them by
    hand, which works until it is someone else's turn to notice.
    """
    if not PYPROJECT.is_file():
        return []
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    tools = config.get("tool", {})
    entries = [
        f"Ruff exempts `{pattern}` from {', '.join(rules)}"
        for pattern, rules in tools.get("ruff", {})
        .get("lint", {})
        .get("per-file-ignores", {})
        .items()
    ]
    entries += [
        f"Pyright ignores `{pattern}`" for pattern in tools.get("pyright", {}).get("ignore", [])
    ]
    return entries


def _fan(modules: list[ModuleFacts]) -> tuple[dict[str, int], dict[str, int]]:
    """Fan-out is imports made; fan-in is imports received, package-rolled-up.

    An import of `sieve.core.filters.blur` counts toward `sieve.core.filters`
    and `sieve.core` too, because a change to a package's surface is felt by
    everyone reaching anywhere inside it.
    """
    fan_out = {module.dotted: len(module.internal_imports) for module in modules}
    fan_in: dict[str, int] = defaultdict(int)
    known = {module.dotted for module in modules}
    for module in modules:
        for imported in module.internal_imports:
            parts = imported.split(".")
            for size in range(1, len(parts) + 1):
                candidate = ".".join(parts[:size])
                if candidate in known and candidate != module.dotted:
                    fan_in[candidate] += 1
    return fan_out, dict(fan_in)


def _findings(modules: list[ModuleFacts], tests: list[TestFacts]) -> dict[str, list[str]]:
    fan_out, fan_in = _fan(modules)
    findings: dict[str, list[str]] = {}

    findings["Large modules"] = [
        f"`{m.dotted}` -- {m.loc} lines (over {LARGE_MODULE_LOC})"
        for m in sorted(modules, key=lambda m: -m.loc)
        if m.loc > LARGE_MODULE_LOC
    ]
    findings["High fan-in (de facto interfaces)"] = [
        f"`{name}` -- imported by {count} modules (over {HIGH_FAN_IN})"
        for name, count in sorted(fan_in.items(), key=lambda item: -item[1])
        if count > HIGH_FAN_IN
    ]
    findings["High fan-out (knows a lot of the tree)"] = [
        f"`{name}` -- imports {count} internal modules (over {HIGH_FAN_OUT})"
        for name, count in sorted(fan_out.items(), key=lambda item: -item[1])
        if count > HIGH_FAN_OUT
    ]
    findings["Deep cross-layer reach"] = [
        f"`{m.dotted}` -- reaches into {imported}"
        for m in modules
        for imported in sorted(set(m.deep_imports))
    ]
    findings["Suppressions"] = _config_exemptions() + [
        f"`{m.path.relative_to(ROOT).as_posix()}` -- {mark}"
        for m in modules
        for mark in m.suppressions
    ]
    findings["Tests worth a second look"] = [
        f"`{t.path.relative_to(ROOT).as_posix()}::{t.name}` (line {t.line}) -- "
        + ", ".join(
            part
            for part in (
                f"{t.asserts} asserts" if t.asserts > MANY_ASSERTS else "",
                f"{t.patches} patches/mocks" if t.patches > MANY_PATCHES else "",
                f"{t.sleeps} sleep/wait calls" if t.sleeps else "",
            )
            if part
        )
        for t in tests
        if t.asserts > MANY_ASSERTS or t.patches > MANY_PATCHES or t.sleeps
    ]
    return findings


def _render(modules: list[ModuleFacts], tests: list[TestFacts]) -> str:
    findings = _findings(modules, tests)
    total_loc = sum(module.loc for module in modules)
    by_layer: dict[str, int] = defaultdict(int)
    for module in modules:
        by_layer[module.layer or "(top level)"] += module.loc

    lines = [
        "# Code health",
        "",
        "Signals worth a second look. Nothing here is a failure; the gates are "
        "`nox -s checks`. Thresholds are stated in `tools/code_health.py` with "
        "their reasoning and are expected to be tuned against what they surface.",
        "",
        f"{len(modules)} modules, {total_loc} lines of code, {len(tests)} tests.",
        "",
        "| Layer | Lines |",
        "| --- | ---: |",
    ]
    lines += [
        f"| {layer} | {loc} |"
        for layer, loc in sorted(by_layer.items(), key=lambda item: -item[1])
        if loc
    ]
    for heading, entries in findings.items():
        lines += ["", f"## {heading}", ""]
        lines += [f"- {entry}" for entry in entries] or ["Nothing flagged."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--output", type=Path, help="write the report to a file as well as stdout")
    args = parser.parse_args(argv)

    modules, module_errors = _collect_modules()
    tests, test_errors = _collect_tests()
    errors = module_errors + test_errors

    if args.json:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "module_count": len(modules),
            "total_loc": sum(module.loc for module in modules),
            "test_count": len(tests),
            "findings": _findings(modules, tests),
            "parse_errors": errors,
        }
        report = json.dumps(payload, indent=2)
    else:
        report = _render(modules, tests)

    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")

    # The one failure mode. A file this cannot parse is a file it silently
    # excluded, and a report that quietly covers less than it claims is the
    # thing that makes a report untrustworthy.
    for error in errors:
        print(f"error: could not parse {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
