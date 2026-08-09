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

`TestTheCommandDerivesWhatV2WasHanded` is the other end of the same file: the
writer takes a region, a span and a format as arguments, and every one of the
three is something `sieve materialize` has to *derive* from a document that
records none of them directly. Here rather than in a module of its own because
the failure it guards against is a file — a cut of the wrong box, over the wrong
frames, that nothing points at — and what proves it is opening that file.
"""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray
from typer.testing import CliRunner, Result

from sieve.cli.app import app
from sieve.core.pipeline_model import Edge, Node, Pipeline, Project, Replicate, SourceSpan
from sieve.core.types import ROI, FrameIndex, FrameSpan
from sieve.decode.reader import VideoReader
from sieve.pipeline import materialize as materialize_module
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.materialize import (
    CropVerificationError,
    MaterializeCancelledError,
    materialize_crop,
)
from sieve.pipeline.plan import ExecutionPlan
from sieve.storage.crop_writer import write_ffv1
from sieve.tools import discover
from sieve.tools.crop import CropParams
from sieve.tools.crop import run as crop_frame
from tests.conftest import FIXTURE_FPS, FIXTURE_FRAMES

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


runner = CliRunner()

PROJECT_NAME = "arena.sieve.yaml"
CUT = "cut"
DOWN = "down"
KEEP = "keep"
SIGNAL = "signal"
GATE = "gate"

#: The crop node carries no region of its own — `crop.WHOLE_FRAME` is its
#: default, which is the identity crop as a value — and the replicate pins the
#: box. That is where geometry lives under schema v1
#: (`adr/detector-is-a-node.md`), and it is what makes the derivation a
#: derivation: a command reading the document would cut the whole frame. The
#: `span` node is the other half — schema v1 records no frame range of its own,
#: so the frames are a node's parameters like everything else.
GRAPH = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
        Node(
            node_id=KEEP,
            tool_id="span",
            version="1.0.0",
            params={"frames": [SPAN.start, SPAN.end]},
        ),
    ),
    edges=(Edge(upstream=CUT, downstream=DOWN), Edge(upstream=DOWN, downstream=KEEP)),
)

#: `detect`'s band, chosen for `test_cli_run.py`'s reason: the transform's reach
#: is charged at the band's low edge, so the wide-open default would want more
#: frames either side of every target than the 40-frame fixture holds.
DETECT_BAND = (10.0, 14.0)

#: The frames `WINDOWED_GRAPH` answers for. Far enough inside the fixture that
#: the window either side of it is legal footage.
WINDOWED_SPAN = SourceSpan(start=16, end=20)

#: The graph `GRAPH` is not: `crop -> downsample` streams, so its decode range
#: *is* its span and a command cutting either would pass every case above. Here
#: the detector reads well past and well behind every frame it answers for.
WINDOWED_GRAPH = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id=SIGNAL, tool_id="block_signal", version="1.0.0", params={"fps": FIXTURE_FPS}),
        Node(
            node_id=GATE,
            tool_id="detect",
            version="1.0.0",
            params={"freq_band": DETECT_BAND, "window_frames": 3, "fps": FIXTURE_FPS},
        ),
        Node(
            node_id=KEEP,
            tool_id="span",
            version="1.0.0",
            params={"frames": [WINDOWED_SPAN.start, WINDOWED_SPAN.end]},
        ),
    ),
    edges=(
        Edge(upstream=CUT, downstream=SIGNAL),
        Edge(upstream=SIGNAL, downstream=GATE),
        Edge(upstream=GATE, downstream=KEEP),
    ),
)

#: A crop of another node's output rather than of the footage, which is a crop of
#: something no file on disk holds.
NO_ROOT_CROP = Pipeline(
    nodes=(
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
    ),
    edges=(Edge(upstream=DOWN, downstream=CUT),),
)

#: Two boxes at the root and nothing in the document to choose between them.
TWO_ROOT_CROPS = Pipeline(
    nodes=(
        Node(node_id=CUT, tool_id="crop", version="1.0.0"),
        Node(node_id="other", tool_id="crop", version="1.0.0"),
        Node(node_id=DOWN, tool_id="downsample", version="1.0.0", params={"factor": 2}),
    ),
    edges=(Edge(upstream=CUT, downstream=DOWN),),
)


def _replicate(region: ROI = ARENA) -> Replicate:
    pinned = {"x": region.x, "y": region.y, "width": region.width, "height": region.height}
    return Replicate(name=NAME, replicate_id="a").with_override(CUT, {"region": pinned})


def _project(
    video: Path,
    directory: Path,
    *,
    pipeline: Pipeline = GRAPH,
    replicate: Replicate | None = None,
) -> Path:
    """Write a one-arena project over `video` into `directory`, and return its path."""
    target = _replicate() if replicate is None else replicate
    project = Project.for_video(video, directory).with_pipeline(pipeline).with_replicates((target,))
    path = directory / PROJECT_NAME
    project.save(path)
    return path


def _materialize(project_path: Path, replicate: str = NAME) -> Result:
    return runner.invoke(app, ["materialize", str(project_path), "--replicate", replicate])


def _reads(pipeline: Pipeline, replicate: Replicate) -> SourceSpan:
    """The source frames a whole-video run of `pipeline` decodes, window included.

    Derived here the way the command derives it rather than written down, because
    the numbers are the detector's own declarations and a literal would be a
    second copy of them going stale on its own schedule.
    """
    discover()
    reading = ExecutionPlan.build(
        Dag.build(pipeline),
        source="",
        span=SourceSpan(start=0, end=FIXTURE_FRAMES),
        replicate=replicate,
        source_end=FrameIndex(FIXTURE_FRAMES),
    ).decode_range
    return SourceSpan(start=int(reading.start), end=int(reading.stop))


class TestTheCommandDerivesWhatV2WasHanded:
    """Region, span and format: three arguments, none of them in the document.

    v2's command read a frame range off the project and an `roi` off the
    replicate, and schema v1 records neither. What is asserted here is that each
    one comes out of the graph as resolved for this replicate — and, where the
    graph does not determine it, that the command says so rather than cutting
    something plausible.
    """

    def test_the_command_cuts_the_box_the_replicate_pins_over_the_graphs_span(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Both derivations at once, read back off the file rather than the record.

        The two failures a command trusting the document would make are visible
        here as sizes: `crop.WHOLE_FRAME` is the node's own region, so a
        derivation skipping the override writes a 160x120 file, and a span read
        off a project that records none writes all forty frames.
        """
        project_path = _project(synthetic_video, tmp_path)

        result = _materialize(project_path)

        assert result.exit_code == 0, result.output
        record = Project.load(project_path).crops[0]
        with VideoReader(record.resolve(tmp_path), luma=True) as reader:
            assert (reader.metadata.width, reader.metadata.height) == (ARENA.width, ARENA.height)
            assert reader.metadata.frame_count == SPAN.frame_count
        assert record.region == ARENA
        assert record.span == SPAN

    def test_the_command_registers_what_it_cut_in_the_project_it_saves(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """The half that is easy to leave out and expensive to notice.

        A written file nothing points at is minutes of decode the next session
        pays again in silence, and the only thing that can say the pointer works
        is the matching rule itself, asked of a document that has been through
        YAML and back.
        """
        project_path = _project(synthetic_video, tmp_path)

        assert _materialize(project_path).exit_code == 0

        reloaded = Project.load(project_path)
        assert len(reloaded.crops) == 1
        assert reloaded.crops[0].backs(
            ARENA, source=source_identity(synthetic_video), luma=True, project_dir=tmp_path
        )

    def test_the_command_cuts_the_window_the_graph_reads_not_only_its_span(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """A file cut to the answer alone is a file the next run declines.

        `resolve` matches a record against the frames a run *reads* — its span
        widened by every window in the graph — and declines one that misses them
        at either end, so a command cutting `plan.span` would write an artifact
        that serves nothing and be re-run every time. The first assertion is what
        makes the second mean anything: under `GRAPH` the two spans are equal and
        this case would pass against either derivation.
        """
        replicate = _replicate()
        reads = _reads(WINDOWED_GRAPH, replicate)
        project_path = _project(
            synthetic_video, tmp_path, pipeline=WINDOWED_GRAPH, replicate=replicate
        )

        assert _materialize(project_path).exit_code == 0

        assert reads.frame_count > WINDOWED_SPAN.frame_count
        assert Project.load(project_path).crops[0].span == reads

    def test_the_command_derives_the_format_and_offers_no_flag_for_it(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """`--format` is the one option that must never exist.

        No tool on the shelf declares a chroma-only input (`Dag.needs_chroma`),
        so every graph today is a luma graph and the derived value cannot be
        contrasted against a colour one. What can be asserted is the thing that
        would make the derivation defeatable — an option letting a user write a
        colour file for a luma session, which is the combination v2's codec
        finding proved reads back as plausible wrong pixels.
        """
        project_path = _project(synthetic_video, tmp_path)

        assert _materialize(project_path).exit_code == 0

        assert Project.load(project_path).crops[0].format == "luma"
        assert "--format" not in runner.invoke(app, ["materialize", "--help"]).output

    def test_the_command_refuses_a_graph_with_no_crop_reading_the_source(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """A crop of another node's output is a crop of something no file holds.

        The graph here *has* a crop node, so a refusal keyed on the tool being
        absent would pass this case while cutting a box that stands for nothing.
        """
        project_path = _project(
            synthetic_video,
            tmp_path,
            pipeline=NO_ROOT_CROP,
            replicate=Replicate(name=NAME, replicate_id="a"),
        )

        result = _materialize(project_path)

        assert result.exit_code == 1
        assert "no crop node reading the source" in result.stderr
        assert not list(tmp_path.glob("**/*.mkv"))

    def test_the_command_refuses_a_graph_with_two_crops_reading_the_source(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Two boxes are two answers, and picking one writes a file that lies.

        Both node ids are named because the fix is an edit to the graph, and a
        message saying only that the graph is ambiguous leaves the reader to find
        which two nodes made it so.
        """
        project_path = _project(synthetic_video, tmp_path, pipeline=TWO_ROOT_CROPS)

        result = _materialize(project_path)

        assert result.exit_code == 1
        assert CUT in result.stderr
        assert "other" in result.stderr
        assert not list(tmp_path.glob("**/*.mkv"))

    def test_the_command_refuses_a_replicate_that_pins_no_region(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Cutting the graph's own box and filing it under one arena's name.

        The graph resolves perfectly well here — `crop.WHOLE_FRAME` is a legal
        region — so nothing downstream would refuse it: the command would write
        the whole frame, record it as this replicate's cut, and go on serving it
        to every other replicate that had pinned the same nothing.
        """
        project_path = _project(
            synthetic_video, tmp_path, replicate=Replicate(name=NAME, replicate_id="a")
        )

        result = _materialize(project_path)

        assert result.exit_code == 1
        assert "overrides no region" in result.stderr
        assert not list(tmp_path.glob("**/*.mkv"))

    def test_the_command_refuses_a_name_no_replicate_answers_to(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Named before a container is opened, and saying what the project holds."""
        project_path = _project(synthetic_video, tmp_path)

        result = _materialize(project_path, replicate="Arena 9")

        assert result.exit_code == 1
        assert NAME in result.stderr
