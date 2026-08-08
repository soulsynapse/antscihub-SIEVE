"""Every line `.importlinter` carries can fail, one planted violation per line.

The gate that landed the contracts added one violating edge per contract and
watched each go red
(`findings/2026.08.06-every-contract-goes-red-on-one-line.md`). That proves
each contract is wired to the linter and says nothing about the other lines in
it — and the one line not probed was the only one that could not have fired,
because a forbidden module naming nothing in the graph is inert and reports
success (`findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`,
`findings/loop/2026.08.06-one-red-per-contract-certifies-the-contract-not-its-lines.md`).

So the cases here are read out of `.importlinter` rather than listed: every
`forbidden_modules` entry against every one of its `source_modules`, every
adjacent pair of `layers` rows in the illegal direction, and every ordered pair
of siblings inside a row, which `|` declares independent. A line added later is
covered the day it lands rather than the day someone remembers.

Each violation is planted in a *copy* of the tree, which is what lets a
generated case cover a line the real tree cannot host: `sieve.core.ops` is
forbidden before ADR `ops-admission-is-two-tools` admits it, and the copy
simply has the package
(`findings/2026.08.07-an-inert-forbidden-entry-can-be-proven-red-against-a-copy.md`).
The copy is linted clean first, because a non-zero exit from a broken copy —
an unparseable config, a package grimp could not find — certifies nothing.

Three ways this could go quietly stale, each closed by a test rather than by a
branch in the generator: a contract of a type with no case shape here, a
contract that contributes no cases at all because a key was renamed under it,
and a fold that drops part of a contract's cases while leaving it non-empty.
The reds cannot see the third — a case never built never fails — so it is
counted instead, by an arithmetic over the same config that the generator
walks.
"""

from __future__ import annotations

import itertools
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.unit.test_import_contracts import CONFIG, contracts, copy_tree, lint, modules

#: The planted module, one name reused and deleted after every case, so no red
#: can be read as belonging to the case that ran before it.
VIOLATION = "_violation"

#: A `layers` row this generator knows the reds of: independent siblings, spelt
#: plainly. import-linter also accepts `?` for an optional layer and `:` for
#: siblings that may import each other, whose violation sets are not the ones
#: planted below — refused rather than guessed, so the day a row uses one,
#: someone decides what red it owes instead of the file silently under-covering.
MEMBER = re.compile(r"[A-Za-z_][\w.]*")

#: The contract types with a case shape here. `test_every_contract_type_...`
#: is what makes this list binding rather than decorative.
GENERATED = ("forbidden", "layers")

#: The one forbidden module the real tree does not host, and so the case that
#: makes the copy grow a package (`adr/ops-admission-is-two-tools.md`).
PLANTED_PACKAGE = "sieve.core.ops"


@dataclass(frozen=True)
class Case:
    """One line of one contract, as the import that must break it."""

    contract: str
    importer: str
    imported: str
    #: The section suffix, carried for the node id alone. Two contracts can
    #: forbid the same edge — `sieve.core` importing `cv2` is both `core-purity`
    #: and `opencv-containment` — and `-k core-purity` selects the one meant,
    #: which the contract's sentence-long `name` would not.
    key: str

    @property
    def id(self) -> str:
        return f"{self.key}__{self.importer}_imports_{self.imported}".replace(".", "_")


def layer_rows(lines: list[str]) -> list[list[str]]:
    """The `layers` value as rows of independent siblings, top row first."""
    rows = []
    for line in lines:
        members = [member.strip() for member in line.split("|")]
        for member in members:
            if not MEMBER.fullmatch(member):
                raise ValueError(
                    f"layer row {line!r} is not independent siblings spelt plainly; "
                    f"{member!r} carries syntax whose violations this file does not generate"
                )
        rows.append(members)
    return rows


def _cases() -> list[Case]:
    cases: list[Case] = []
    for section_name, section in contracts().items():
        key = section_name.rsplit(":", 1)[-1]
        name = section["name"]
        if section.get("type") == "forbidden":
            for importer, imported in itertools.product(
                modules(section, "source_modules"), modules(section, "forbidden_modules")
            ):
                cases.append(Case(name, importer, imported, key))
        elif section.get("type") == "layers":
            rows = layer_rows(modules(section, "layers"))
            # Upward: the lower row importing the higher one is the illegal
            # direction, and the legal one is what the tree already does.
            for higher, lower in itertools.pairwise(rows):
                for imported, importer in itertools.product(higher, lower):
                    cases.append(Case(name, importer, imported, key))
            for row in rows:
                for importer, imported in itertools.permutations(row, 2):
                    cases.append(Case(name, importer, imported, key))
    return cases


CASES = _cases()


def _owed() -> int:
    """The cases the config is owed, multiplied out rather than walked.

    Deliberately a second expression of the same rule, which is the only way a
    generator gets a subject: a wrong case cannot hide — a legal edge lints
    clean and fails its own red — so the failure left is a case that was never
    built, and nothing that iterates the config alongside `_cases` would notice
    the same fold twice. Spelt without `pairwise` or `product` for that reason.
    """
    owed = 0
    for section in contracts().values():
        if section.get("type") == "forbidden":
            owed += len(modules(section, "source_modules")) * len(
                modules(section, "forbidden_modules")
            )
        elif section.get("type") == "layers":
            rows = layer_rows(modules(section, "layers"))
            owed += sum(len(rows[i]) * len(rows[i + 1]) for i in range(len(rows) - 1))
            owed += sum(len(row) * (len(row) - 1) for row in rows)
    return owed


def _ensure_package(tree: Path, dotted: str) -> Path | None:
    """`dotted` as a package in the copy; the topmost directory made, if any."""
    created = None
    path = tree
    for part in dotted.split("."):
        path = path / part
        if not path.exists():
            created = created or path
            path.mkdir()
            (path / "__init__.py").write_bytes(b"")
    return created


def _lint_with(tree: Path, case: Case) -> subprocess.CompletedProcess[str]:
    """`tree` linted with `case` planted in it, and the tree left as it was."""
    created = [
        _ensure_package(tree, module)
        for module in (case.importer, case.imported)
        if module.startswith("sieve.")
    ]
    violation = tree.joinpath(*case.importer.split(".")) / f"{VIOLATION}.py"
    violation.write_text(f"import {case.imported}\n", encoding="utf-8")
    try:
        return lint(tree)
    finally:
        violation.unlink()
        for path in created:
            if path is not None:
                shutil.rmtree(path)


@pytest.fixture(scope="module")
def tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return copy_tree(tmp_path_factory.mktemp("lines"))


def test_every_contract_type_is_one_this_file_generates() -> None:
    """A contract of an unhandled type would contribute nothing and say nothing."""
    types = {section.get("type") for section in contracts().values()}

    assert types <= set(GENERATED), (
        f"{types - set(GENERATED)} in {CONFIG.name} have no case shape here, so their "
        f"lines are uncovered and the generator reports that as full coverage"
    )


def test_every_contract_contributes_at_least_one_case() -> None:
    """A key renamed under a contract empties it silently; nothing else would tell."""
    named = {section["name"] for section in contracts().values()}

    assert {case.contract for case in CASES} == named


def test_every_line_contributes_every_case_it_owes() -> None:
    """A contract can lose cases without losing all of them, and stay green."""
    assert len(CASES) == _owed()


@pytest.mark.parametrize(
    ("row", "refused"),
    [
        ("sieve.a | sieve.b", False),
        ("sieve.a : sieve.b", True),
        ("(sieve.a)", True),
        ("sieve.a?", True),
    ],
)
def test_a_row_this_file_cannot_generate_is_refused(row: str, refused: bool) -> None:
    if not refused:
        assert layer_rows([row]) == [["sieve.a", "sieve.b"]]
        return
    with pytest.raises(ValueError, match="does not generate"):
        layer_rows([row])


def test_the_copied_tree_lints_clean(tree: Path) -> None:
    """The control: every red below is the planted edge and not the copy."""
    result = lint(tree)

    assert result.returncode == 0, result.stdout + result.stderr


def test_a_case_leaves_the_tree_as_it_found_it(tree: Path) -> None:
    """One copy serves every case, so what a case plants has to leave with it.

    The package is the sharper half: `sieve.core.ops` outliving its case would
    make an entry that is inert in the real tree enforceable for every case
    after it, and each of those would then be red for a reason its own line did
    not earn.
    """
    planting = [case for case in CASES if case.imported == PLANTED_PACKAGE]
    assert planting, f"no case plants {PLANTED_PACKAGE}, so nothing here tests the cleanup"
    before = sorted(path.relative_to(tree) for path in tree.rglob("*"))

    _lint_with(tree, planting[0])

    # The paths and not the verdict: a leftover import and a leftover package
    # each lint clean alone, and only their pair is a red, so a tree that still
    # lints clean is no evidence that either one left.
    assert sorted(path.relative_to(tree) for path in tree.rglob("*")) == before


@pytest.mark.parametrize("case", CASES, ids=[case.id for case in CASES])
def test_the_line_goes_red(tree: Path, case: Case) -> None:
    result = _lint_with(tree, case)
    report = result.stdout + result.stderr

    assert result.returncode != 0, report
    assert f"{case.contract} BROKEN" in result.stdout, report
    assert f"{case.importer}.{VIOLATION} -> {case.imported}" in result.stdout, report
