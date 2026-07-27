"""`docs/SCAFFOLD.md` is the placement authority, so it has to be true.

The previous version of that file drifted for two weeks: it named a napari
viewer and a visual DAG editor after both were rejected, named five packages
nobody wrote, and omitted twenty-seven GUI modules that were. An agent reading
it for "where does this go" would have been sent to three places that had
already been refused.

Prose cannot be checked, so the file is now two lists and these tests are what
make them binding. Every path under `## Built` must exist; every path under
`## Projected` must not. The second half is the one that matters more — a
projected module that quietly gets built is how the file stops describing the
gap between intent and reality, which is the only thing it is for.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = REPO_ROOT / "docs" / "SCAFFOLD.md"

BUILT = "## Built"
PROJECTED = "## Projected"
FENCE = "```"


def paths_under(heading: str) -> list[str]:
    """Repo-relative paths from the fenced blocks under one `##` heading.

    A line's path is its first whitespace-delimited token; everything after is
    the annotation. Blank lines and lines outside a fence are prose.
    """
    lines = SCAFFOLD.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(heading)]
    assert len(starts) == 1, f"{heading!r} must appear exactly once in {SCAFFOLD.name}"

    start = starts[0] + 1
    ends = [i for i, line in enumerate(lines[start:], start) if line.startswith("## ")]
    section = lines[start : ends[0] if ends else len(lines)]

    found: list[str] = []
    inside = False
    for line in section:
        if line.startswith(FENCE):
            inside = not inside
        elif inside and line.strip():
            found.append(line.split()[0])
    return found


@pytest.fixture(scope="module")
def built() -> list[str]:
    return paths_under(BUILT)


@pytest.fixture(scope="module")
def projected() -> list[str]:
    return paths_under(PROJECTED)


class TestTheFileIsParseable:
    """A malformed SCAFFOLD fails here rather than silently checking nothing."""

    def test_both_halves_have_entries(self, built: list[str], projected: list[str]) -> None:
        # An empty list would make every assertion below vacuously pass, which
        # is the failure mode that lets the file rot while the suite stays green.
        assert len(built) > 40
        assert len(projected) > 10

    def test_no_path_is_listed_in_both_halves(self, built: list[str], projected: list[str]) -> None:
        assert not set(built) & set(projected)


class TestBuiltPathsExist:
    def test_every_named_module_is_there(self, built: list[str]) -> None:
        missing = [path for path in built if not (REPO_ROOT / path).exists()]
        assert not missing, (
            f"SCAFFOLD.md names these under `{BUILT}` but they do not exist: {missing}. "
            "Either the file moved, or the line belongs under `## Projected`."
        )


class TestProjectedPathsDoNotExist:
    def test_nothing_projected_has_quietly_landed(self, projected: list[str]) -> None:
        landed = [path for path in projected if (REPO_ROOT / path).exists()]
        assert not landed, (
            f"SCAFFOLD.md lists these as not built, but they exist: {landed}. "
            f"Move the line to `{BUILT}` and annotate what it owns."
        )


class TestRejectedModulesStayRejected:
    """Three designs were refused with reasoning; the file must not re-propose them."""

    def test_rejected_modules_are_absent_from_the_tree(self) -> None:
        for path in ("src/sieve/gui/viewer.py", "src/sieve/gui/pipeline_editor.py"):
            assert not (REPO_ROOT / path).exists(), (
                f"{path} was rejected — see SCAFFOLD.md `## Rejected`. "
                "Building it needs a new demand, not a revisit."
            )

    def test_the_spec_folder_the_handoff_used_to_ask_for_stays_absent(self) -> None:
        # `src/sieve/docs/` never existed. Contracts live in module docstrings
        # with their reasoning in the matching completed-todo entry.
        assert not (REPO_ROOT / "src" / "sieve" / "docs").exists()
