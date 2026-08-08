"""`pipeline` must not reach into `core/ops/`, and the entry that says so fires.

`.importlinter`'s header calls the file the forbidden edge set of VISION.md's
component table made checkable, and this is the one import-shaped `Never` in
that table with no contract behind it until now: `core` sits below `pipeline`,
so `pipeline -> core.ops` points downward and is legal under the layers
contract, exactly the hole `gui-computes-nothing` exists to close one row up.
Reaching a tool's array math from the executor is the second execution path
(`adr/one-execution-path.md`), taken from the layer that owns the first.

Two claims, and the second is why this file exists rather than a line in
`.importlinter` alone. `src/sieve/core/ops/` does not exist yet
(`adr/ops-admission-is-two-tools.md`), and a forbidden module that names
nothing in the graph is silently inert — `lint-imports` reports success and no
setting says otherwise
(`findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`). So
reading the entry back out of the config would only re-read the line the same
commit wrote. The proof of red is run against a *copy* of the tree in which
`ops/` exists and a `sieve.pipeline` module imports it, which is what lets the
red land with the line instead of waiting on ops admission.

The copy is also linted clean before the violation is planted. Without that,
a non-zero exit could be a broken copy — an unparseable config, a package
grimp could not find — and a red for the wrong reason certifies nothing.

This is one line proven by hand, and the copy is the part
`test_contract_lines_go_red.py` inherits: it plants the same package to cover
every other line the file carries. What stays here is the pair of claims that
generator has no shape for — that some forbidden contract holds this edge at
all, and that `allow_indirect_imports` leaves `pipeline -> tools -> ops` legal,
which is not a red.
"""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import sieve

SRC = Path(str(sieve.__file__)).resolve().parent
REPO = SRC.parents[1]
CONFIG = REPO / ".importlinter"

#: The edge, spelt as `.importlinter` spells its two ends.
SOURCE = "sieve.pipeline"
FORBIDDEN = "sieve.core.ops"

#: Run the linter in-process in a child rather than through the `lint-imports`
#: console script: the script's location differs by platform and by installer,
#: and `lint_imports` is the same function the script calls. `no_cache` because
#: each copy is a fresh tree at the same path family and a cache hit would
#: answer for the wrong one.
_LINT = (
    "import sys; from importlinter.cli import lint_imports; sys.exit(lint_imports(no_cache=True))"
)


def modules(section: configparser.SectionProxy, key: str) -> list[str]:
    """The multi-line value at `key`, minus blanks and comment lines."""
    return [
        line.strip()
        for line in section.get(key, "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def contracts() -> dict[str, configparser.SectionProxy]:
    parsed = configparser.ConfigParser()
    parsed.read(CONFIG, encoding="utf-8")
    return {
        name: parsed[name]
        for name in parsed.sections()
        if name.startswith("importlinter:contract:")
    }


def _forbidding_edge(source: str, forbidden: str) -> configparser.SectionProxy | None:
    for section in contracts().values():
        if section.get("type") != "forbidden":
            continue
        if source in modules(section, "source_modules") and forbidden in modules(
            section, "forbidden_modules"
        ):
            return section
    return None


def lint(tree: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _LINT],
        cwd=tree,
        # A non-zero exit is the result under test, not an error.
        check=False,
        capture_output=True,
        text=True,
        # The report is drawn with box characters, which the console's cp1252
        # default cannot decode — the reader thread dies mid-report and the
        # test reads an exit code with no output behind it.
        encoding="utf-8",
        errors="replace",
        # The renderer wraps to the terminal width, and a contract name broken
        # across two lines would fail a substring check for a cosmetic reason.
        env={**os.environ, "COLUMNS": "200"},
    )


def copy_tree(tree: Path) -> Path:
    """The tree as `lint-imports` sees it: the package beside its config.

    Copied to the cwd as a top-level `sieve/` because `lint_imports` puts the
    working directory on `sys.path` and nothing else — the editable install
    that makes `src/sieve` importable here is not what is being tested.
    """
    shutil.copytree(SRC, tree / "sieve", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(CONFIG, tree / ".importlinter")
    return tree


@pytest.fixture(scope="module")
def copied(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return copy_tree(tmp_path_factory.mktemp("linted"))


@pytest.fixture(scope="module")
def violating(copied: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """`copied`, plus the package ADR-defers and the import that reaches it."""
    tree = tmp_path_factory.mktemp("violating")
    shutil.copytree(copied, tree, dirs_exist_ok=True)
    (tree / "sieve" / "core" / "ops").mkdir()
    (tree / "sieve" / "core" / "ops" / "__init__.py").write_text(
        "def absdiff(): ...\n", encoding="utf-8"
    )
    (tree / "sieve" / "pipeline" / "_reaches_into_ops.py").write_text(
        "import sieve.core.ops\n", encoding="utf-8"
    )
    return tree


def test_a_forbidden_contract_carries_the_edge() -> None:
    section = _forbidding_edge(SOURCE, FORBIDDEN)

    assert section is not None, (
        f"no forbidden contract in {CONFIG.name} has {SOURCE!r} among its sources "
        f"and {FORBIDDEN!r} among its forbidden modules"
    )


def test_the_supported_path_stays_legal() -> None:
    """`pipeline -> tools -> ops` is the one execution path, reached from above.

    What the entry forbids is `pipeline/` *holding* array math, which is only
    ever a direct import — the same distinction `gui-computes-nothing` draws,
    and `allow_indirect_imports` is where it is drawn.
    """
    section = _forbidding_edge(SOURCE, FORBIDDEN)
    assert section is not None

    assert section.getboolean("allow_indirect_imports") is True
    assert "sieve.tools" not in modules(section, "forbidden_modules")


def test_the_copied_tree_lints_clean(copied: Path) -> None:
    """The control: red in the next test is the planted edge and not the copy."""
    result = lint(copied)

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_entry_fires_where_ops_exists(violating: Path) -> None:
    section = _forbidding_edge(SOURCE, FORBIDDEN)
    assert section is not None

    result = lint(violating)

    assert result.returncode != 0, result.stdout + result.stderr
    assert section["name"] in result.stdout, result.stdout + result.stderr
    assert "sieve.pipeline._reaches_into_ops -> sieve.core.ops" in result.stdout
