














from __future__ import annotations

import csv
from pathlib import Path

from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.filter_base import ElementKind
from sieve.core.pipeline_model import DetectorSettings, Edge, Node, Pipeline, Project
from sieve.detect.tables import series_columns

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







    project = _project(synthetic_video, tmp_path, detector=None)

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 0, result.output
    assert "no detector" in result.output
    assert "0 intervals" not in result.output


def test_two_sinks_are_refused_rather_than_one_being_picked(
    synthetic_video: Path, tmp_path: Path
) -> None:






    project = _project(
        synthetic_video, tmp_path, detector=DetectorSettings(count_frac=(0.0, 1.0)), two_sinks=True
    )

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40"])

    assert result.exit_code == 1
    assert "--node" in result.output


def _rows(path: Path) -> list[dict[str, str]]:

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))







DETECTED = series_columns(ElementKind.BLOCK)[-1].name


def test_the_header_is_a_published_interface(synthetic_video: Path, tmp_path: Path) -> None:








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







    project = _project(synthetic_video, tmp_path, detector=DetectorSettings(window_frames=5))
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40", "--csv", str(out)])

    assert result.exit_code == 0, result.output
    assert not (out / "intervals.csv").exists()
    assert {row[DETECTED] for row in _rows(out / "series.csv")} == {"NA"}


def test_csv_against_an_untuned_project_is_refused_before_any_decode(
    synthetic_video: Path, tmp_path: Path
) -> None:






    project = _project(synthetic_video, tmp_path, detector=None)
    out = tmp_path / "tables"

    result = runner.invoke(app, ["detect", str(project), "--frames", "0:40", "--csv", str(out)])

    assert result.exit_code == 1
    assert not out.exists()





_SHRUNK = (
    SERIES_NODE,
    Node(node_id="small", filter_id="downsample", version="1.0.0", params={"factor": 2}),
)
_SHRUNK_EDGES = (Edge(upstream="blocks", downstream="small"),)


def test_a_node_whose_elements_have_no_meaning_is_refused(
    synthetic_video: Path, tmp_path: Path
) -> None:


















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


    assert "| `pixels_in_band` |" in (out / "README.md").read_text(encoding="utf-8")
