"""REWORK R4's literal half: a filter id spelled away from home is an enumeration.

Rule 3 says nothing enumerates filters, and `test_filter_discovery.py` enforces
it for *imports* — a manifest cannot be added without failing that check. It is
blind to the other way the enumeration comes back: `"block_signal"` typed into a
widget. Eleven `(module, filter_id)` pairs are typed today, and every one of them
is a place the discovery contract cannot see, so adding a filter means editing
those modules after all.

The exception set is the work list, in `gui-computes-nothing`'s shape and
`WITHOUT_PRODUCER`'s: an undeclared spelling fails, and so does a declared one
that has gone — deleting the literal and deleting its entry are one edit, and
*adding* an entry is a visible widening.

It lives here rather than in `src/` — the one place `WITHOUT_PRODUCER`'s shape
does not carry over. A list of filter ids in a module under `src/sieve/` would
be eleven foreign spellings of its own, so the declaration would trip the check
it declares.

Deliberately narrow: registered ids, and declared column names. A generic
two-layer duplicate-literal detector would seed an exception list the size of the
codebase — `"in"`, `"array"`, every StrEnum value — which is enumeration rot
re-encoded in Python. REWORK.md R4's Gate line records the rejection.

The second check covers declared table columns and the element-dependent
detection columns generated from emitted element names. The first table emitter
will add to the same set; it will not invent a second guardrail shape.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Iterable, Iterator
from pathlib import Path

import pytest

import sieve
from sieve.core.filter_base import SOURCE_ELEMENT_NAMES, ElementNames, FilterSpec, TableSpec
from sieve.detect.tables import element_series_column_names
from sieve.filters import discover

SRC = Path(str(sieve.__file__)).resolve().parent

#: `(module relative to src/sieve, filter_id)`, one per id a module spells that
#: is registered somewhere else. Shrink-only; see this module's docstring.
SPELLED_AWAY_FROM_HOME = frozenset(
    {
        # The CLI command name and the compatibility package's exported
        # function predate the filter id. They are homonyms, not a filter
        # enumeration, and stay until `sieve detect` collapses into `sieve run`.
        ("cli/app.py", "detect"),
        ("detect/__init__.py", "detect"),
        # Step ids that happen to equal filter ids, plus `node.filter_id ==`
        # comparisons in the caption builder and in `parity_chain`.
        ("gui/chain_model.py", "block_signal"),
        ("gui/chain_model.py", "normalize"),
        ("gui/chain_model.py", "rescale"),
        # The widget's per-step body table, its parameter submissions, and the
        # five-step membership test.
        ("gui/filter_tab.py", "block_signal"),
        ("gui/filter_tab.py", "normalize"),
        ("gui/filter_tab.py", "rescale"),
        # `catalog()` names each node-backed entry twice — as `entry_id` and as
        # `filter_id` — and `_seed_node` special-cases one of them.
        ("gui/wizard_model.py", "background_ema"),
        ("gui/wizard_model.py", "block_signal"),
        ("gui/wizard_model.py", "downsample"),
        ("gui/wizard_model.py", "normalize"),
        ("gui/wizard_model.py", "rescale"),
        # The FFmpeg source lowerer recognizes the one root crop/area-scale
        # prefix whose filter semantics it can move into the decoder contract.
        ("pipeline/lowering.py", "crop"),
        ("pipeline/lowering.py", "downsample"),
        ("pipeline/lowering.py", "rescale"),
    }
)


def _string_constants(path: Path) -> Iterator[str]:
    """Every string literal in `path`, docstrings and f-string parts included.

    Read as an AST rather than as text so that this module's own prose, and the
    guidance markdown quoted in a docstring, cannot trip the check — the same
    reason `test_discovery_imports_no_filter_module` parses instead of greps.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def _home(spec: FilterSpec) -> Path:
    """The module that registered `spec`, asked of the class rather than assumed.

    Not `filters/<filter_id>.py`: that convention holds for all seven filters
    today and is not a rule anything enforces, so deriving the path from it
    would make this check quietly wrong for the first filter that breaks it.
    """
    return Path(inspect.getfile(spec.params_model)).resolve()


def _spellings(modules: Iterable[Path], homes: dict[str, Path], root: Path) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in modules:
        for value in _string_constants(path):
            home = homes.get(value)
            if home is not None and home != path.resolve():
                found.add((path.resolve().relative_to(root).as_posix(), value))
    return found


@pytest.fixture(scope="module")
def homes() -> dict[str, Path]:
    return {spec.filter_id: _home(spec) for spec in discover()}


@pytest.fixture(scope="module")
def spelled(homes: dict[str, Path]) -> set[tuple[str, str]]:
    return _spellings(sorted(SRC.rglob("*.py")), homes, SRC)


def test_no_filter_id_is_spelled_outside_its_module_undeclared(
    spelled: set[tuple[str, str]],
) -> None:
    undeclared = spelled - SPELLED_AWAY_FROM_HOME
    assert undeclared == set(), (
        "a filter id typed outside the module that registers it is an "
        "enumeration rule 3 forbids; eliminate the spelling, or declare it in "
        f"`SPELLED_AWAY_FROM_HOME` as a deliberate widening: {sorted(undeclared)}"
    )


def test_the_declared_spellings_only_shrink(spelled: set[tuple[str, str]]) -> None:
    """Deleting the literal and deleting its entry are one edit."""
    stale = SPELLED_AWAY_FROM_HOME - spelled
    assert stale == set(), (
        f"no longer spelled — remove from `SPELLED_AWAY_FROM_HOME`: {sorted(stale)}"
    )


def test_the_declared_spellings_name_real_filters_and_real_modules(
    homes: dict[str, Path],
) -> None:
    """A pair naming nothing would shrink the list without moving any code."""
    unknown = {pair for pair in SPELLED_AWAY_FROM_HOME if pair[1] not in homes}
    assert unknown == set(), f"not registered filter ids: {sorted(unknown)}"
    missing = {pair for pair in SPELLED_AWAY_FROM_HOME if not (SRC / pair[0]).is_file()}
    assert missing == set(), f"no such module: {sorted(missing)}"


def test_the_walk_sees_a_spelling_and_is_not_fooled_by_a_near_miss(
    tmp_path: Path, homes: dict[str, Path]
) -> None:
    """A checker over a tree that already satisfies it cannot be told from one
    that never looks — the reason `test_guardrail_refs.py` carries the same
    half. Both directions, because exact equality is the whole narrowing: the
    prose in a docstring mentions these ids constantly and must not fire."""
    planted = tmp_path / "planted.py"
    planted.write_text('BODIES = {"rescale": 1}\n"""Prose about rescale."""\n', encoding="utf-8")
    assert _spellings([planted], homes, tmp_path) == {("planted.py", "rescale")}

    near = tmp_path / "near.py"
    near.write_text('X = "rescale_v2"\nY = "Rescale"\n', encoding="utf-8")
    assert _spellings([near], homes, tmp_path) == set()


# --- the second check: declared column names ---------------------------------


def _packages(root: Path) -> tuple[Path, ...]:
    """Top-level packages, read off the tree. Typing them would be the
    enumeration this file exists to refuse."""
    return tuple(sorted(path for path in root.iterdir() if (path / "__init__.py").is_file()))


def _declared_columns() -> set[str]:
    names: set[str] = set()
    element_names: set[ElementNames] = {SOURCE_ELEMENT_NAMES}
    for spec in discover():
        accepts = spec.accepts.values() if isinstance(spec.accepts, dict) else [spec.accepts]
        for stream in (*accepts, spec.emits):
            if isinstance(stream, TableSpec):
                names.update(stream.columns)
        if spec.element_names is not None:
            element_names.add(spec.element_names)
    for emitted in element_names:
        names.update(element_series_column_names(emitted))
    return names


def _packages_spelling(name: str, packages: Iterable[Path]) -> set[str]:
    return {
        package.name
        for package in packages
        if any(name in _string_constants(path) for path in package.rglob("*.py"))
    }


def test_no_declared_column_name_is_spelled_in_two_packages() -> None:
    packages = _packages(SRC)
    spread = {name: _packages_spelling(name, packages) for name in _declared_columns()}
    duplicated = {name: sorted(where) for name, where in spread.items() if len(where) > 1}
    assert duplicated == {}, (
        "a column name declared on a `TableSpec` and typed in two packages is "
        f"one name with two homes; promote it or eliminate a spelling: {duplicated}"
    )


def test_the_column_check_fires_on_two_package_spellings(tmp_path: Path) -> None:
    """A planted tree pins the duplicate-spelling mechanism directly."""
    for package, body in (("alpha", 'COLUMN = "centroid_x"\n'), ("beta", 'X = "centroid_x"\n')):
        (tmp_path / package).mkdir()
        (tmp_path / package / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / package / "mod.py").write_text(body, encoding="utf-8")
    (tmp_path / "not_a_package.py").write_text('X = "centroid_x"\n', encoding="utf-8")

    packages = _packages(tmp_path)
    assert [path.name for path in packages] == ["alpha", "beta"]
    assert _packages_spelling("centroid_x", packages) == {"alpha", "beta"}
    assert _packages_spelling("frame", packages) == set()
