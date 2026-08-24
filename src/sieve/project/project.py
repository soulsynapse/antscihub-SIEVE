"""A folder somebody pointed at, and what SIEVE knows about it.

Opening a project is: read the document if there is one, detect what footage is
there now, write the document back. All of it is cheap — headers and `stat`
calls — so pointing at a folder is instant and reversible, which is what makes
adding one a free move rather than an import.

**A project is the folder.** Not a file that happens to live in one: the folder
is what somebody chose, the footage is what is in it, and the document is
SIEVE's note to itself in a dot-directory beside them. That is why detection
runs on every open rather than only on the first — files arrive in a folder by
being copied there, and a project that only saw what was present the day it was
created would be wrong by the second session.

**Nothing is moved and nothing is copied.** The folder is read. What SIEVE
writes goes under the derived location the document names, which defaults to
`.sieve/` inside the project, so a project is one directory that can be copied
whole with its expensive work intact.

**A session is opened per source, not per project.** A project holds several
sources; what a session is about is one of them, plus the crop and the window
somebody is working in. `session_for` is the join between the two, and it is the
only place in this package that knows a decoder exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sieve.project import sources as detection
from sieve.project.document import Document, SourceRecord
from sieve.session.session import Session


@dataclass
class Project:
    """One folder, its document, and the footage found in it."""

    folder: Path
    document: Document

    # ── opening ──────────────────────────────────────────────────────────
    @classmethod
    def open(cls, folder: Path, *, detect: bool = True) -> "Project":
        """Open or adopt `folder`. Never raises for a folder that has no document.

        A folder nobody has pointed at before and a folder whose document is
        unreadable are the same situation and are treated the same way: make a
        document, detect what is there, write it. The only difference between
        adopting and reopening is whether an identity already exists, and that
        difference belongs in the document rather than in two methods.
        """
        folder = Path(folder).resolve()
        document = Document.load(folder) or Document(name=folder.name)
        if not document.name:
            document.name = folder.name
        project = cls(folder=folder, document=document)
        if detect:
            project.rescan()
        project.document = project.document.touched()
        project.save()
        return project

    def ignored(self) -> list[Path]:
        """Everything detection must not look in for this project.

        Its own derived location first, because everything SIEVE produces is a
        video file and a detector that finds its own chunks reports them as
        footage. Then whatever a person has excluded.
        """
        paths = [self.derived]
        for entry in self.document.excluded:
            written = Path(entry)
            paths.append(written if written.is_absolute()
                         else self.folder / written)
        return paths

    def exclude(self, path: Path) -> bool:
        """Stop looking in `path`. Returns whether it was newly excluded.

        For the folder of exports that lives beside the footage. SIEVE cannot
        tell somebody else's rendered clips from the footage they came from,
        and guessing from a directory name would be a rule that is wrong for
        whoever names theirs differently — so it is asked once and remembered
        in the document, where the answer travels with the project.
        """
        target = Path(path)
        try:
            relative = target.resolve().relative_to(self.folder).as_posix()
        except ValueError:
            relative = str(target)
        if relative in self.document.excluded:
            return False
        self.document.excluded.append(relative)
        self.rescan()
        self.save()
        return True

    def rescan(self) -> int:
        """Look again at what is in the folder. Returns how many sources."""
        records, unreadable = detection.detect(self.folder,
                                               self.document.sources,
                                               self.ignored(),
                                               self.document.skipped)
        self.document.sources = records
        self.document.skipped = unreadable
        return len(records)

    def save(self) -> bool:
        return self.document.save(self.folder)

    # ── what it holds ────────────────────────────────────────────────────
    @property
    def name(self) -> str:
        return self.document.name or self.folder.name

    @property
    def derived(self) -> Path:
        return self.document.derived_in(self.folder)

    @property
    def sources(self) -> list[SourceRecord]:
        return list(self.document.sources)

    @property
    def unreadable(self) -> int:
        """How many files looked like video and would not open."""
        return len(self.document.skipped)

    def path_of(self, source: SourceRecord) -> Path:
        return self.folder / source.path

    def missing(self) -> list[SourceRecord]:
        """Sources the document knows about that are no longer where it says.

        Reported rather than dropped. A file that has been moved away is
        different from one that was never there, and a project that quietly
        forgot it would lose the only record that it used to be part of this
        work.
        """
        return [source for source in self.document.sources
                if not (self.folder / source.path).exists()]

    def total_seconds(self) -> float:
        return sum(source.duration_s for source in self.document.sources)

    def summary(self) -> str:
        """What the card says this project holds, in the user's terms.

        Formed here rather than in the view, because deciding what counts as a
        source is a decision about what a project is. Duration rather than a
        frame count, for the reason `sources.py` gives: the honest count costs
        a demux and the cheap one is wrong.
        """
        count = len(self.document.sources)
        if not count:
            return "empty" if not self.unreadable else \
                f"nothing readable ({self.unreadable} skipped)"
        noun = "source" if count == 1 else "sources"
        parts = [f"{count} {noun}", _duration(self.total_seconds())]
        shapes = {(s.width, s.height) for s in self.document.sources if s.width}
        if len(shapes) == 1:
            width, height = next(iter(shapes))
            parts.append(f"{width}×{height}")
        elif len(shapes) > 1:
            parts.append(f"{len(shapes)} shapes")
        if self.unreadable:
            parts.append(f"{self.unreadable} skipped")
        return " · ".join(parts)

    # ── the join to the substrate ────────────────────────────────────────
    def session_for(self, source: SourceRecord, **kwargs) -> Session:
        """A session over one of this project's sources.

        The derived directory comes from the document, so every session of one
        project writes to one place and a project moved to another machine
        finds its own chunks rather than rebuilding them.
        """
        return Session(self.path_of(source), self.derived / source.path,
                       **kwargs)


def _duration(seconds: float) -> str:
    """Seconds as somebody reads them, not as they are stored."""
    if seconds < 1:
        return "under a second"
    minutes, remainder = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {remainder:02d}s"
    return f"{remainder}s"
