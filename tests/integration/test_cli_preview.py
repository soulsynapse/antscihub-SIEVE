"""`sieve preview` over a real video, which is where the seams are.

`tests/unit/test_preview.py` pins the session's arithmetic against a
hand-written `run`. What this adds is everything between a document on disk and
that session — the replicate a project has to be read to find, the two writes
`--edit` performs through `with_param_edit`, a real prefetching reader
satisfying `FrameSource`, and a `MetricBus` hearing keys `pipeline/preview.py`
names as string literals because it may not import the budget table.

The last of those is the one only an integration test can catch: a misspelled
key raises `KeyError` at publish, so the first render against a real bus is
where it surfaces, and that render happens here.

v2's file holds **3 cases** and all three survive. What is added is one case per
flag this command keeps that v2's file never invoked — `--at`, `--replicate`,
and the value a tool refuses — because `adr/declared-means-verified.md` is the
reason `--backend`, `--workers` and `--check` are not on the command at all, and
a kept flag no case types is the same claim wearing a different hat.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import Result
from typer.testing import CliRunner

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import Recorder, Sample
from sieve.cli.app import app
from sieve.cli.preview_cmd import _timings
from sieve.core.pipeline_model import Edge, Node, Pipeline, Replicate
from tests.projects import project_over

runner = CliRunner()


def _invoke(project: Path, *flags: str) -> Result:
    """The `preview` invocation for `project`, so no case respells the verb."""
    return runner.invoke(app, ["preview", str(project), *flags])


def _pipeline() -> Pipeline:
    """A two-node chain, so a suffix and the graph are different things."""
    return Pipeline(
        nodes=(
            Node(node_id="head", tool_id="downsample", version="1.0.0", params={"factor": 2}),
            Node(node_id="tail", tool_id="downsample", version="1.0.0", params={"factor": 2}),
        ),
        edges=(Edge(upstream="head", downstream="tail"),),
    )


def _project(
    video: Path, directory: Path, *, replicates: tuple[Replicate, ...] = (), name: str = "arena"
) -> Path:
    project = project_over(video, directory, _pipeline()).with_replicates(replicates)
    path = directory / f"{name}.sieve.yaml"
    project.save(path)
    return path


def _arena_project(video: Path, directory: Path) -> Path:
    """One replicate that already pins the parameter `--edit` will move.

    The pin is the point rather than decoration: it is what separates a session
    re-aimed at the edited document from one still holding the replicate as it
    was before the edit. See `test_an_edit_below_the_root_is_reported_as_a_half_reuse`.
    """
    return _project(
        video,
        directory,
        replicates=(
            Replicate(replicate_id="a", name="arena 1", overrides={"tail": {"factor": 2}}),
        ),
    )


def test_a_repeated_render_reuses_the_store_and_reports_both_budgets(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """One session, two renders, and the second computes nothing.

    The second render is where the store earns its place: every key is
    unchanged, so eight node outputs come back from it and no frame is decoded.
    A command that built a session per render would print these same two lines
    with 0% reuse on both and no other symptom.

    Both budget keys appear because a window render publishes both — and they
    appear at all only if the literals in `preview.py` name budgets the bus
    recognises, which is the assertion no unit test of that module can make.
    They are keys and not the table's human labels because those contain an
    arrow and an en dash, and printing them crashes a cp1252 Windows console.
    """
    project = _arena_project(synthetic_video, tmp_path)

    result = _invoke(project, "--frames", "10:14", "--repeat", "2")

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    # Three nodes and twelve outputs: the footage is a root of the graph now
    # (`adr/a-document-names-footage-only-through-a-tool.md`), so the chain the
    # command reports is one longer than the tools the case wired.
    assert lines[0] == "arena 1: window 10:14, 3 nodes"
    assert lines[1] == "render 1: 4 frames 10:14, 12 node outputs computed, 0 from cache (0% reuse)"
    assert (
        lines[2] == "render 2: 4 frames 10:14, 0 node outputs computed, 12 from cache (100% reuse)"
    )
    assert "slider_to_preview: median" in result.output
    assert "full_preview_render: median" in result.output
    assert result.output.isascii()


def test_an_edit_below_the_root_is_reported_as_a_half_reuse(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The claim the module exists for, at the layer a user types.

    `--edit tail:factor=4` moves the downstream node's parameters, so the head's
    four entries are found and the tail's four are computed. 50% reuse of a
    two-node chain is a suffix; 0% would be the graph.

    The replicate here already pins `tail.factor`, which is what makes this a
    test of `_aim` as well: an edit writes the new value to the node's default
    *and* to the replicate's pin, so a session still holding the pre-edit
    replicate resolves the stale pin over the new default, renders the unedited
    graph, and reports 100% reuse — an edit that did nothing, described as a
    perfect cache.
    """
    project = _arena_project(synthetic_video, tmp_path)

    result = _invoke(project, "--frames", "10:14", "--repeat", "2", "--edit", "tail:factor=4")

    assert result.exit_code == 0, result.output
    assert (
        "render 2: 4 frames 10:14 after tail:factor=4, 4 node outputs computed, "
        "8 from cache (67% reuse)" in result.output
    )


def test_an_edit_of_a_project_with_no_replicates_moves_the_node_itself(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """The other branch of `_apply`: no replicate means nothing to pin.

    Separate from the case above because the two branches write to different
    halves of the document and only one of them goes through
    `Project.with_param_edit`. A baseline project whose edit silently did
    nothing would print 100% reuse, which is the reading a working cache also
    produces.
    """
    project = _project(synthetic_video, tmp_path, name="baseline")

    result = _invoke(project, "--frames", "10:14", "--repeat", "2", "--edit", "tail:factor=4")

    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[0] == "baseline: window 10:14, 3 nodes"
    assert (
        "render 2: 4 frames 10:14 after tail:factor=4, 4 node outputs computed, "
        "8 from cache (67% reuse)" in result.output
    )


def test_an_edit_naming_no_node_is_refused_before_anything_decodes(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """A typo in `--edit` is a typo, not a render of the unedited graph.

    Worth its own case because the failure it prevents is silent: an edit
    applied to nothing would render twice, report 100% reuse, and look exactly
    like a preview whose caching worked perfectly.
    """
    project = _arena_project(synthetic_video, tmp_path)

    result = _invoke(project, "--frames", "10:14", "--repeat", "2", "--edit", "middle:factor=4")

    assert result.exit_code == 1
    assert "middle" in result.stderr
    assert "render 1" not in result.output


def test_an_edit_with_one_render_is_refused_rather_than_ignored(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """`--edit` applies from the second render, so one render cannot show it.

    Refused rather than silently rendering the unedited graph: the whole reason
    to type `--edit` is to read the second render's reuse, and a command that
    printed a first render and no edit would answer a question nobody asked.
    """
    project = _arena_project(synthetic_video, tmp_path)

    result = _invoke(project, "--frames", "10:14", "--edit", "tail:factor=4")

    assert result.exit_code == 1
    assert "--repeat 2" in result.stderr


def test_a_value_the_tool_refuses_is_a_refusal_and_not_a_traceback(
    synthetic_video: Path, tmp_path: Path
) -> None:
    """`--edit` is the one surface that hands a user's raw value to a params model.

    `downsample.factor` is bounded at 64, so `factor=999` fails validation when
    the second render plans. Without `ValidationError` in `_render`'s list the
    user gets a pydantic traceback for something they typed.
    """
    project = _arena_project(synthetic_video, tmp_path)

    result = _invoke(project, "--frames", "10:14", "--repeat", "2", "--edit", "tail:factor=999")

    assert result.exit_code == 1
    assert "factor" in result.stderr
    assert "render 1:" in result.output


def test_one_frame_publishes_only_the_slider_budget(synthetic_video: Path, tmp_path: Path) -> None:
    """`--at` is the slider path, and it must not feed the 3 s series.

    A one-frame render publishing `full_preview_render` too would put a cheap
    sample into the series that measures a whole window and quietly improve its
    median — a budget met by measuring something else.
    """
    project = _arena_project(synthetic_video, tmp_path)

    result = _invoke(project, "--frames", "10:14", "--at", "11")

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "arena 1: frame 11, 3 nodes"
    assert lines[1] == "render 1: 1 frames 11:12, 3 node outputs computed, 0 from cache (0% reuse)"
    assert "slider_to_preview: median" in result.output
    assert "full_preview_render" not in result.output


def test_the_named_replicate_is_the_one_previewed(synthetic_video: Path, tmp_path: Path) -> None:
    """`--replicate` picks one viewport; without it the first is the default.

    A preview is one viewport and a run is the fan-out, so a command that
    ignored this flag would silently preview a different replicate's parameters
    from the ones the user asked to look at.
    """
    project = _project(
        synthetic_video,
        tmp_path,
        replicates=(
            Replicate(replicate_id="a", name="arena 1"),
            Replicate(replicate_id="b", name="arena 2"),
        ),
    )

    named = _invoke(project, "--frames", "10:14", "--replicate", "b")
    defaulted = _invoke(project, "--frames", "10:14")

    assert named.exit_code == 0, named.output
    assert named.output.splitlines()[0] == "arena 2: window 10:14, 3 nodes"
    assert defaulted.output.splitlines()[0] == "arena 1: window 10:14, 3 nodes"


def test_an_unknown_replicate_is_refused(synthetic_video: Path, tmp_path: Path) -> None:
    """Naming nothing is refused rather than falling back to the first.

    A fallback would preview a replicate the user did not name and report its
    timings as if they were the ones asked for.
    """
    project = _arena_project(synthetic_video, tmp_path)

    result = _invoke(project, "--replicate", "nope")

    assert result.exit_code == 1
    assert "nope" in result.stderr


def test_a_missed_budget_is_named_in_the_line_it_missed() -> None:
    """The `MISS by` suffix, which is the whole of what a miss is visible as.

    Driven from a hand-fed `Recorder` rather than from a slow render, because
    nothing in this repo can make a real clock exceed a ceiling on demand — that
    is also why `--check` is not a flag (`preview_cmd.py`'s docstring). Without a
    case the suffix would be the one part of the report that could be wrong for
    as long as every render happened to be fast.
    """
    recorder = Recorder()
    for elapsed in (40.0, 250.0):
        recorder.record(Sample(budget=BUDGETS["slider_to_preview"], elapsed_ms=elapsed))

    line = _timings(recorder, "slider_to_preview")

    assert line.startswith(
        "slider_to_preview: median 145.0 ms of 100 ms (2 samples: 40.0, 250.0 ms)"
    )
    assert line.endswith("MISS by 150.0 ms")
