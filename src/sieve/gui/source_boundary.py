"""The source boundary: the card above the stack, and the write pass behind it.

The *reading* of which state a replicate's boundary is in belongs to the
document (`crop_backing`, over `pipeline/crop_binding.py`); everything here is
the wording of the four states and the gesture that moves between them.

**It is a controller, not a view and not a tab.** It is built from the document
and the `SourceCard` — both downward reads — and holds no reference back to the
tab that owns it. Three signals cross the seam: `render_hold` around the write,
`render_stale` when what is on screen was produced by a resolution that no
longer holds, and `status_message` for the one line the window's status bar
gets. Anything the controller comes to need from the tab that is not one of
those three is a sign the seam is in the wrong place.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QMessageBox

from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.gui.chain_stack import MATERIALIZE_PRICE, SourceCard
from sieve.gui.document import ReplicateDocument
from sieve.gui.materialize_worker import MaterializeRequest, MaterializeRunner
from sieve.pipeline.crop_binding import CropBacking, CropState, evidence_for


class SourceBoundary(QObject):
    """What the chain consumes, and the gesture that puts it at rest."""

    #: Stop rendering and let go of the files, or give both back. True must be
    #: delivered synchronously — see `_on_discard_crop`.
    render_hold = Signal(bool)
    #: The frames on screen were produced by a resolution that has since moved.
    render_stale = Signal()
    #: One line about what just happened, for the window's status bar.
    status_message = Signal(str)

    def __init__(
        self,
        document: ReplicateDocument,
        card: SourceCard,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._card = card
        #: The write pass, on its own thread. Owned here rather than by the
        #: window because the gesture is the source card's, and because pausing
        #: the preview around a write is a statement about the filter tab's
        #: render, which nothing else submits.
        self._materializer = MaterializeRunner(self)
        #: The row a running write belongs to. The card follows the selection,
        #: so a user who switches arenas mid-write must not see the progress of
        #: somebody else's crop on this one's card.
        self._writing_row: int | None = None
        self._connect()
        self._refresh_source_card()

    def _connect(self) -> None:
        # Every path that can move one of the four states is here: a record
        # appearing or going, a box or a graph moving under an existing one, a
        # different arena being looked at, and the clip moving past what was cut.
        card = self._card
        card.materialize_requested.connect(self._on_materialize)
        card.cancel_requested.connect(self._materializer.cancel)
        card.discard_requested.connect(self._on_discard_crop)
        self._materializer.progressed.connect(card.set_progress)
        self._materializer.written.connect(self._on_crop_written)
        self._materializer.failed.connect(self._on_crop_failed)
        self._materializer.cancelled.connect(self._on_crop_cancelled)
        document = self._document
        document.crops_changed.connect(self._refresh_source_card)
        document.selection_changed.connect(self._refresh_source_card)
        document.replicate_changed.connect(self._refresh_source_card)
        document.structure_changed.connect(self._refresh_source_card)
        document.clip_changed.connect(self._refresh_source_card)
        document.pipeline_changed.connect(self._refresh_source_card)
        document.source_changed.connect(self._refresh_source_card)

    def shutdown(self) -> None:
        """Stop the write thread. Call before the application exits.

        The same obligation `PreviewRunner.shutdown` carries, for the same
        reason: a `QThread` still running when Qt tears the widget tree down is
        a crash rather than a leak.
        """
        self._materializer.shutdown()

    @property
    def materializer(self) -> MaterializeRunner:
        """The write pass. Exposed for the window's shutdown order and for tests."""
        return self._materializer

    @Slot()
    def _refresh_source_card(self) -> None:
        """Re-read the boundary and repaint the card.

        Cheap enough to run on every document signal that could move it: the
        reading is a handful of comparisons plus one `is_file` per record, and
        a card refreshed only on the signals somebody remembered would be the
        stale-looks-fresh failure rule 6 is about.
        """
        card = self._card
        document = self._document
        home = document.source_home
        index = document.selected_index
        replicate = document.selected_replicate
        if home is None or index is None or replicate is None:
            card.setVisible(False)
            return
        card.setVisible(True)
        subject = f"{replicate.name} · {home.video.name}"
        if self._writing_row == index:
            card.set_state(
                CropState.WRITING,
                subject=subject,
                detail="cutting the crop — the preview is paused while the write reads the source",
            )
            return
        backing = document.crop_backing(index)
        card.set_state(backing.state, subject=subject, detail=self._boundary_detail(backing))

    def _boundary_detail(self, backing: CropBacking) -> str:
        """The one sentence under the title, per state.

        Stale carries `backing.reason` verbatim and then says the file is still
        there, which is the whole of the absent/stale distinction as the user
        experiences it: the remedy for a stale record is a discard or a re-cut,
        and both are cheaper decisions to take knowing the bytes exist.
        """
        if backing.state is CropState.ABSENT:
            return f"recut from the source on every render · {MATERIALIZE_PRICE}"
        artifact = backing.artifact
        if backing.state is CropState.STALE:
            return f"{backing.reason} — the file is still in the folder."
        if artifact is None:
            return ""
        return (
            f"at rest · {self._artifact_stamp(artifact)} · "
            "the box and the clip are held while this backs the replicate"
        )

    def _artifact_stamp(self, artifact: CropArtifact) -> str:
        """Size, format, span, and when it was written, as the card's one line.

        The reading is `crop_binding.evidence_for`; what is here is the wording.
        With no home bound there is no directory to resolve against, so the line
        falls back to what the record itself carries rather than stating a size
        it has not looked at.
        """
        home = self._document.source_home
        fmt = artifact.format
        extent = f"frames [{artifact.span.start}:{artifact.span.end})"
        if home is None:
            return f"{fmt} · {extent}"
        evidence = evidence_for(artifact, home.project_dir)
        if evidence.size_bytes is None or evidence.written_at is None:
            return f"{fmt} · {extent} · {evidence.path.name} (not readable)"
        written = datetime.fromtimestamp(evidence.written_at).strftime("%Y-%m-%d %H:%M")
        return f"{evidence.size_bytes / 1e6:.1f} MB · {fmt} · {extent} · written {written}"

    @Slot()
    def _on_materialize(self) -> None:
        """Cut the selected replicate's crop over the whole source.

        The whole source, not the working window, and the difference is the
        difference between an artifact that survives the user's next gesture and
        one that does not. `resolve_source` declines a record whose span does not
        cover what is being asked for, and moving the window is the single most
        ordinary thing anyone does here — cutting to the window would put a
        minute of re-encoding behind an action the user reads as scrolling. A
        full-source cut is asked for once and covers every window afterwards, at
        the cost of a longer write (`MATERIALIZE_PRICE` says so on the card).
        """
        document = self._document
        home = document.source_home
        replicate = document.selected_replicate
        frames = document.source_frames
        index = document.selected_index
        if home is None or replicate is None or frames <= 0 or index is None:
            return
        span = ClipRange(start=0, end=frames)
        if self._materializer.busy:
            self.status_message.emit("a crop is already being written")
            return
        # Before the request, not after: the write pass is a sequential decode
        # of the same footage, and a render still in flight when it starts is
        # the bandwidth wall the artifact exists to remove.
        self.render_hold.emit(True)
        self._writing_row = index
        started = self._materializer.start(
            MaterializeRequest(
                video=home.video,
                replicate=replicate,
                span=span,
                project_dir=home.project_dir,
                luma=document.decodes_luma(),
            )
        )
        if not started:
            self._writing_row = None
            self.render_hold.emit(False)
            return
        self._refresh_source_card()
        self.status_message.emit(f"writing the crop for {replicate.name}…")

    @Slot(object)
    def _on_crop_written(self, record: object) -> None:
        """A verified artifact landed: record it, and read from it from now on.

        `object` in the signature because the signal carries `object` — the
        worker's payload crosses a thread boundary as one — and the narrowing
        here is what keeps the document's side of it typed.
        """
        self._writing_row = None
        if not isinstance(record, CropArtifact):
            return
        self._document.register_crop(record)
        self._resume_after_write()
        self.status_message.emit("crop written and at rest — this replicate now reads from it")

    @Slot(str)
    def _on_crop_failed(self, message: str) -> None:
        """The write did not produce a usable file. Nothing was recorded."""
        self._writing_row = None
        self._resume_after_write()
        self.status_message.emit(f"the crop was not written: {message}")

    @Slot()
    def _on_crop_cancelled(self) -> None:
        self._writing_row = None
        self._resume_after_write()
        self.status_message.emit("crop write cancelled — nothing was left on disk")

    def _resume_after_write(self) -> None:
        """Give the decode bandwidth back and re-render whatever is now true.

        The stale report is not optional: a registered record re-roots the run
        on the artifact's own identity, so the frames on screen were produced by
        a resolution that no longer holds.
        """
        self.render_hold.emit(False)
        self._refresh_source_card()
        self.render_stale.emit()

    @Slot()
    def _on_discard_crop(self) -> None:
        """Drop a record and delete the file behind it, once confirmed.

        The file goes with the record, and the confirmation says so. A record is
        the only thing that associates a crop file with a replicate — nothing
        rediscovers an unrecorded file — so keeping the bytes would leave the
        user a folder of artifacts SIEVE can neither serve nor explain.

        **The render thread is holding the file open, and it has to let go
        first.** A record that is serving is a file the preview has a pool of
        captures over, and an open handle is an unlink that fails on Windows —
        which is how this gesture came to do nothing at all. That is what
        `render_hold(True)` buys, and it must be *delivered* before the next
        statement runs: both objects live on the GUI thread, so the slot runs to
        completion inside the emit. The day somebody makes that connection
        queued, the delete races the release and the gesture regresses to a
        no-op with no error anywhere — which is why the hold is one signal
        carrying both halves rather than a pause and a release the caller has to
        order correctly twice.

        **The record goes first, and a delete that fails does not take it with
        it.** The record is what makes the file serve; dropping it is the whole
        of what the user asked for, and it is exactly the "never registered"
        state `materialize.py` already treats as safe. A file that survives is
        reported by name — it is in a folder the user can open — rather than
        being a reason to refuse the gesture.
        """
        document = self._document
        home = document.source_home
        index = document.selected_index
        if home is None or index is None:
            return
        artifact = document.crop_backing(index).artifact
        if artifact is None:
            return
        path = artifact.resolve(home.project_dir)
        answer = QMessageBox.question(
            self._card,
            "Discard crop",
            f"Discard {path.name}?\n\n"
            "The file is deleted and this replicate is read from the source again.",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Discard:
            return
        self.render_hold.emit(True)
        document.discard_crop(artifact)
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            self.status_message.emit(
                f"the record is dropped, but {path.name} is still on disk: {error}"
            )
        self.render_hold.emit(False)
        self._refresh_source_card()
        self.render_stale.emit()
