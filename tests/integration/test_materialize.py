"""The crop writer end to end: a real decode, a real encode, a real read-back.

An integration test because every part of the claim is about a file. The
question is not whether the arithmetic is right — there is none — but whether
the bytes that leave `VideoReader`, pass through PyAV, and come back through
`VideoReader` are the same bytes, in both decode formats, and whether the
verification pass actually catches the case where they are not.

That last one is the load-bearing test in this module. The codec finding
measured a *lossless* encoding whose frames came back wrong through the same
reader with the right shape and the right count — so a writer that trusted its
encoder would have registered it. The refusal test simulates exactly that:
right file, right frame count, wrong pixels.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import ClipRange, Project
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.decode.reader import VideoReader
from sieve.pipeline import materialize as materialize_module
from sieve.pipeline.materialize import (
    CropVerificationError,
    MaterializeCancelledError,
    materialize_crop,
)
from sieve.storage.crop_writer import write_ffv1

runner = CliRunner()

ARENA = ROI(x=16, y=8, width=64, height=48)
SPAN = ClipRange(start=10, end=16)


def _replicate() -> Replicate:
    return Replicate(roi=ARENA, name="Arena 1")


def _source_crops(video: Path, span: ClipRange, *, luma: bool) -> list[NDArray[Any]]:
    """What the executor would hand the graph for each frame of `span`."""
    with VideoReader(video, luma=luma) as reader:
        return [
            np.array(ARENA.crop(reader.read(index).data)) for index in range(span.start, span.end)
        ]


class TestTheArtifactHoldsWhatTheGraphWouldHaveSeen:
    @pytest.mark.parametrize("luma", [False, True], ids=["bgr", "luma"])
    def test_every_frame_reads_back_as_the_crop_it_was_cut_from(
        self, synthetic_video: Path, tmp_path: Path, luma: bool
    ) -> None:
        """Both formats, frame for frame, against a second decode of the source.

        Byte-parity is not load-bearing for identity any more — the artifact is
        keyed as its own source — but it is what the codec measurement promised
        FFV1 delivers, and a regression to "close enough" would be a silent
        change to what every downstream number is computed from.
        """
        expected = _source_crops(synthetic_video, SPAN, luma=luma)

        artifact = materialize_crop(
            synthetic_video, _replicate(), SPAN, project_dir=tmp_path, luma=luma
        )

        with VideoReader(artifact.resolve(tmp_path), luma=luma) as reader:
            assert reader.metadata.frame_count == SPAN.frame_count
            for offset, fed in enumerate(expected):
                assert np.array_equal(reader.read(offset).data, fed)

    def test_artifact_frame_zero_is_the_span_start(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The one index translation there is, asserted on the fixture's ramp.

        Frame `n` of the fixture carries blue `n * 5`, so an artifact that
        started at frame 0 — or that was off by the lead-in of some plan — shows
        up here as a different colour, not merely as a different array.
        """
        artifact = materialize_crop(
            synthetic_video, _replicate(), SPAN, project_dir=tmp_path, luma=False
        )

        with VideoReader(artifact.resolve(tmp_path)) as reader:
            first = float(reader.read(0).data[:, :, 0].mean())
        with VideoReader(synthetic_video) as source:
            at_start = float(ARENA.crop(source.read(SPAN.start).data)[:, :, 0].mean())

        assert first == pytest.approx(at_start)

    def test_the_record_says_where_it_lives_and_what_it_was_cut_from(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        artifact = materialize_crop(
            synthetic_video, _replicate(), SPAN, project_dir=tmp_path, luma=True
        )

        assert artifact.format == "luma"
        assert artifact.roi == ARENA
        assert artifact.span == SPAN
        assert str(synthetic_video.name) in artifact.cut_from
        assert artifact.resolve(tmp_path).is_file()
        # Relative, so moving the folder is a rebase and not a search.
        assert not Path(artifact.path).is_absolute()


class TestAFileThatDoesNotReadBackIsRefused:
    def test_wrong_pixels_are_caught_even_though_the_file_is_valid(
        self, synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The qp0-gray failure class, simulated: right count, wrong content.

        Nothing about the encoder, the container, the frame count, or the shape
        is wrong here — only the pixels. If the read-back comparison were
        dropped, this artifact would be registered and every number computed
        from it would be wrong with no evidence anywhere.
        """

        def inverting_writer(path: Path, frames: Iterable[NDArray[Any]], *, fps: float) -> int:
            return write_ffv1(path, (255 - array for array in frames), fps=fps)

        monkeypatch.setattr(materialize_module, "write_ffv1", inverting_writer)

        with pytest.raises(CropVerificationError, match="different pixels"):
            materialize_crop(synthetic_video, _replicate(), SPAN, project_dir=tmp_path, luma=True)

        assert not list(tmp_path.glob("**/*.mkv"))

    def test_a_refused_write_leaves_no_artifact_at_the_final_name(
        self, synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A truncated encode must not be renamed into place."""

        def short_writer(path: Path, frames: Iterable[NDArray[Any]], *, fps: float) -> int:
            kept = list(frames)[:2]
            return write_ffv1(path, iter(kept), fps=fps)

        monkeypatch.setattr(materialize_module, "write_ffv1", short_writer)

        with pytest.raises(CropVerificationError, match="frames"):
            materialize_crop(synthetic_video, _replicate(), SPAN, project_dir=tmp_path, luma=True)

        assert not list(tmp_path.glob("**/*.mkv"))


class TestCancellation:
    def test_withdrawing_mid_write_leaves_no_part_file(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """A cancelled cut leaves the folder as it found it.

        A `.part.mkv` left behind is not merely litter: the next run writes to
        the same name, and a partial file that survived is one an interrupted
        session could later mistake for progress.
        """
        seen: list[int] = []

        def cancelled() -> bool:
            seen.append(len(seen))
            return len(seen) > 2

        with pytest.raises(MaterializeCancelledError):
            materialize_crop(
                synthetic_video,
                _replicate(),
                SPAN,
                project_dir=tmp_path,
                luma=True,
                cancelled=cancelled,
            )

        assert not list(tmp_path.glob("**/*.mkv"))


class TestTheCommand:
    def test_materialize_writes_and_registers_it_on_the_project(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """O3: the artifact is creatable headless, and the project knows about it.

        The registration is the half that is easy to leave out and expensive to
        notice: an artifact nothing points at is minutes of decode the next
        session silently pays again.
        """
        replicate = _replicate()
        project_path = tmp_path / "clip.sieve.yaml"
        (
            Project.for_video(synthetic_video, tmp_path)
            .with_replicates((replicate,))
            .with_clip(SPAN)
            .save(project_path)
        )

        result = runner.invoke(app, ["materialize", str(project_path), "--replicate", "Arena 1"])

        assert result.exit_code == 0, result.output
        saved = Project.load(project_path)
        (crop,) = saved.crops
        assert crop.backs(
            replicate,
            source=crop.cut_from,
            luma=True,
            project_dir=tmp_path,
        )

    def test_an_unknown_replicate_is_refused(self, synthetic_video: Path, tmp_path: Path) -> None:
        project_path = tmp_path / "clip.sieve.yaml"
        (
            Project.for_video(synthetic_video, tmp_path)
            .with_replicates((_replicate(),))
            .with_clip(SPAN)
            .save(project_path)
        )

        result = runner.invoke(app, ["materialize", str(project_path), "--replicate", "Arena 9"])

        assert result.exit_code == 1
        assert "no replicate named" in result.output
