"""Every `source_modules` entry answers to a row of VISION's component table.

`.importlinter` opens by calling itself "the forbidden edge set of VISION.md's
component table, made checkable", which quantifies over the whole file in both
directions. The table-to-config direction has been walked three times by hand;
this is the other one, and it is the tractable half — a `source_modules` entry
is a literal module name, so what a walk of it needs is only a way to say which
phrase of a `Never` cell carries a given module.

That is `CELL_PHRASES`, and it lives here rather than in the table because the
table is prose a reader arrives at and a parser cannot classify
(`findings/2026.08.08-vision-never-column-has-two-import-shaped-lines-no-contract-checks.md`,
`open_questions`). Keeping it here buys the gate the walks lacked: a forbidden
module with no entry fails rather than passing unnoticed, so a new one cannot
land without someone naming the words its rows have to use.

Three hand walks each closed the divergence they could see and left the
contracts they did not have open
(`findings/loop/2026.08.07-a-universal-claim-over-an-inherited-list-is-supported-by-the-only-two-members-quoted.md`).
The denominator is what stops that: the cases below are read out of the config,
so a source line added later is walked the day it lands.

The other direction stays prose. A `Never` clause is import-shaped or an ADR
gate, and telling those apart is the classification both walks got wrong — so
green here says every contract answers to a cell, and says nothing about a cell
answering to a contract.
"""

from __future__ import annotations

import re

import pytest
from doc_index import COMPONENT_HEADING, _spoken

from tests.unit.test_import_contracts import REPO, contracts, modules

VISION = REPO / "docs" / "VISION.md"

#: All three columns, unlike `doc_index.COMPONENT_ROW`, which reads the second.
ROW = re.compile(r"^\|\s*`(?P<package>[a-z_]+)`\s*\|(?P<owns>[^|]*)\|(?P<never>[^|]*)\|")

#: What a row has to say for a forbidden module to be carried by it, spelt as
#: `_spoken` reduces a cell. Alternatives because one module is refused for two
#: reasons at two layers: reaching `ops/` from `pipeline` is the executor taking
#: the second execution path, and from `gui` or `session` it is a layer that
#: renders or holds computing instead.
CELL_PHRASES: dict[str, tuple[str, ...]] = {
    "PySide6": ("qt",),
    "cv2": ("cv2",),
    "zarr": ("codecs",),
    "subprocess": ("processes",),
    "multiprocessing": ("processes",),
    "sieve.tools": ("computing anything",),
    "sieve.core.ops": ("computing anything", "reaching into ops/"),
    "sieve.core.pipeline_model": ("what a tool or a schema is",),
}


def never_cells() -> dict[str, str]:
    """Each package's `Never` cell, reduced, keyed by the package the row names."""
    text = VISION.read_text(encoding="utf-8")
    assert COMPONENT_HEADING in text, f"docs/VISION.md has no {COMPONENT_HEADING!r}"
    section = text.split(COMPONENT_HEADING, 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        row = ROW.match(line)
        if row:
            rows[row["package"]] = _spoken(row["never"])
    assert rows, "docs/VISION.md's component table has no rows this walk can read"
    return rows


def refusals() -> list[tuple[str, str, str]]:
    """Every (contract, source, forbidden) triple the `forbidden` contracts hold."""
    found = []
    for name, section in contracts().items():
        if section.get("type") != "forbidden":
            continue
        short = name.rsplit(":", 1)[-1]
        for source in modules(section, "source_modules"):
            for forbidden in modules(section, "forbidden_modules"):
                found.append((short, source, forbidden))
    return found


REFUSALS = refusals()
IDS = [f"{contract}-{source}-{forbidden}" for contract, source, forbidden in REFUSALS]


def test_the_walk_has_a_denominator() -> None:
    """An empty parametrization is a walk of nothing, which passes.

    What the count refuses is a narrowed nesting inside `refusals()` — the two
    loops walked in step rather than crossed — which drops cases while leaving
    every contract contributing something. It cannot refuse a key renamed in
    the config, because both sides of it read the same literal keys through
    `modules`, so a key that stops parsing zeroes the walk and the count
    together
    (`findings/loop/2026.08.07-a-generator-that-drops-half-its-cases-is-green-because-the-reds-only-see-what-it-built.md`,
    dated section). That is what the first leg is for, and it is spelt the one
    way the others are not: the keys are asked for by presence rather than by
    what they parse to, so no single fold reaches both statements. `_owed` in
    `test_contract_lines_go_red.py` buys the same separation by multiplying
    where its generator walks.
    """
    for name, section in contracts().items():
        if section.get("type") == "forbidden":
            missing = {"source_modules", "forbidden_modules"} - set(section)
            assert not missing, (
                f"{name} has no {sorted(missing)}, so it contributes no cases and the count "
                f"below agrees with a walk of nothing"
            )

    assert len(REFUSALS) == sum(
        len(modules(section, "source_modules")) * len(modules(section, "forbidden_modules"))
        for section in contracts().values()
        if section.get("type") == "forbidden"
    )
    assert REFUSALS


@pytest.mark.parametrize(("contract", "source", "forbidden"), REFUSALS, ids=IDS)
def test_every_config_source_answers_to_a_row(contract: str, source: str, forbidden: str) -> None:
    package = source.removeprefix("sieve.")
    assert package and "." not in package, (
        f"{contract} names {source!r}, which is not a package the table has rows at"
    )

    cells = never_cells()
    assert package in cells, (
        f"{contract} names {source!r} and VISION.md's component table has no `{package}` row — "
        f"either the package is a component and gets one, or the header sentence of "
        f".importlinter is what has to change"
    )

    phrases = CELL_PHRASES.get(forbidden)
    assert phrases is not None, (
        f"{contract} forbids {forbidden!r} and CELL_PHRASES says nothing about it — "
        f"name the words a `Never` cell has to use for it before the line lands"
    )
    assert any(phrase in cells[package] for phrase in phrases), (
        f"{contract} refuses `{package}` -> {forbidden}, and its `Never` cell says none of "
        f"{phrases}: {cells[package]!r}"
    )


def test_no_phrase_outlives_the_module_it_was_written_for() -> None:
    """A stale entry is a gap the gate would report as covered."""
    forbidden = {module for _, _, module in REFUSALS}
    assert set(CELL_PHRASES) == forbidden
