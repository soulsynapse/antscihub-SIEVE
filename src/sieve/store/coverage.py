"""What is on disk, written down rather than worked out.

The rule this module exists to enforce: **coverage is recorded, never
inferred.** Not from a file being present, not from a gap in a sequence, not
from a value being zero. `series.py` states the same rule for the analysis tier
and states why — an unwritten row and a row whose value is genuinely zero are
indistinguishable in the data, and every consumer added later is one that does
not know to check.

The frame tiers had the same defect in a different disguise. Both explorers
answer "which chunks exist" by globbing a directory and parsing integers out of
filenames, per call, and then bolt a trust heuristic on top because a file being
written is present but incomplete. Three separate things go wrong there: a
partial file reads as a whole one, an identity has to survive a round trip
through a path, and the answer costs a directory listing every time it is
wanted.

**A span is published, not noticed.** Anything this tree encodes is written
under a temporary name and renamed into place, and only then recorded here. So
presence in the record means complete, and a process killed mid-encode leaves an
orphan that reads as absent and gets re-derived — which is the safe direction to
fail in. The record is written the same way, through a rename, so a crash leaves
the previous record rather than a truncated one.

**Recording is a whole-document rewrite, and that is a stated limit rather
than an oversight.** Every `record` serialises every span and renames the file
into place, so the cost of adding one grows with how many there already are.
That is affordable for a session's worth of chunks and it is not free: the
measurement lives beside the other numbers, as a case in
`experiments/substrate-checks/03-tiers.py`, where a later one can sit next to it
rather than argue with it. Two consequences worth knowing before this is called
from anywhere new. It belongs on a producer's thread and not on the one that
draws — a publisher that records several spans in a row is doing that work
serially, and presentation-layer work nobody clocked is the shape of every
freeze this tree has diagnosed. And the growth is in spans rather than in
frames, so shortening chunks costs more here than lengthening them saves.

**A span names a pts range, not a row range.** Rows are a coordinate inside one
store and mean nothing to the next thing that opens this directory (ADR-0004).
The file this record points at is named by a digest rather than by its identity,
because a form key contains characters a path cannot hold on every platform, and
an artifact whose identity must be recovered by parsing its filename stops being
readable the first time it is.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

_FILE = "coverage.json"


@dataclass(frozen=True)
class Span:
    """One file, and exactly which instants of which picture it holds."""

    form_key: str
    start_pts: int      #: first frame's timestamp, inclusive
    end_pts: int        #: last frame's timestamp, inclusive
    rows: int           #: how many frames are in the file
    filename: str

    def holds(self, pts: int) -> bool:
        return self.start_pts <= pts <= self.end_pts


def digest(form_key: str, start_pts: int) -> str:
    """A filename that carries no identity, for a record that carries all of it.

    Short and stable: the same form and start always name the same file, so a
    re-encode replaces rather than accumulating, and nothing has to parse this
    to learn what it is.
    """
    material = f"{form_key}|{start_pts}".encode("utf-8")
    return hashlib.blake2b(material, digest_size=8).hexdigest()


class Coverage:
    """The record for one directory of spans, read and written under a lock."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.path = directory / _FILE
        self._lock = threading.RLock()
        self._spans: list[Span] = []
        self._load()

    # ── reading ──────────────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        with self._lock:
            self._spans = [Span(**entry) for entry in raw.get("spans", [])
                           if isinstance(entry, dict)]

    def find(self, form_key: str, pts: int) -> Span | None:
        """The span holding this instant of this picture, or `None`."""
        with self._lock:
            for span in self._spans:
                if span.form_key == form_key and span.holds(pts):
                    return span
        return None

    def spans(self, form_key: str | None = None) -> list[Span]:
        with self._lock:
            return [s for s in self._spans
                    if form_key is None or s.form_key == form_key]

    def forms(self) -> set[str]:
        with self._lock:
            return {span.form_key for span in self._spans}

    def __len__(self) -> int:
        with self._lock:
            return len(self._spans)

    # ── writing ──────────────────────────────────────────────────────────
    def record(self, span: Span) -> None:
        """Note a span that is already completely on disk.

        Called after the rename and never before it. A caller that records
        first and writes second has reintroduced exactly the partial-file
        problem this record exists to remove.
        """
        with self._lock:
            self._spans = [s for s in self._spans
                           if not (s.form_key == span.form_key
                                   and s.start_pts == span.start_pts)]
            self._spans.append(span)
            self._save()

    def forget(self, span: Span, unlink: bool = True) -> None:
        """Drop a span from the record, and by default from the disk.

        The record goes first. An entry pointing at a file that is gone is a
        lie this module is responsible for; a file with no entry is an orphan,
        which costs space and nothing else.
        """
        with self._lock:
            self._spans = [s for s in self._spans if s != span]
            self._save()
        if unlink:
            (self.directory / span.filename).unlink(missing_ok=True)

    def clear(self, form_key: str | None = None) -> int:
        """Forget every span, or every span of one form. Returns how many."""
        for span in self.spans(form_key):
            self.forget(span)
        return len(self.spans(form_key))

    def _save(self) -> None:
        """Whole-document replace through a rename. Called under the lock."""
        payload = {"spans": [asdict(span) for span in self._spans]}
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(dir=str(self.directory),
                                                 suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                json.dump(payload, out, indent=1)
            os.replace(temporary, self.path)
        except OSError:
            # a record that could not be written means the spans it describes
            # read as absent next session and are re-derived; the alternative
            # is a session that will not open over a full disk
            pass
