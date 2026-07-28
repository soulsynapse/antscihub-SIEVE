"""The crop record: what it survives, what it refuses, and what it matches.

Three claims worth a test, each failing for a different reason. A record has to
round-trip through YAML with its geometry intact, or an artifact written today
is unfindable tomorrow. A version-4 document has to load unchanged, or the
schema bump orphans every project written before this build. And `backs` has to
say no to a moved box, a re-exported source, and a flipped format, because each
of those yes-answers serves pixels that are not what the caller asked for — the
failure mode the codec finding spent a session characterising.
"""

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
        """Geometry, span, and parentage all come back as themselves.

        The ROI is the half that would fail silently: it is a stdlib dataclass
        inside a pydantic model, so a serializer that flattened it to a list, or
        a loader that handed back a dict, would leave `backs` comparing an ROI
        against something that is not one and answering no forever.
        """
        project = _project(tmp_path).with_crop(_artifact())

        restored = Project.from_yaml(project.to_yaml())

        (crop,) = restored.crops
        assert crop.roi == ARENA
        assert crop.span == SPAN
        assert crop.format == "luma"
        assert crop.cut_from == "/videos/clip.mp4|1234|5678"

    def test_a_version_four_document_loads_unchanged(self, tmp_path: Path) -> None:
        """The bump must not orphan projects written before crops existed.

        A v4 document carries no `crops` key at all, which is exactly what an
        empty tuple means — nothing was ever written at rest — and it comes back
        restamped as this build's schema.
        """
        document = yaml.safe_load(_project(tmp_path).to_yaml())
        document["schema_version"] = 4
        del document["crops"]

        restored = Project.model_validate(document)

        assert restored.crops == ()
        assert restored.schema_version == SCHEMA_VERSION

    def test_two_records_of_one_cut_are_refused(self, tmp_path: Path) -> None:
        """Nothing downstream could choose between them — `backs` says yes twice."""
        project = _project(tmp_path).with_crop(_artifact())
        document = yaml.safe_load(project.to_yaml())
        document["crops"] = [*document["crops"], {**document["crops"][0], "path": "other.mkv"}]

        with pytest.raises(ValidationError, match="same cut"):
            Project.model_validate(document)

    def test_rewriting_one_cut_replaces_its_record_in_place(self, tmp_path: Path) -> None:
        """Re-cutting an arena must not append the pair the validator refuses."""
        first = _artifact(path="clip.crops/a.mkv")
        second = _artifact(path="clip.crops/b.mkv")
        other = _artifact(format="bgr", path="clip.crops/c.mkv")

        project = _project(tmp_path).with_crop(first).with_crop(other).with_crop(second)

        assert [crop.path for crop in project.crops] == ["clip.crops/b.mkv", "clip.crops/c.mkv"]

    def test_relocating_a_project_rebases_the_artifact_path(self, tmp_path: Path) -> None:
        """A folder that moved must not leave the record pointing at nothing."""
        here = tmp_path / "here"
        there = tmp_path / "there"
        here.mkdir()
        there.mkdir()
        project = _project(here).with_crop(_artifact(path="clip.crops/arena.mkv"))

        moved = project.relocated(here, there)

        assert moved.crops[0].resolve(there) == (here / "clip.crops" / "arena.mkv").resolve()


class TestTheMatchingRule:
    """`backs` decides whether a record may serve a replicate right now."""

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
            # A box the user nudged: the artifact holds different pixels than
            # the replicate now asks for, and serving it would silently analyse
            # the old geometry.
            (ROI(x=17, y=8, width=64, height=48), "/videos/clip.mp4|1234|5678", True),
            # A re-exported or restored source: same path, new identity.
            (ARENA, "/videos/clip.mp4|9999|5678", True),
            # A session that now needs colour. One artifact per format.
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
        """The record is location, and location is checked, never trusted."""
        artifact = _artifact(path="clip.crops/deleted.mkv")
        replicate = Replicate(roi=ARENA, name="Arena 1")

        assert not artifact.backs(
            replicate,
            source="/videos/clip.mp4|1234|5678",
            luma=True,
            project_dir=tmp_path,
        )

    def test_a_rename_does_not_break_the_match(self, on_disk: CropArtifact, tmp_path: Path) -> None:
        """Nothing is matched by name or by id — geometry and parentage only."""
        renamed = Replicate(roi=ARENA, name="Something else entirely")

        assert on_disk.backs(
            renamed,
            source="/videos/clip.mp4|1234|5678",
            luma=True,
            project_dir=tmp_path,
        )
