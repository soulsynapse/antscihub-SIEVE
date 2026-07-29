










from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from sieve.core.pipeline_model import (
    SCHEMA_VERSION,
    ClipRange,
    CropArtifact,
    Project,
)
from sieve.core.replicates import Replicate
from sieve.core.types import ROI

ARENA = ROI(x=16, y=8, width=64, height=48)
SPAN = ClipRange(start=10, end=20)


def _artifact(**overrides: object) -> CropArtifact:
    fields: dict[str, object] = {
        "path": "clip.crops/arena-luma-10-20.mkv",
        "roi": ARENA,
        "format": "luma",
        "span": SPAN,
        "cut_from": "/videos/clip.mp4|1234|5678",
        "decoder": "opencv-4.13.0/policy-2",
    }
    fields.update(overrides)
    return CropArtifact.model_validate(fields)


def _project(tmp_path: Path) -> Project:
    return Project.for_video(tmp_path / "clip.mp4", tmp_path)


class TestTheRecordSurvivesTheDocument:
    def test_a_registered_crop_round_trips_through_yaml(self, tmp_path: Path) -> None:







        project = _project(tmp_path).with_crop(_artifact())

        restored = Project.from_yaml(project.to_yaml())

        (crop,) = restored.crops
        assert crop.roi == ARENA
        assert crop.span == SPAN
        assert crop.format == "luma"
        assert crop.cut_from == "/videos/clip.mp4|1234|5678"

    def test_a_version_four_document_loads_unchanged(self, tmp_path: Path) -> None:






        document = yaml.safe_load(_project(tmp_path).to_yaml())
        document["schema_version"] = 4
        del document["crops"]

        restored = Project.model_validate(document)

        assert restored.crops == ()
        assert restored.schema_version == SCHEMA_VERSION

    def test_two_records_of_one_cut_are_refused(self, tmp_path: Path) -> None:

        project = _project(tmp_path).with_crop(_artifact())
        document = yaml.safe_load(project.to_yaml())
        document["crops"] = [*document["crops"], {**document["crops"][0], "path": "other.mkv"}]

        with pytest.raises(ValidationError, match="same cut"):
            Project.model_validate(document)

    def test_rewriting_one_cut_replaces_its_record_in_place(self, tmp_path: Path) -> None:

        first = _artifact(path="clip.crops/a.mkv")
        second = _artifact(path="clip.crops/b.mkv")
        other = _artifact(format="bgr", path="clip.crops/c.mkv")

        project = _project(tmp_path).with_crop(first).with_crop(other).with_crop(second)

        assert [crop.path for crop in project.crops] == ["clip.crops/b.mkv", "clip.crops/c.mkv"]

    def test_relocating_a_project_rebases_the_artifact_path(self, tmp_path: Path) -> None:

        here = tmp_path / "here"
        there = tmp_path / "there"
        here.mkdir()
        there.mkdir()
        project = _project(here).with_crop(_artifact(path="clip.crops/arena.mkv"))

        moved = project.relocated(here, there)

        assert moved.crops[0].resolve(there) == (here / "clip.crops" / "arena.mkv").resolve()


class TestTheMatchingRule:


    @pytest.fixture()
    def on_disk(self, tmp_path: Path) -> CropArtifact:
        artifact = _artifact(path="clip.crops/arena-luma-10-20.mkv")
        written = artifact.resolve(tmp_path)
        written.parent.mkdir(parents=True, exist_ok=True)
        written.write_bytes(b"not a real file, but a present one")
        return artifact

    def test_it_backs_the_replicate_it_was_cut_for(
        self, on_disk: CropArtifact, tmp_path: Path
    ) -> None:
        replicate = Replicate(roi=ARENA, name="Arena 1")

        assert on_disk.backs(
            replicate,
            source="/videos/clip.mp4|1234|5678",
            luma=True,
            project_dir=tmp_path,
        )

    @pytest.mark.parametrize(
        ("roi", "source", "luma"),
        [



            (ROI(x=17, y=8, width=64, height=48), "/videos/clip.mp4|1234|5678", True),

            (ARENA, "/videos/clip.mp4|9999|5678", True),

            (ARENA, "/videos/clip.mp4|1234|5678", False),
        ],
        ids=["moved-roi", "re-exported-source", "flipped-format"],
    )
    def test_each_condition_fails_alone(
        self, on_disk: CropArtifact, tmp_path: Path, roi: ROI, source: str, luma: bool
    ) -> None:
        replicate = Replicate(roi=roi, name="Arena 1")

        assert not on_disk.backs(replicate, source=source, luma=luma, project_dir=tmp_path)

    def test_a_record_whose_file_is_gone_backs_nothing(self, tmp_path: Path) -> None:

        artifact = _artifact(path="clip.crops/deleted.mkv")
        replicate = Replicate(roi=ARENA, name="Arena 1")

        assert not artifact.backs(
            replicate,
            source="/videos/clip.mp4|1234|5678",
            luma=True,
            project_dir=tmp_path,
        )

    def test_a_rename_does_not_break_the_match(self, on_disk: CropArtifact, tmp_path: Path) -> None:

        renamed = Replicate(roi=ARENA, name="Something else entirely")

        assert on_disk.backs(
            renamed,
            source="/videos/clip.mp4|1234|5678",
            luma=True,
            project_dir=tmp_path,
        )
