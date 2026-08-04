"""Secret: what a project is.

A name and a source video path — a value, nothing else. The name matches
the convention a ``Pipeline.source`` uses (see ``pipeline.py``), so a
project's name is what a pipeline built for it names as its source. Which
projects exist and how that's persisted is ``registry.py``'s secret, not
this module's.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Project:
    name: str
    source_path: Path
