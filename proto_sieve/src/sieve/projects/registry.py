"""Secret: which projects the user has deliberately added, and how that
list is persisted.

Projects are never discovered by scanning a directory — a project exists
because ``add_project`` was called, and stops existing when
``remove_project`` is. The whole registry is one JSON file (one array of
projects), read and written through ``store/``'s name-to-file primitive;
this module owns the JSON shape of that array, ``store/`` owns the file.
"""

from __future__ import annotations

import json
from pathlib import Path

from proto_sieve.src.sieve.projects.projects import Project
from proto_sieve.src.sieve.store import load_text, repo_root, save_text

DEFAULT_CONFIG_DIR = repo_root() / "proto_sieve" / "config"
_REGISTRY_NAME = "projects"


def _to_json(projects: list[Project]) -> str:
    payload = [{"name": p.name, "source_path": str(p.source_path)} for p in projects]
    return json.dumps(payload, sort_keys=True)


def _from_json(blob: str) -> list[Project]:
    return [Project(d["name"], Path(d["source_path"])) for d in json.loads(blob)]


def list_projects(directory: Path = DEFAULT_CONFIG_DIR) -> list[Project]:
    try:
        text = load_text(_REGISTRY_NAME, directory)
    except FileNotFoundError:
        return []
    return _from_json(text)


def add_project(project: Project, directory: Path = DEFAULT_CONFIG_DIR) -> None:
    projects = list_projects(directory)
    if any(p.name == project.name for p in projects):
        raise ValueError(f"a project named {project.name!r} already exists")
    projects.append(project)
    projects.sort(key=lambda p: p.name)
    save_text(_REGISTRY_NAME, _to_json(projects), directory)


def remove_project(name: str, directory: Path = DEFAULT_CONFIG_DIR) -> None:
    remaining = [p for p in list_projects(directory) if p.name != name]
    save_text(_REGISTRY_NAME, _to_json(remaining), directory)
