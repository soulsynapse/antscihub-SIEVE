"""The end-to-end smoke test.

[INTENT] One test that grows with the vertical slice rather than one test per
phase. Today the slice is "the package installs and its layers import"; as
decode, then a filter, then a worker, then a graph land, this file follows them
end to end. What it checks is meant to change; that there is exactly one of it
is not.
"""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest

# The layer packages named in ARCHITECTURE.md section 3. Importing every one of
# them in a single process is the cheapest available proof that the layer
# contract in .importlinter describes something real: a cycle or a missing
# dependency shows up here as an ImportError rather than at first use.
LAYER_MODULES = [
    "sieve.core",
    "sieve.core.filters",
    "sieve.backends",
    "sieve.io",
    "sieve.pipeline",
    "sieve.workers",
    "sieve.bench",
    "sieve.cli",
    "sieve.gui",
    "sieve.review",
]

# Layers that a headless run reaches. Qt must not arrive as a side effect of
# importing any of them -- that is the guarantee that lets the CLI and an HPC
# job drive the same code the GUI drives. .importlinter checks this statically;
# this checks it at runtime, where a lazy import inside a function body would
# otherwise hide.
HEADLESS_MODULES = [m for m in LAYER_MODULES if m not in {"sieve.gui"}]

QT_BINDINGS = ("PySide6", "PyQt6", "qtpy")


@pytest.mark.parametrize("module_name", LAYER_MODULES)
def test_layer_package_imports(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None


def test_headless_layers_do_not_pull_in_qt() -> None:
    program = (
        "import sys\n"
        + "".join(f"import {name}\n" for name in HEADLESS_MODULES)
        + f"loaded = [b for b in {QT_BINDINGS!r} if b in sys.modules]\n"
        "print(','.join(loaded))\n"
    )
    # A subprocess, because the test session itself may already have imported a
    # Qt binding for other tests. The question is what these modules pull in on
    # their own.
    completed = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        check=True,
    )
    loaded = completed.stdout.strip()
    assert not loaded, f"headless layers imported a Qt binding: {loaded}"
