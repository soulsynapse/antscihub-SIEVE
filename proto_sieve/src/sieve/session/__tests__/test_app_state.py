"""Proof for session/app_state.py's secret: selecting a project produces a
live session seeded with an empty pipeline against that project's source.
"""

from __future__ import annotations

from pathlib import Path

from proto_sieve.src.sieve.pipeline import Pipeline
from proto_sieve.src.sieve.projects import Project
from proto_sieve.src.sieve.session.app_state import NoProject, ProjectActive, select


def test_select_produces_a_project_active_state():
    project = Project("rep3_intermittent_crop", Path("video-test/rep3_intermittent_crop.MP4"))
    state = select(project)

    assert isinstance(state, ProjectActive)
    assert state.project == project


def test_select_seeds_an_empty_pipeline_for_the_projects_source():
    project = Project("rep3_intermittent_crop", Path("video-test/rep3_intermittent_crop.MP4"))
    state = select(project)

    assert state.session.pipeline == Pipeline(source="rep3_intermittent_crop", steps=())


def test_select_seeds_a_session_with_nothing_to_undo():
    project = Project("rep3_intermittent_crop", Path("video-test/rep3_intermittent_crop.MP4"))
    state = select(project)

    assert not state.session.can_undo()
    assert not state.session.can_redo()


def test_no_project_is_a_distinct_state():
    assert NoProject() != select(Project("x", Path("x.mp4")))
