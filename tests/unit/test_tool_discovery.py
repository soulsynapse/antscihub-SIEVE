"""Discovery is a scan, and a params model is what a cache key is made of.

Each test here stands for a distinct way one of those stops being true: a tool
that only works because someone imported it by name, a tool with nothing to show
for itself in a collapsed node, a params model that cannot survive the artifact
it is written to, or a params model whose canonical form is a memory address in
disguise.

Ported from v2's `tests/unit/test_filter_discovery.py`, minus its two
guidance-markdown cases: v3 has no per-tool document to check.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import sieve.tools
from sieve.tools import discover
from sieve.tools.downsample import DownsampleParams


def test_discovery_imports_no_tool_module() -> None:
    """The scan, not a list, is what finds tools.

    Parses the package's own source rather than checking that the registry ended
    up populated: a `from sieve.tools import downsample` added here would make
    every other test in this file pass while the guardrail they exist for was
    dead. Only the import list can tell the two apart, and it is read as an AST
    rather than as text so that the prose above it — which has to be allowed to
    name the mistake it is warning about — does not trip the check.

    That the scan then finds anything is the *next* test's claim, and it cannot
    be this one's: this module imports `DownsampleParams` at file scope as a
    fixture, so the registry is stocked here whatever `discover()` does.
    """
    package = Path(str(sieve.tools.__file__))
    modules = {path.stem for path in package.parent.glob("*.py") if path.stem != "__init__"}
    assert modules, "no tool modules to check discovery against"

    imported: set[str] = set()
    for node in ast.walk(ast.parse(package.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name.rpartition(".")[2] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(alias.name for alias in node.names)
            imported.add((node.module or "").rpartition(".")[2])

    assert not (imported & modules), (
        f"sieve/tools/__init__.py imports tool modules: {sorted(imported & modules)}"
    )


def test_the_scan_stocks_a_shelf_no_one_else_touched() -> None:
    """`discover()` has to be the thing that puts a tool on the shelf.

    In a fresh interpreter, because inside this one it cannot be shown: the
    fixture import at the top of this file registers `downsample` before any
    test runs, so a `discover()` whose body did nothing but return `REGISTRY`
    would still satisfy an in-process assertion — it did, for the whole of
    a686d13, and the mutant printed `()` outside pytest. The subprocess is the
    only place the two routes to a populated registry come apart.

    Asserts containment rather than equality so that the second tool to land
    does not fail this; the claim is that the scan found one nobody named, not
    that it found exactly one.
    """
    script = "from sieve.tools import discover;print(sorted(s.tool_id for s in discover()))"
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )

    assert "downsample" in ast.literal_eval(result.stdout.strip())


def test_every_discovered_tool_declares_a_caption() -> None:
    """A collapsed node has to say something about how it is configured.

    Either declaration satisfies this, because `caption_for_params` reads both:
    an explicit `caption` when the parts need labels or literal text, and
    `primary_params` when the bare values are the whole caption. A tool
    declaring neither renders as an empty string in a collapsed node — the one
    place a user is told what a node is set to.
    """
    missing = [spec.key for spec in discover() if not (spec.caption or spec.primary_params)]
    assert not missing, f"tools with no presentation caption: {missing}"


def test_params_round_trip_through_json() -> None:
    """The artifact is JSON, so a params model that cannot survive it is a tool
    that cannot be saved and reloaded — and the failure would land on open, long
    after the run it invalidated."""
    original = DownsampleParams(factor=4, anti_alias=False)
    restored = DownsampleParams.model_validate_json(original.model_dump_json())

    assert restored == original
    assert restored.canonical_json() == original.canonical_json()


def test_canonical_params_are_stable_across_processes() -> None:
    """The cache key input has to mean the same thing tomorrow.

    Run in a subprocess and not merely twice in this one: `hash()` on a str is
    salted per process and `id()` differs per allocation, so an accidental use
    of either is invisible to any test that stays inside one interpreter. This
    is the only check in the suite that would catch it before a cache silently
    stopped ever hitting, which is why it is not folded into the in-process
    canonical-form assertions in `test_tool_contract.py`.
    """
    script = (
        "from sieve.tools.downsample import DownsampleParams;"
        "print(DownsampleParams(factor=4, anti_alias=False).canonical_json())"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == '{"anti_alias":false,"factor":4}'
    assert result.stdout.strip() == DownsampleParams(factor=4, anti_alias=False).canonical_json()
