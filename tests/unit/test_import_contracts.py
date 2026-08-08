"""The downward nevers are held by a contract, and each entry that says so fires.

`.importlinter`'s header calls the file the forbidden edge set of VISION.md's
component table made checkable. A never-clause is refused for free when the
import it names points *upward* through the layers contract, and needs a
bespoke `forbidden` contract only when it points downward — a package refusing
to reach something the layer order allows it to reach. Four clauses are of that
second kind
(`findings/2026.08.08-vision-never-column-has-two-import-shaped-lines-no-contract-checks.md`).
Three are the same refusal at three layers: reaching a tool's array math from
`gui`, `session` or `pipeline` is the second execution path
(`adr/one-execution-path.md`), taken from a layer that owns or asks for the
first. The fourth is `decode` and a schema.

Two claims per edge, and the second is why this file exists rather than a line
in `.importlinter` alone. `src/sieve/core/ops/` does not exist yet
(`adr/ops-admission-is-two-tools.md`), and a forbidden module that names nothing
in the graph is silently inert — `lint-imports` reports success and no setting
says otherwise
(`findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`). So
reading the entry back out of the config would only re-read the line the same
commit wrote. The proof of red is run against a *copy* of the tree in which the
missing package exists and the source module imports it, which is what lets the
red land with the line instead of waiting on ops admission.

The copy is also linted clean before the violation is planted. Without that,
a non-zero exit could be a broken copy — an unparseable config, a package
grimp could not find — and a red for the wrong reason certifies nothing.

These are lines proven by hand, and the copy is the part
`test_contract_lines_go_red.py` inherits: it plants the same package to cover
every other line the file carries. What stays here is the pair of claims that
generator has no shape for — that some forbidden contract holds each edge at
all, and that where a supported route exists `allow_indirect_imports` leaves it
legal, which is not a red.
"""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

import sieve

SRC = Path(str(sieve.__file__)).resolve().parent
REPO = SRC.parents[1]
CONFIG = REPO / ".importlinter"


@dataclass(frozen=True)
class Edge:
    """One downward never, spelt as `.importlinter` spells its two ends."""

    source: str
    forbidden: str
    #: The layer `source` reaches `forbidden` through when it legitimately needs
    #: what is behind it, and which therefore may not itself be forbidden here.
    #: `None` where the row grants no route at all, as `decode`'s does not.
    reached_through: str | None = None

    @property
    def id(self) -> str:
        return f"{self.source}_imports_{self.forbidden}".replace("sieve.", "").replace(".", "_")


#: `gui`'s two are absent: its contract predates this file, and the generator
#: covers its reds as it covers every other line. Each edge below landed
#: alongside the case that proves it.
EDGES = (
    Edge("sieve.session", "sieve.tools", reached_through="sieve.pipeline"),
    Edge("sieve.session", "sieve.core.ops", reached_through="sieve.pipeline"),
    Edge("sieve.pipeline", "sieve.core.ops", reached_through="sieve.tools"),
    Edge("sieve.decode", "sieve.core.pipeline_model"),
)

#: The module each planted violation lives in, named once so the report line the
#: fire case looks for is the one it wrote.
VIOLATION = "_reaches_across"

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
def violating(copied: Path, tmp_path_factory: pytest.TempPathFactory) -> Callable[[Edge], Path]:
    """`copied`, plus any package an ADR defers, plus the import that crosses."""

    def build(edge: Edge) -> Path:
        tree = tmp_path_factory.mktemp("violating")
        shutil.copytree(copied, tree, dirs_exist_ok=True)
        for dotted in (edge.source, edge.forbidden):
            path = tree
            for part in dotted.split("."):
                path = path / part
                if not path.exists():
                    path.mkdir()
                    (path / "__init__.py").write_bytes(b"")
        crossing = tree.joinpath(*edge.source.split(".")) / f"{VIOLATION}.py"
        crossing.write_text(f"import {edge.forbidden}\n", encoding="utf-8")
        return tree

    return build


@pytest.mark.parametrize("edge", EDGES, ids=[edge.id for edge in EDGES])
def test_a_forbidden_contract_carries_the_edge(edge: Edge) -> None:
    section = _forbidding_edge(edge.source, edge.forbidden)

    assert section is not None, (
        f"no forbidden contract in {CONFIG.name} has {edge.source!r} among its sources "
        f"and {edge.forbidden!r} among its forbidden modules"
    )


ROUTED = tuple(edge for edge in EDGES if edge.reached_through)


@pytest.mark.parametrize("edge", ROUTED, ids=[edge.id for edge in ROUTED])
def test_the_supported_path_stays_legal(edge: Edge) -> None:
    """Asking the layer below for a run is the one execution path, not a red.

    What each entry forbids is the source layer *holding* the computation,
    which is only ever a direct import, and `allow_indirect_imports` is where
    that distinction is drawn.
    """
    section = _forbidding_edge(edge.source, edge.forbidden)
    assert section is not None

    assert section.getboolean("allow_indirect_imports") is True
    assert edge.reached_through not in modules(section, "forbidden_modules")


def test_the_copied_tree_lints_clean(copied: Path) -> None:
    """The control: red in the next test is the planted edge and not the copy."""
    result = lint(copied)

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("edge", EDGES, ids=[edge.id for edge in EDGES])
def test_the_entry_fires(violating: Callable[[Edge], Path], edge: Edge) -> None:
    section = _forbidding_edge(edge.source, edge.forbidden)
    assert section is not None

    result = lint(violating(edge))

    assert result.returncode != 0, result.stdout + result.stderr
    assert section["name"] in result.stdout, result.stdout + result.stderr
    assert f"{edge.source}.{VIOLATION} -> {edge.forbidden}" in result.stdout
