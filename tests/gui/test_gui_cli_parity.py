"""Phase 7's gate, first half: the window and the command answer the same.

05.5 took the stirred clip out of a GUI test and made it a fixture so the oracle
could run against it first; 05.8 ran both repos' CLIs over it and compared what
came out. This is the same clip from the other side. A user opens the project,
walks to a node, drags a parameter, reads the trace, ticks the output and hands
the file to a cluster — and what the cluster computes has to be, frame for frame,
what they were looking at when they decided to hand it over. That is the whole of
`adr/one-execution-path.md` stated as something a test can fail.

**Equality, not a tolerance.** Both sides run the same `execute` over the same
graph, so a difference is not numerical drift — it is the GUI having reached a
second implementation, or having rendered a document other than the one it saved.
Either is a defect at the digit, so the assertion is at the digit.

**The two sides are asked for the same frames by different routes, and that is
not a weakness.** The working window is view state and nothing in the document
records it (`gui/timeline/bar.py`), so the GUI previews the stretch the user is
tuning on and `sieve run` covers the footage. Handing the command `--frames` is
what makes the comparison a comparison; running the whole clip would be comparing
30 frames against 40, and — with `detect` reading 11 frames ahead of every frame
it answers for — against 11 the clip cannot supply either.

**The parameter is moved through the widget the generator made**, not through
`SetParam`. A parity test that issued the intent itself would hold everything
below the form and nothing about the form: the claim is that the thing the user
touched wrote the document the run ran.

Qt and `sieve.gui` are imported inside the test bodies, for the reason
`conftest.py` gives.
"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from typer.testing import CliRunner

from sieve.cli.app import app
from sieve.core.pipeline_model import Project, SourceSpan
from sieve.storage.checkpoint_writer import checkpoints_dir, replicate_dir
from sieve.tools import discover
from tests.gui import driving
from tests.integration.test_v2_oracle import ARENA, DETECTOR, SPAN, graph

runner = CliRunner()

#: How long the decode thread is given to open the clip and the preview to render
#: it. Generous for `test_save_and_run.py`'s reason: a slow machine costs a flake
#: and buys nothing, because every wait here ends when the thing it waits on does.
_TIMEOUT_MS = 60_000

#: The detection window the user drags to, replacing the graph's own. A value
#: nothing in the fixture uses, so a run that ignored the edit and re-ran the
#: baseline would differ from a GUI that honoured it — the two sides agreeing on
#: an unmoved parameter would prove only that both can read a file.
_EDITED_WINDOW = 7

CONFIG = Path(__file__).resolve().parents[2] / ".importlinter"


@pytest.fixture
def project_file(stirred_clip: Path, tmp_path: Path) -> Path:
    """The oracle's chain over the stirred clip, saved where a window can open it.

    The graph is imported rather than respelt, for `tests/bench/test_loop_budget.py`'s
    reason: a second spelling of the reference workload is a second reference
    workload, and the first symptom is a claim that holds against a chain nothing
    else runs.

    No replicates. The window previews one thing at a time and the baseline is
    what it previews (`pipeline/preview.py`), so a fan-out here would be
    comparing the GUI's one answer against a run that produced two.
    """
    video = tmp_path / stirred_clip.name
    video.write_bytes(stirred_clip.read_bytes())
    path = tmp_path / "stirred.sieve.yaml"
    Project.for_video(video, tmp_path).model_copy(update={"pipeline": graph()}).save(path)
    return path


def _open(project_file: Path) -> Any:
    """A window with the project open, its footage decoded, and its window set."""
    from sieve.gui.app import MainWindow
    from sieve.gui.project_select import projects_in

    window = MainWindow(projects_in(project_file.parent))
    window.show()
    window.open_project(project_file)
    driving.wait_until(lambda: window.player.metadata is not None, _TIMEOUT_MS)
    # The stretch the user is tuning on, which is every frame `detect` can answer
    # for on this clip — `test_v2_oracle` derives why that is 29 and not 40.
    window.timeline.set_window(SourceSpan(start=SPAN.start, end=SPAN.end))
    return window


def _settled(window: Any) -> None:
    """Wait for the refill in flight, and fail with its exception rather than a timeout."""
    driving.wait_until(
        lambda: not window.graph.is_stale or window.tuning.last_error is not None, _TIMEOUT_MS
    )
    assert window.tuning.last_error is None, window.tuning.last_error


def test_the_trace_the_window_drew_is_what_the_command_computes(
    qapp, project_file: Path, tmp_path: Path
) -> None:
    """One edit, one refill, one `sieve run`, one array compared twice over.

    The tick is made through the save screen because that is what writes
    `checkpoints`, and without it the run leaves no file to compare against —
    which makes the checkoff load-bearing here rather than decorative: the thing
    the user pressed is what decided the cluster would keep this node.
    """
    del qapp
    discover()
    window = _open(project_file)
    try:
        # Down to the detector, which is where the graph the user reads comes
        # from and the last node of the chain.
        window.go_down()
        window.go_down()
        assert window.current_node is not None
        assert window.current_node.node_id == DETECTOR
        assert window.tuning.watching == DETECTOR
        # The walk onto a node fills its graph, and that render is the session's
        # cold one. Waited for here so what the edit below supersedes is a trace
        # that exists — the stale assertion two lines down is about an interval
        # between two answers, not between nothing and an answer.
        _settled(window)
        assert window.graph.series is not None

        window.control.step_pane.form.widget("window_frames").setValue(_EDITED_WINDOW)
        # Before the render, and this is the only place the interval is visible:
        # the mark goes up as the edit lands and comes down with the answer, and
        # what is on screen in between is the previous parameters' trace saying
        # so rather than a blank panel (`gui/graph_panel.py`). It is also what
        # makes the refill deferred rather than inline — a mark painted after the
        # render it announces is a state nothing can ever see.
        assert window.graph.is_stale
        assert window.graph.series is not None

        _settled(window)

        session = window.session
        assert session is not None
        assert session.project.params_for(DETECTOR)["window_frames"] == _EDITED_WINDOW

        drawn = window.graph.series
        assert drawn is not None
        assert drawn.start_index == SPAN.start
        assert drawn.data.shape == (SPAN.frame_count, 1, 1)

        # The fourth position, reached by walking to it: the track is a line and
        # the save screen is its far end (`gui/control.py`).
        window.go_forward()
        window.go_forward()
        assert window.control.current_position() == "save"
        screen = window.control.save_pane
        row = next(row for row in screen.rows if row.node_id == DETECTOR)
        screen.checkbox(row).click()
        assert session.project.checkpoints == (DETECTOR,)

        # Saved here rather than through the run button, whose own save is
        # `test_save_and_run.py`'s subject: what this file needs is the artifact
        # on disk, and the command is then run in-process so `--frames` can name
        # the stretch the trace above covers.
        session.save()
    finally:
        window.close()

    result = runner.invoke(app, ["run", str(project_file), "--frames", f"{SPAN.start}:{SPAN.end}"])
    assert result.exit_code == 0, result.output

    video = Project.load(project_file).source.resolve(tmp_path)
    base = replicate_dir(checkpoints_dir(video, tmp_path), None)
    computed = np.load(base / f"{DETECTOR}.npy")

    assert np.array_equal(drawn.data, computed)
    # And it is a detection rather than a flat line, so the equality above is two
    # runs agreeing about an answer rather than about a constant.
    assert 0 < float(computed.sum()) < computed.size


def test_the_window_edited_the_document_the_command_read(qapp, project_file: Path) -> None:
    """The edit reached the file, and reached only the node it was addressed to.

    The other way parity can be lost without either side computing wrongly: a
    form that wrote the whole node set would hand the run a document the user
    never built, and every array would still match because both sides ran it.
    """
    del qapp
    discover()
    window = _open(project_file)
    try:
        before = Project.load(project_file)
        window.go_down()
        window.go_down()
        window.control.step_pane.form.widget("window_frames").setValue(_EDITED_WINDOW)
        _settled(window)
        assert window.session is not None
        window.session.save()
    finally:
        window.close()

    after = Project.load(project_file)

    assert after.params_for(DETECTOR)["window_frames"] == _EDITED_WINDOW
    assert after.params_for(ARENA) == before.params_for(ARENA)
    assert after.pipeline.node("blocks").params == before.pipeline.node("blocks").params


def test_the_gui_computes_nothing_exception_list_is_still_empty() -> None:
    """Phase 7's third gate line, now that there is a GUI for it to be about.

    The list was empty from commit one because there was no v2 GUI code to
    grandfather (`.importlinter`), and the whole of Phase 7 has since been
    written above it. It is read back here rather than in
    `tests/unit/test_import_contracts.py` because the claim it makes is this
    file's: the window's answer equals the command's *because* the window holds
    no computation, and an exception would be the one edit that could make both
    of those false at once while `lint-imports` stayed green.

    `unmatched_ignore_imports_alerting` is asserted beside it, because it is what
    makes an entry that no longer matches anything a failure rather than a line
    nobody notices — an emptied list and a list of dead entries look the same
    from here otherwise.
    """
    parsed = configparser.ConfigParser()
    parsed.read(CONFIG, encoding="utf-8")
    contract = parsed["importlinter:contract:gui-computes-nothing"]

    assert contract.get("ignore_imports", "").strip() == ""
    assert contract["unmatched_ignore_imports_alerting"] == "error"
