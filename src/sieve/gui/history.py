from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sieve.core.pipeline_model import PROJECT_SUFFIX, Project


HISTORY_SUFFIX = ".history"


SNAPSHOT_LIMIT = 50


SESSION_KIND = "session"
STEP_KIND = "step"


UNTITLED = "Edit"

_FILENAME = re.compile(
    rf"^(?P<sequence>\d+)-(?P<kind>{SESSION_KIND}|{STEP_KIND})-(?P<slug>.*)"
    rf"{re.escape(PROJECT_SUFFIX)}$"
)

_UNSAFE = re.compile(r"[^A-Za-z0-9]+")


_SLUG_LIMIT = 48


def slugged(text: str) -> str:
    cleaned = _UNSAFE.sub("_", text).strip("_")[:_SLUG_LIMIT].strip("_")
    return cleaned or UNTITLED


@dataclass(frozen=True)
class Snapshot:
    path: Path
    sequence: int

    session_start: bool

    written_at: float

    @property
    def text(self) -> str:
        match = _FILENAME.match(self.path.name)
        return match["slug"].replace("_", " ") if match else UNTITLED


class SnapshotStore:
    def __init__(self, directory: Path, *, limit: int = SNAPSHOT_LIMIT) -> None:
        self._directory = directory
        self._limit = max(limit, 1)
        self._written = 0

    @property
    def directory(self) -> Path:
        return self._directory

    def entries(self) -> list[Snapshot]:
        if not self._directory.is_dir():
            return []
        found: list[Snapshot] = []
        for path in self._directory.iterdir():
            match = _FILENAME.match(path.name)
            if match is None or not path.is_file():
                continue
            found.append(
                Snapshot(
                    path=path,
                    sequence=int(match["sequence"]),
                    session_start=match["kind"] == SESSION_KIND,
                    written_at=path.stat().st_mtime,
                )
            )
        return sorted(found, key=lambda snapshot: snapshot.sequence)

    def record(self, project: Project, text: str) -> Snapshot:
        self._directory.mkdir(parents=True, exist_ok=True)
        existing = self.entries()
        sequence = existing[-1].sequence + 1 if existing else 1
        session_start = self._written == 0
        kind = SESSION_KIND if session_start else STEP_KIND
        path = (
            self._directory / f"{sequence:06d}-{kind}-{slugged(text)}{PROJECT_SUFFIX}"
        )
        project.save(path)
        self._written += 1
        self._prune()
        return Snapshot(
            path=path,
            sequence=sequence,
            session_start=session_start,
            written_at=path.stat().st_mtime,
        )

    def _prune(self) -> None:
        entries = self.entries()
        ordinary = [snapshot for snapshot in entries if not snapshot.session_start]
        doomed = set(ordinary[: max(len(ordinary) - self._limit, 0)])
        for snapshot in doomed:
            try:
                snapshot.path.unlink()
            except OSError:
                continue


def history_directory(project_path: Path) -> Path:
    return project_path.with_name(project_path.name + HISTORY_SUFFIX)


def age_text(seconds: float) -> str:
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    days = int(seconds // 86400)
    return "yesterday" if days == 1 else f"{days} days ago"
