"""Secret: whether a project is chosen yet, and what "chosen" hands you.

Two states: ``NoProject`` (nothing picked — the GUI's project selection
screen owns what that looks like) and ``ProjectActive`` (a project plus a
live ``Session`` for it). ``select`` is the only path from one to the
other. What pipeline a freshly-chosen project starts with is not decided
beyond "empty" — see docs/DECISIONS.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from proto_sieve.src.sieve.pipeline import Pipeline
from proto_sieve.src.sieve.projects import Project
from proto_sieve.src.sieve.session.session import Session


@dataclass(frozen=True)
class NoProject:
    pass


class ProjectActive:
    def __init__(self, project: Project, session: Session) -> None:
        self.project = project
        self.session = session


AppState = NoProject | ProjectActive


def select(project: Project) -> ProjectActive:
    return ProjectActive(project, Session(Pipeline(source=project.name, steps=())))
