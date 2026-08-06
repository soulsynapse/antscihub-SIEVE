"""`sieve detect` from a YAML file on disk to intervals, with no Qt in the room.

The claim `docs/todo/headless-detection.md` made is not "detection is correct" —
`tests/unit/test_detection.py` and `tests/unit/test_partial_detector.py` own
that — it is that a *document* can be detected against without a GUI. So these
tests type the command a cluster job would type, and what they can catch is the
seam between a saved `DetectorSettings` and the derivation: a detector that is
absent rendering as zero intervals, a disarmed one rendering as "found nothing",
and a graph whose series node is ambiguous being picked for silently.

Not marked `gui`, deliberately, and that is half the point: before
`sieve.detect` existed there was no import path from a project to intervals
that did not go through `sieve.gui`.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import cast

from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.filter_base import ElementNames
from sieve.core.pipeline_model import DetectorSettings, Edge, Node, Pipeline, Project
from sieve.detect.tables import series_columns
from sieve.filters.block_signal import BlockSignalParams

runner = CliRunner()

SERIES_NODE = Node(
    node_id="blocks",
    filter_id="block_signal",
    version="1.0.0",
    params={"block": 16, "fps": 20.0},
)


def _project(
    video: Path,
    directory: Path,
    *,
    detector: DetectorSettings | None,
    two_sinks: bool = False,
    nodes: tuple[Node, ...] = (SERIES_NODE,),
    edges: tuple[Edge, ...] = (),
) -> Path:
    """Write a project beside `video` and return its path.

    Defaults to the one-node block-signal graph every detection test used
    before the series node had to declare what its values are; `nodes`/`edges`
    are how the tests about *that* build a chain instead.
    """
    if two_sinks:
        nodes = (*nodes, SERIES_NODE.model_copy(update={"node_id": "blocks2"}))
    project = Project.for_video(video, directory).with_pipeline(Pipeline(nodes=nodes, edges=edges))
    if detector is not None:
        project = project.model_copy(update={"detector": detector})
    path = directory / "arena.sieve.yaml"
    project.save(path)
    return path


def test_an_armed_project_prints_intervals_without_a_gui(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The whole item: a saved threshold becomes intervals from a shell.

    The fixture ramps its blue channel linearly, so change energy is flat and
    a threshold spanning the whole population gates every settled frame — the
    interval count is not the assertion, the fact that one was computed at all
    is. Fails if the derivation is still only reachable through a Qt widget.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        detector=DetectorSettings(count_frac=(0.0, 1.0), window_frames=5, centered=True),
    )

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 0, result.output
    assert "interval" in result.output
    assert "disarmed" not in result.output


def test_an_untuned_project_says_so_rather_than_claiming_nothing(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """`Project.detector` unset is *never tuned*, and must not read as zero.

    The one output a wrong answer would look identical to a right one in:
    "0 intervals" from a project that never had a threshold is a claim about
    the footage that nothing ever made. Rule 6, at the one field that
    documents a `None`.
    """
    project = _project(synthetic_video, tmp_path, detector=None)

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 0, result.output
    assert "no detector" in result.output
    assert "0 intervals" not in result.output


def test_two_sinks_are_refused_rather_than_one_being_picked(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """Which series a detection was taken over is part of what it means.

    Fails if `_series_node` falls back to the last node in topological order,
    which is the plausible implementation and the one that makes the choice
    invisible in the output.
    """
    project = _project(
        synthetic_video, tmp_path, detector=DetectorSettings(count_frac=(0.0, 1.0)), two_sinks=True
    )

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 1
    assert "--node" in result.output


def _rows(path: Path) -> list[dict[str, str]]:
    """Read a written table the way something that is not SIEVE would."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


#: Referenced through the module constant, not spelled, in the tests below.
#: A rename then breaks `test_the_header_is_a_published_interface` and nothing
#: else — one deliberate diff naming exactly what a downstream script must
#: change, rather than five tests failing on a `KeyError` that says nothing
#: about whether the rename was intended.
BLOCK_NAMES = cast(ElementNames, BlockSignalParams.spec().element_names)
DETECTED = series_columns(BLOCK_NAMES)[-1].name


def test_the_header_is_a_published_interface(synthetic_video: Path, tmp_path: Path) -> None:
    """The written header is these names in this order, spelled out once.

    The one test that is *supposed* to fail on a rename, because the header is
    not an internal detail: an R script reading `windowed_mean_fraction` breaks
    on the same change, and it has no test suite here to say so. Spelled as
    literals rather than compared to the constants they came from — asserting
    `SERIES_COLUMNS == SERIES_COLUMNS` would pass through any rename at all.
    """
    project = _project(synthetic_video, tmp_path, detector=DetectorSettings(count_frac=(0.0, 1.0)))
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40", "--csv", str(out)])

    assert result.exit_code == 0, result.output
    with (out / "series.csv").open(encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == [
            "replicate",
            "node_id",
            "filter",
            "frame",
            "time_seconds",
            "blocks_total",
            "blocks_in_band",
            "blocks_in_band_fraction",
            "windowed_mean_blocks",
            "windowed_mean_fraction",
            "detected",
        ]
    with (out / "intervals.csv").open(encoding="utf-8", newline="") as handle:
        assert next(csv.reader(handle)) == [
            "replicate",
            "node_id",
            "filter",
            "start_frame",
            "end_frame_exclusive",
            "start_seconds",
            "end_seconds",
            "duration_frames",
            "duration_seconds",
        ]


def test_csv_carries_the_series_the_summary_only_counts(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """One row per frame, in absolute frames, readable by stdlib csv alone.

    The claim is the one `docs/todo/parity-comparison-finding.md` needs and
    stdout cannot make: not that intervals were found, but that the per-frame
    count and gate a later run is diffed against actually left the process.
    Fails if the export summarises rather than emits — a file of intervals
    only would still print "wrote" and satisfy the armed test above.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        detector=DetectorSettings(count_frac=(0.0, 1.0), window_frames=5, centered=True),
    )
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "10:40", "--csv", str(out)])

    assert result.exit_code == 0, result.output
    series = _rows(out / "series.csv")
    assert len(series) == 30
    assert [int(row["frame"]) for row in series] == list(range(10, 40))
    assert {row["node_id"] for row in series} == {"blocks"}
    assert {row[DETECTED] for row in series} <= {"TRUE", "FALSE"}
    intervals = _rows(out / "intervals.csv")
    assert all(int(row["start_frame"]) < int(row["end_frame_exclusive"]) for row in intervals)


def test_a_disarmed_detector_writes_no_intervals_file(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """Rule 6 at the file boundary: absent must not arrive as empty.

    A header-only `intervals.csv` is indistinguishable from an armed run that
    found nothing, and a reader in R would not know to ask. The series is
    still real and is still written, with `detected` as `NA` — the value R and
    pandas both already read as absent, rather than `FALSE`.
    """
    project = _project(synthetic_video, tmp_path, detector=DetectorSettings(window_frames=5))
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40", "--csv", str(out)])

    assert result.exit_code == 0, result.output
    assert not (out / "intervals.csv").exists()
    assert {row[DETECTED] for row in _rows(out / "series.csv")} == {"NA"}


def test_csv_against_an_untuned_project_is_refused_before_any_decode(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """No detector means no series either, so there is nothing to write.

    Refused up front rather than after the run: the alternative that looks
    reasonable is writing `series.csv` anyway, and the counts are taken
    inside the value band, so those columns do not exist to be written.
    """
    project = _project(synthetic_video, tmp_path, detector=None)
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40", "--csv", str(out)])

    assert result.exit_code == 1
    assert not out.exists()


#: A chain whose sink aggregates a block grid: `block_signal` makes blocks,
#: `downsample` averages four of them into one, and a mean of blocks is not a
#: block. The invocation `docs/todo/what-one-element-means.md` opened on.
_SHRUNK = (
    SERIES_NODE,
    Node(node_id="small", filter_id="downsample", version="1.0.0", params={"factor": 2}),
)
_SHRUNK_EDGES = (Edge(upstream="blocks", downstream="small"),)


def test_a_node_whose_elements_have_no_meaning_is_refused(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The count is real and the noun would be invented, so there is no count.

    Before the declaration this ran to completion and wrote `blocks_total`
    over a number that counts neither blocks nor pixels — the numbers real,
    the label a lie, and the lie on disk after the session ended. Rule 6 at
    the one boundary where a wrong answer outlives the run.

    Refused *before* any decode, which is the second half: paying for a
    thirty-second pass and then declining to name it would be a worse version
    of the same answer.

    The message has to name `small`, and asserting that is not decoration.
    `downsample` declares `AGGREGATED` — it is `block_signal` upstream that
    makes aggregating meaningless — so a refusal phrased as "this filter does
    not declare" is wrong every time it fires, and sends the reader to a file
    that is fine. An array emitter cannot be registered without a declaration,
    so a lost meaning is always the chain's and never the node's own omission.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        detector=DetectorSettings(count_frac=(0.0, 1.0)),
        nodes=_SHRUNK,
        edges=_SHRUNK_EDGES,
    )
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40", "--csv", str(out)])

    assert result.exit_code == 1
    assert "lost it at small (downsample" in result.output
    assert "does not declare" not in result.output
    assert not out.exists()


def test_a_pixel_series_names_its_columns_for_pixels(synthetic_video: Path, tmp_path: Path) -> None:
    """The other half, and the one a refusal-only change would have missed.

    `downsample` straight off the source emits a coarser grid of *pixels*, so
    the count is honest and the only thing that was ever wrong is the noun.
    Naming it `pixels_in_band` is what makes this a declaration read from the
    pipeline rather than a whitelist of nodes `tables.py` approves of — and
    the alternative, a shape-neutral `units_in_band`, would be honest and
    unreadable, which is the trade rule 6 exists to refuse.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        detector=DetectorSettings(count_frac=(0.0, 1.0)),
        nodes=(
            Node(node_id="small", filter_id="downsample", version="1.0.0", params={"factor": 8}),
        ),
    )
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:4", "--csv", str(out)])

    assert result.exit_code == 0, result.output
    with (out / "series.csv").open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle))
    assert "pixels_in_band" in header
    assert "pixels_total" in header
    assert not any(name.startswith("blocks") for name in header)
    # And the data dictionary is a rendering of whatever was written, so it
    # follows the rename without anybody maintaining a second table.
    assert "| `pixels_in_band` |" in (out / "README.md").read_text(encoding="utf-8")
