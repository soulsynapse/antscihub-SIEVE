"""Every member of a declaration vocabulary reaches a consumer or is listed.

`adr/an-unconsumed-member-is-named-in-a-list.md` applied to the two vocabularies
that have members nothing consumes. The value is entirely in the second
direction: a list of gaps that only a human updates is a comment, and what makes
it a mechanism is that landing the consumer while the name stays put turns the
tree red.

The two vocabularies name their consumer differently, and neither is a
call-graph proof:

- a `ParamStereotype` is consumed when the user can populate it the way the
  member names — an entry in `kind_editors._EDITORS` for a kind that is a
  gesture on a surface, or a real control in `param_form._BUILDERS` for one that
  is typed. `_stated_value` is what the panel shows for a kind with neither, so
  a builder that *is* `_stated_value` is the absence of a consumer rather than
  one, and that is the whole of the discrimination here.
- a `DisplaySurface` is consumed when a module under `src/` names it outside the
  two packages that are its declaration: `core/`, where the vocabulary lives,
  and `tools/`, where a tool declares a surface for its band and fills it. Both
  ends of the channel are already refused against each other at registration and
  again at the fill, and both are green with nothing drawing anything — so the
  scan is over the readers, not over the declarations.

The scanner is exercised against planted text as well as against the tree, for
`test_budget_producers.py`'s reason: with nothing yet drawing a surface, a
scanner that reached no files and an honest one report the same emptiness.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from sieve.core.tool_base import (
    STEREOTYPES_WITHOUT_EDITOR,
    SURFACES_WITHOUT_PAINTER,
    DisplaySurface,
    ParamStereotype,
)

SRC = Path(__file__).resolve().parents[2] / "src" / "sieve"

#: Where a surface is defined and where one is declared and filled. Naming a
#: member in either is not drawing it.
_DECLARING_PACKAGES = (SRC / "core", SRC / "tools")


def _modules_outside_declarations() -> list[Path]:
    return [
        path
        for path in SRC.rglob("*.py")
        if not any(package in path.parents for package in _DECLARING_PACKAGES)
    ]


def _surfaces_named_in(sources: Iterable[str]) -> set[DisplaySurface]:
    texts = list(sources)
    return {
        surface
        for surface in DisplaySurface
        if any(f"DisplaySurface.{surface.name}" in text for text in texts)
    }


@pytest.fixture(scope="module")
def drawn() -> set[DisplaySurface]:
    """Surfaces named by a module under `src/` that neither defines nor fills one."""
    return _surfaces_named_in(
        path.read_text(encoding="utf-8") for path in _modules_outside_declarations()
    )


# ---- ParamStereotype -------------------------------------------------------


def _kinds_with_an_editor() -> set[ParamStereotype]:
    from sieve.gui.kind_editors import _EDITORS
    from sieve.gui.param_form import _BUILDERS, _stated_value

    typed = {kind for kind, build in _BUILDERS.items() if build is not _stated_value}
    return set(_EDITORS) | typed


def test_every_stereotype_has_an_editor_or_is_declared_not_to() -> None:
    """A kind minted with neither a gesture nor a control lands in the list or red."""
    without = set(ParamStereotype) - _kinds_with_an_editor()
    assert without == set(STEREOTYPES_WITHOUT_EDITOR), (
        "a stereotype no editor populates must be declared in "
        "`tool_base.STEREOTYPES_WITHOUT_EDITOR`; undeclared: "
        f"{sorted(kind.value for kind in without - STEREOTYPES_WITHOUT_EDITOR)}"
    )


def test_declared_editorless_stereotypes_have_not_quietly_grown_one() -> None:
    """The list only shrinks, and shrinking it is a deliberate edit."""
    grown = STEREOTYPES_WITHOUT_EDITOR & _kinds_with_an_editor()
    assert grown == set(), (
        f"{sorted(kind.value for kind in grown)} can now be populated — remove it from "
        "`STEREOTYPES_WITHOUT_EDITOR` in the commit that landed the editor"
    )


def test_a_read_only_restatement_is_not_counted_as_a_control() -> None:
    """The discrimination the first two rest on, asserted rather than assumed.

    Every kind in the list is in `_BUILDERS` — the map is total, and a kind
    absent from it is a parameter no panel can show at all. So if
    `_stated_value` counted as a consumer, both tests above would pass over an
    empty set forever and neither would ever be able to go red.
    """
    from sieve.gui.param_form import _BUILDERS, _stated_value

    assert STEREOTYPES_WITHOUT_EDITOR <= set(_BUILDERS)
    assert all(_BUILDERS[kind] is _stated_value for kind in STEREOTYPES_WITHOUT_EDITOR)


# ---- DisplaySurface --------------------------------------------------------


def test_every_surface_has_a_painter_or_is_declared_not_to(drawn: set[DisplaySurface]) -> None:
    undrawn = set(DisplaySurface) - drawn
    assert undrawn == set(SURFACES_WITHOUT_PAINTER), (
        "a surface nothing draws must be declared in `tool_base.SURFACES_WITHOUT_PAINTER`; "
        f"undeclared: {sorted(surface.value for surface in undrawn - SURFACES_WITHOUT_PAINTER)}"
    )


def test_declared_painterless_surfaces_have_not_quietly_grown_one(
    drawn: set[DisplaySurface],
) -> None:
    """The list only shrinks, and shrinking it is a deliberate edit."""
    grown = SURFACES_WITHOUT_PAINTER & drawn
    assert grown == set(), (
        f"{sorted(surface.value for surface in grown)} is now read outside `core/` and "
        "`tools/` — remove it from `SURFACES_WITHOUT_PAINTER` in the commit that landed "
        "the painter"
    )


# ---- the scanner's own sight -----------------------------------------------


def test_the_walk_reaches_the_modules_that_exist() -> None:
    """A scanner over a tree it never opened cannot be told from a green one."""
    walked = {path.relative_to(SRC).as_posix() for path in _modules_outside_declarations()}
    assert "gui/graph_panel.py" in walked
    assert "pipeline/series_collector.py" in walked
    assert not any(name.startswith(("core/", "tools/")) for name in walked)


def test_a_named_surface_is_seen_as_a_painter() -> None:
    """With nothing drawing anything, the scanner's own sight needs a case."""
    assert _surfaces_named_in(["_PAINTERS = {DisplaySurface.SCALOGRAM: _scalogram}"]) == {
        DisplaySurface.SCALOGRAM
    }
    assert _surfaces_named_in(["a scalogram is a picture of the bank"]) == set()
