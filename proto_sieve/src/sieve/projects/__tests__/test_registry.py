"""Proof for projects/registry.py's secret: a project exists only because
it was added, the registry round-trips through its one JSON file, and a
duplicate name is rejected rather than silently overwriting.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proto_sieve.src.sieve.projects.projects import Project
from proto_sieve.src.sieve.projects.registry import add_project, list_projects, remove_project


def test_a_freshly_added_project_appears_in_the_list(tmp_path):
    add_project(Project("rep3_intermittent_crop", Path("video-test/rep3_intermittent_crop.MP4")), tmp_path)

    assert list_projects(tmp_path) == [
        Project("rep3_intermittent_crop", Path("video-test/rep3_intermittent_crop.MP4"))
    ]


def test_an_empty_registry_lists_nothing_without_ever_being_written(tmp_path):
    assert list_projects(tmp_path) == []


def test_adding_a_duplicate_name_raises(tmp_path):
    add_project(Project("a", Path("a.mp4")), tmp_path)
    with pytest.raises(ValueError):
        add_project(Project("a", Path("other.mp4")), tmp_path)


def test_remove_project_drops_it_from_the_list(tmp_path):
    add_project(Project("a", Path("a.mp4")), tmp_path)
    add_project(Project("b", Path("b.mp4")), tmp_path)

    remove_project("a", tmp_path)

    assert list_projects(tmp_path) == [Project("b", Path("b.mp4"))]


def test_projects_are_listed_sorted_by_name(tmp_path):
    add_project(Project("z", Path("z.mp4")), tmp_path)
    add_project(Project("a", Path("a.mp4")), tmp_path)

    assert [p.name for p in list_projects(tmp_path)] == ["a", "z"]
