







from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import sieve.filters
from sieve.filters import discover, guidance_path
from sieve.filters.downsample import DownsampleParams


def test_discovery_imports_no_filter_module() -> None:









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

    missing = [spec.key for spec in discover() if not guidance_path(spec).is_file()]
    assert not missing, f"filters with no guidance markdown: {missing}"


def test_params_round_trip_through_json() -> None:



    original = DownsampleParams(factor=4, anti_alias=False)
    restored = DownsampleParams.model_validate_json(original.model_dump_json())

    assert restored == original
    assert restored.canonical_json() == original.canonical_json()


def test_canonical_params_are_stable_across_processes() -> None:








    script = (
        "from sieve.filters.downsample import DownsampleParams;"
        "print(DownsampleParams(factor=4, anti_alias=False).canonical_json())"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == '{"anti_alias":false,"factor":4}'
    assert result.stdout.strip() == DownsampleParams(factor=4, anti_alias=False).canonical_json()
