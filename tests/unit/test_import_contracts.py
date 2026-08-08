"""The downward nevers are held by a contract, and the route around each stays legal.

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

Two claims per edge, and both are read out of the config, which is the whole of
what this file is for: that some `forbidden` contract carries the edge at all,
and that where the row grants a supported route, `allow_indirect_imports`
leaves that route legal. The second is not a red and so has no proof-of-red
shape at all; the first would be, but the generated reds in
`test_contract_lines_go_red.py` walk every `forbidden_modules` entry against
every one of its `source_modules` and so already plant every edge below, and
assert the contract's name against `BROKEN` rather than against a report that
lists every contract. Proving them here too was the same red twice, bought with
a tree copy and a linter subprocess each
(`findings/loop/2026.08.08-a-file-whose-docstring-claims-a-division-of-labour-the-generator-has-outgrown.md`).
`test_no_downward_never_is_proven_red_twice` holds that split, so a fifth edge
added later costs one config-reading case rather than two.

`lint` and `copy_tree` stay here because the generator runs its reds through
them, and the copy is what lets a red land on a line the real tree cannot host.
"""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
import sys
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
#: covers its reds as it covers every other line.
EDGES = (
    Edge("sieve.session", "sieve.tools", reached_through="sieve.pipeline"),
    Edge("sieve.session", "sieve.core.ops", reached_through="sieve.pipeline"),
    Edge("sieve.pipeline", "sieve.core.ops", reached_through="sieve.tools"),
    Edge("sieve.decode", "sieve.core.pipeline_model"),
)

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
