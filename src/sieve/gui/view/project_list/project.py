"""One project as the list reads it: a name and three display-ready lines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    """A row in the library: what it is called, what it holds, where it lives."""

    name: str
    holds: str
    opened: str
    folder: str
