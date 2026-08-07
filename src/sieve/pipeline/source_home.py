"""The frame of reference a crop record is read against: three facts, one value.

A `CropRecord` is unreadable without all three. `project_dir` is what its
relative `path` resolves against; `identity` is what its `cut_from` is matched
against; `video` is what a run falls back to and what a re-cut would read. A
caller holding `project_dir` without `identity` resolves a path and then matches
it against nothing, and one holding `identity` without `video` learns a record is
stale with nothing to re-cut from. They travel together or the caller has a bug
that looks like a working call.

**Its own module because it is the argument both twins take and neither owns.**
`resolve_source.resolve` and `crop_binding.backing_for` walk the same clauses
over the same records and are deliberately siblings; putting the value they
share inside either one would make the other import through it and give the pair
a direction they do not have. Not `core/` either, though the fields alone would
allow it: `for_video` stats the parent through `cache_key.source_identity`, and
a fourth fact added to what a record is read against changes this file and both
twins in one commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sieve.pipeline.cache_key import source_identity


@dataclass(frozen=True, slots=True)
class SourceHome:
    """Where the footage is, what it is, and what its crops sit beside."""

    #: The project's parent footage — what a run reads when no record serves.
    video: Path
    #: What `CropRecord.path` is relative to. The project file's directory once
    #: there is one, and the conventional home beside the video until then, so an
    #: artifact written before the first save is not made unfindable by the save.
    project_dir: Path
    #: `cache_key.source_identity(video)`, held rather than derived on demand: it
    #: stats the parent, and the four-state reading is asked for far more often
    #: than the footage changes.
    identity: str

    @classmethod
    def for_video(cls, video: Path, project_dir: Path) -> SourceHome:
        """`video`'s home, with the identity read from the file.

        Raises:
            OSError: if the footage is not where the project says. Left to the
                caller because the answer differs by front end — a command
                refuses with a message naming the path, and a GUI drops the home
                entirely so that no record can claim to be at rest.
        """
        return cls(video=video, project_dir=project_dir, identity=source_identity(video))
