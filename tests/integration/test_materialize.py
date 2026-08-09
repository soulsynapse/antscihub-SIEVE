"""The crop writer end to end: a real decode, a real encode, a real read-back.

An integration test because every part of the claim is about a file. The
question is not whether the arithmetic is right — there is none — but whether the
bytes that leave `VideoReader`, pass through PyAV, and come back through
`VideoReader` are the same bytes, in both decode formats, and whether the
verification pass actually catches the case where they are not.

That last one is the load-bearing test in this module. v2's codec finding
measured a *lossless* encoding whose frames came back wrong through the same
reader with the right shape and the right count — so a writer that trusted its
encoder would have registered it. The refusal test simulates exactly that: right
file, right frame count, wrong pixels.

The record's own model is not the subject here — `TestCropRecords` in
`tests/unit/test_pipeline_model.py` owns it, and the pixel round trip through
`write_ffv1` alone is `tests/unit/test_crop_artifact.py`'s. What is asserted
below is the join: the file holds what the graph would have seen, the record
points at it, and neither exists when the write went wrong.
"""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from sieve.core.pipeline_model import SourceSpan
from sieve.core.types import ROI, FrameSpan
from sieve.decode.reader import VideoReader
from sieve.pipeline import materialize as materialize_module
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.materialize import (
    CropVerificationError,
    MaterializeCancelledError,
    materialize_crop,
)
from sieve.storage.crop_writer import write_ffv1
from sieve.tools.crop import CropParams
from sieve.tools.crop import run as crop_frame

#: Wholly inside the 160x120 fixture and at an odd origin in both axes, so a
#: codec that quietly re-aligned the crop to a macroblock grid would show up.
ARENA = ROI(x=17, y=9, width=64, height=48)
SPAN = SourceSpan(start=10, end=16)
NAME = "Arena 1"


def _source_crops(video: Path, span: SourceSpan, *, luma: bool) -> list[NDArray[Any]]:
    """What the graph would be handed for each frame of `span`.

    Reached through the crop tool rather than through a slice written here, for
    the reason `materialize._cropped` reaches through it: a second spelling of
    the clamp would make this test agree with itself instead of with the graph.
    """
    params = CropParams(region=ARENA)
    with VideoReader(video, luma=luma) as reader:
        return [
            np.array(crop_frame(params, FrameSpan((reader.read(index),)), None).data)
            for index in range(span.start, span.end)
        ]


class TestTheArtifactHoldsWhatTheGraphWouldHaveSeen:
    @pytest.mark.parametrize("luma", [False, True], ids=["bgr", "luma"])
    def test_every_frame_reads_back_as_the_crop_it_was_cut_from(
        self, synthetic_video: Path, tmp_path: Path, luma: bool
    ) -> None:
        """Both formats, frame for frame, against a second decode of the source.

        Byte-parity is not load-bearing for identity — the artifact is keyed as
        its own source — but it is what the codec measurement promised FFV1
        delivers, and a regression to "close enough" would be a silent change to
        what every downstream number is computed from.
        """
        expected = _source_crops(synthetic_video, SPAN, luma=luma)

        record = materialize_crop(
            synthetic_video, ARENA, SPAN, name=NAME, project_dir=tmp_path, luma=luma
        )

        with VideoReader(record.resolve(tmp_path), luma=luma) as reader:
            assert reader.metadata.frame_count == SPAN.frame_count
            for offset, fed in enumerate(expected):
                assert np.array_equal(reader.read(offset).data, fed), f"frame {offset} differs"

    def test_artifact_frame_zero_is_the_span_start(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The one index translation there is, asserted on the fixture's ramp.

        Frame `n` of the fixture carries blue `n * 5`, so an artifact that
        started at frame 0 — or that was off by the lead-in of some plan — shows
        up here as a different colour, not merely as a different array.
        """
        record = materialize_crop(
            synthetic_video, ARENA, SPAN, name=NAME, project_dir=tmp_path, luma=False
        )

        with VideoReader(record.resolve(tmp_path)) as reader:
            first = float(reader.read(0).data[:, :, 0].mean())
        at_start = float(_source_crops(synthetic_video, SPAN, luma=False)[0][:, :, 0].mean())

        assert first == pytest.approx(at_start)

    def test_the_record_says_where_it_lives_and_what_it_was_cut_from(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        record = materialize_crop(
            synthetic_video, ARENA, SPAN, name=NAME, project_dir=tmp_path, luma=True
        )

        assert record.format == "luma"
        assert record.region == ARENA
        assert record.span == SPAN
        assert record.cut_from == source_identity(synthetic_video)
        assert record.resolve(tmp_path).is_file()
        # Relative, so moving the folder is a rebase and not a search.
        assert not Path(record.path).is_absolute()

    def test_a_region_overhanging_the_frame_is_recorded_as_drawn_not_as_cut(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """`CropRecord.region`'s rule, on the only path that can break it.

        The clamp is a function of the frame that arrived, and the executor
        applies the identical one, so a record storing the clamped result would
        describe a box the user never drew — and `backs` would then miss the very
        file it was written for. The file is the clamped size; the record is not.
        """
        overhang = ROI(x=130, y=100, width=64, height=48)

        record = materialize_crop(
            synthetic_video, overhang, SPAN, name=NAME, project_dir=tmp_path, luma=True
        )

        assert record.region == overhang
        with VideoReader(record.resolve(tmp_path), luma=True) as reader:
            assert (reader.metadata.width, reader.metadata.height) == (30, 20)
        assert record.backs(overhang, source=record.cut_from, luma=True, project_dir=tmp_path)

    def test_the_artifact_is_a_source_with_an_identity_of_its_own(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """What "it opens in SIEVE as an ordinary source" has to mean.

        Two claims in one, because either alone would be satisfied by the wrong
        thing: the file's identity is its own rather than the parent's — so a run
        against it re-keys instead of colliding — and the whole file is the
        region, so nothing downstream needs to know it was cut from anything.
        """
        record = materialize_crop(
            synthetic_video, ARENA, SPAN, name=NAME, project_dir=tmp_path, luma=True
        )
        artifact = record.resolve(tmp_path)

        assert source_identity(artifact) != record.cut_from
        with VideoReader(artifact, luma=True) as reader:
            assert (reader.metadata.width, reader.metadata.height) == (ARENA.width, ARENA.height)
            assert reader.metadata.frame_count == SPAN.frame_count


class TestAFileThatDoesNotReadBackIsRefused:
    def test_wrong_pixels_are_caught_even_though_the_file_is_valid(
        self, synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The lossless-but-wrong failure class, simulated: right count, wrong content.

        Nothing about the encoder, the container, the frame count, or the shape
        is wrong here — only the pixels. If the read-back comparison were
        dropped, this artifact would be registered and every number computed from
        it would be wrong with no evidence anywhere.
        """

        def inverting_writer(path: Path, frames: Iterable[NDArray[Any]], *, fps: Fraction) -> int:
            return write_ffv1(path, (255 - array for array in frames), fps=fps)

        monkeypatch.setattr(materialize_module, "write_ffv1", inverting_writer)

        with pytest.raises(CropVerificationError, match="different pixels"):
            materialize_crop(
                synthetic_video, ARENA, SPAN, name=NAME, project_dir=tmp_path, luma=True
            )

        assert not list(tmp_path.glob("**/*.mkv"))

    def test_a_refused_write_leaves_no_artifact_at_the_final_name(
        self, synthetic_video: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A truncated encode must not be renamed into place."""

        def short_writer(path: Path, frames: Iterable[NDArray[Any]], *, fps: Fraction) -> int:
            kept = list(frames)[:2]
            return write_ffv1(path, iter(kept), fps=fps)

        monkeypatch.setattr(materialize_module, "write_ffv1", short_writer)

        with pytest.raises(CropVerificationError, match="frames"):
            materialize_crop(
                synthetic_video, ARENA, SPAN, name=NAME, project_dir=tmp_path, luma=True
            )

        assert not list(tmp_path.glob("**/*.mkv"))


class TestTwoCutsThatShareANameAndSpan:
    def test_two_regions_under_one_name_and_span_do_not_collide_on_one_file(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Distinct cuts get distinct files, and the older record keeps telling the truth.

        The verification pass cannot reach this: at the moment it runs the file
        genuinely is what was fed to it, and the lie appears afterwards in the
        *first* record, which nothing re-checks
        (`findings/2026.08.07-two-crops-of-one-name-and-span-write-one-file-and-backs-still-says-yes.md`).
        So what is asserted is the write, not the guard.

        The two regions differ in size and not only in origin because
        `synthetic_video` is spatially uniform
        (`findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md`):
        under it a read-back shape is the only thing that can tell one region's
        pixels from another's.
        """
        other = ROI(x=0, y=0, width=32, height=24)

        first = materialize_crop(
            synthetic_video, ARENA, SPAN, name=NAME, project_dir=tmp_path, luma=True
        )
        second = materialize_crop(
            synthetic_video, other, SPAN, name=NAME, project_dir=tmp_path, luma=True
        )

        assert first.identity() != second.identity()
        assert first.path != second.path
        for record, region in ((first, ARENA), (second, other)):
            with VideoReader(record.resolve(tmp_path), luma=True) as reader:
                assert (reader.metadata.width, reader.metadata.height) == (
                    region.width,
                    region.height,
                )
            assert record.backs(region, source=record.cut_from, luma=True, project_dir=tmp_path)


class TestTheTwoCallbacksALongWriteOffers:
    def test_withdrawing_mid_write_reports_its_progress_and_leaves_no_part_file(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """A cancelled cut leaves the folder as it found it, having said how far it got.

        A `.part.mkv` left behind is not merely litter: the next run writes to the
        same name, and a partial file that survived is one an interrupted session
        could later mistake for progress. The progress reports are asserted here
        rather than in a case of their own because the two callbacks exist for
        one reason — a write long enough that somebody is watching it — and the
        cancellation is what bounds how many of them there should be.
        """
        polls = 0
        reported: list[tuple[int, int]] = []

        def cancelled() -> bool:
            nonlocal polls
            polls += 1
            return polls > 2

        with pytest.raises(MaterializeCancelledError, match="after 2 frames"):
            materialize_crop(
                synthetic_video,
                ARENA,
                SPAN,
                name=NAME,
                project_dir=tmp_path,
                luma=True,
                cancelled=cancelled,
                progress=lambda done, total: reported.append((done, total)),
            )

        assert reported == [(1, SPAN.frame_count), (2, SPAN.frame_count)]
        assert not list(tmp_path.glob("**/*.mkv"))
