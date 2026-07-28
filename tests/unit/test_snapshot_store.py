"""The snapshot store's two load-bearing claims: a snapshot is a project, and
retention keeps the entries a rollback is actually reached for.

Everything here is filesystem and naming, which is why it is a unit test rather
than a GUI one — `SnapshotStore` is deliberately Qt-free.
"""

from __future__ import annotations

from pathlib import Path

from sieve.core.pipeline_model import Project
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.history import SnapshotStore, age_text, history_directory, slugged


def a_project(tmp_path: Path, *, replicates: int = 0) -> Project:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"")
    project = Project.for_video(video, tmp_path / "history")
    return project.with_replicates(
        tuple(
            Replicate(roi=ROI(x=index, y=0, width=10, height=10), name=f"R{index}")
            for index in range(replicates)
        )
    )


class TestASnapshotIsAProject:
    def test_a_written_snapshot_loads_back_through_the_ordinary_reader(
        self, tmp_path: Path
    ) -> None:
        # The claim that makes history worth having at all: nothing bespoke
        # reads these files. If `Project.load` can open one, so can the CLI.
        store = SnapshotStore(tmp_path / "history")
        snapshot = store.record(a_project(tmp_path, replicates=2), "Add R1")
        assert len(Project.load(snapshot.path).replicates) == 2

    def test_the_source_resolves_from_inside_the_history_directory(self, tmp_path: Path) -> None:
        # The anchoring decision. A snapshot anchored to the *project*
        # directory would name a video one level up from where it sits, so
        # opening one directly would fail to find the footage.
        store = SnapshotStore(tmp_path / "history")
        snapshot = store.record(a_project(tmp_path), "Add R1")
        loaded = Project.load(snapshot.path)
        assert loaded.source_path(snapshot.path) == (tmp_path / "clip.mp4").resolve()


class TestRetention:
    def test_the_newest_window_survives_and_older_steps_do_not(self, tmp_path: Path) -> None:
        store = SnapshotStore(tmp_path / "history", limit=3)
        for index in range(6):
            store.record(a_project(tmp_path), f"Edit {index}")
        texts = [snapshot.text for snapshot in store.entries()]
        # Three ordinary steps, plus the session start that retention pins.
        assert texts == ["Edit 0", "Edit 3", "Edit 4", "Edit 5"]

    def test_the_session_start_outlives_the_window_it_falls_out_of(self, tmp_path: Path) -> None:
        # The whole reason the mark exists: a pure newest-N rule ages out the
        # "before today" restore point exactly mid-session, which is the case a
        # rollback is most often reached for.
        store = SnapshotStore(tmp_path / "history", limit=2)
        for index in range(10):
            store.record(a_project(tmp_path), f"Edit {index}")
        starts = [snapshot for snapshot in store.entries() if snapshot.session_start]
        assert [snapshot.text for snapshot in starts] == ["Edit 0"]

    def test_a_second_store_over_the_same_directory_starts_its_own_session(
        self, tmp_path: Path
    ) -> None:
        # A store is constructed once per project a session opens, so "first
        # write of this store" is the session boundary — nothing has to be told
        # when a session begins.
        first = SnapshotStore(tmp_path / "history")
        first.record(a_project(tmp_path), "Edit 0")
        first.record(a_project(tmp_path), "Edit 1")
        second = SnapshotStore(tmp_path / "history")
        second.record(a_project(tmp_path), "Edit 2")
        marked = [snapshot.text for snapshot in second.entries() if snapshot.session_start]
        assert marked == ["Edit 0", "Edit 2"]

    def test_sequence_numbers_continue_past_what_is_already_there(self, tmp_path: Path) -> None:
        first = SnapshotStore(tmp_path / "history")
        first.record(a_project(tmp_path), "Edit 0")
        second = SnapshotStore(tmp_path / "history")
        snapshot = second.record(a_project(tmp_path), "Edit 1")
        assert snapshot.sequence == 2


class TestTheDirectoryReadsAsHistory:
    def test_an_undo_text_round_trips_through_the_filename(self, tmp_path: Path) -> None:
        store = SnapshotStore(tmp_path / "history")
        snapshot = store.record(a_project(tmp_path), "Set All to 1000x800")
        assert snapshot.text == "Set All to 1000x800"
        assert "Set_All_to_1000x800" in snapshot.path.name

    def test_a_text_with_nothing_safe_in_it_still_produces_a_name(self) -> None:
        assert slugged("///") == "Edit"
        assert slugged("") == "Edit"

    def test_files_that_are_not_snapshots_are_ignored_rather_than_fatal(
        self, tmp_path: Path
    ) -> None:
        # This directory sits in a user's project folder. A note dropped in it
        # must not stop the safety net listing.
        store = SnapshotStore(tmp_path / "history")
        store.record(a_project(tmp_path), "Edit 0")
        (tmp_path / "history" / "notes.txt").write_text("hello", encoding="utf-8")
        assert [snapshot.text for snapshot in store.entries()] == ["Edit 0"]

    def test_the_directory_hangs_off_the_whole_project_name(self, tmp_path: Path) -> None:
        # Not the stem: `arena.sieve.yaml` must not share a directory with a
        # sibling that happens to be called `arena.history`.
        assert history_directory(tmp_path / "arena.sieve.yaml").name == "arena.sieve.yaml.history"


class TestAge:
    def test_the_units_are_the_coarsest_that_still_distinguish(self) -> None:
        assert age_text(5) == "just now"
        assert age_text(300) == "5 min ago"
        assert age_text(3600) == "1 hour ago"
        assert age_text(7200) == "2 hours ago"
        assert age_text(86400) == "yesterday"
        assert age_text(86400 * 3) == "3 days ago"
