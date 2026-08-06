"""Guardrail §3, machine-checked: one class, one markdown, no wiring.

Each test here stands for a distinct way discovery stops being real: a filter
that only works because someone imported it by name, a filter that ships with no
guidance or with guidance that answers none of the three questions, a params
model that cannot survive the artifact it is written to, or a params model whose
canonical form is a memory address in disguise.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import sieve.filters
from sieve.core.filter_base import FilterSpec
from sieve.filters import GUIDANCE_SECTIONS, discover, guidance_for, guidance_path
from sieve.filters.downsample import DownsampleParams


def test_discovery_imports_no_filter_module() -> None:
    """The scan, not a list, is what finds filters.

    Parses the package's own source rather than checking that the registry
    ended up populated: a `from sieve.filters import downsample` added here
    would make every other test in this file pass while the guardrail they exist
    for was dead. Only the import list can tell the two apart, and it is read as
    an AST rather than as text so that the prose above it — which has to be
    allowed to name the mistake it is warning about — does not trip the check.
    """
    package = Path(str(sieve.filters.__file__))
    modules = {path.stem for path in package.parent.glob("*.py") if path.stem != "__init__"}
    assert modules, "no filter modules to check discovery against"

    imported: set[str] = set()
    for node in ast.walk(ast.parse(package.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name.rpartition(".")[2] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(alias.name for alias in node.names)
            imported.add((node.module or "").rpartition(".")[2])

    assert not (imported & modules), (
        f"sieve/filters/__init__.py imports filter modules: {sorted(imported & modules)}"
    )
    assert "downsample" in {spec.filter_id for spec in discover()}


def test_every_discovered_filter_has_guidance_markdown() -> None:
    """§3's "one class + one colocated markdown", as an assertion."""
    missing = [spec.key for spec in discover() if not guidance_path(spec).is_file()]
    assert not missing, f"filters with no guidance markdown: {missing}"


def test_every_discovered_filter_declares_a_caption() -> None:
    missing = [spec.key for spec in discover() if not spec.caption]
    assert not missing, f"filters with no presentation caption: {missing}"


def test_every_guidance_file_answers_the_three_questions() -> None:
    """A file that exists but says nothing passes §3 while failing its reader.

    `guidance_for` degrades a missing file to blank sections rather than
    raising, which is right for an out-of-tree filter and wrong for one in this
    package — so the refusal to ship undocumented lives here, where the shelf
    is known, and not in the reader.
    """
    blank = {
        spec.key: [
            name for name, body in zip(GUIDANCE_SECTIONS, _sections(spec), strict=True) if not body
        ]
        for spec in discover()
    }
    empty = {key: names for key, names in blank.items() if names}
    assert not empty, f"guidance sections missing or empty: {empty}"


def _sections(spec: FilterSpec) -> tuple[str, str, str]:
    guidance = guidance_for(spec)
    return guidance.when_to_use, guidance.not_do, guidance.cost


def test_params_round_trip_through_json() -> None:
    """The artifact is JSON, so a params model that cannot survive it is a
    filter that cannot be saved and reloaded — and the failure would land on
    open, long after the run it invalidated."""
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
    stopped ever hitting.
    """
    script = (
        "from sieve.filters.downsample import DownsampleParams;"
        "print(DownsampleParams(factor=4, anti_alias=False).canonical_json())"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == '{"anti_alias":false,"factor":4}'
    assert result.stdout.strip() == DownsampleParams(factor=4, anti_alias=False).canonical_json()
