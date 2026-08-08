"""What the run keeps, and the command that runs it.

**The list is read off the specs, so it cannot lie.** A row per product of every
node — `ToolSpec.emissions`, which exists to say what `emits` cannot: which
products a tool can be *configured* to compute, over the whole legal parameter
range rather than over the run that has just finished (VISION's save screen, and
`core/tool_base.py` on why both directions are refused at registration). A screen
that listed only what the current parameters select would offer fewer outputs
than the tool has, which is the failure that declaration is checked against.

**A checkoff is `SetOutputs` and nothing else.** It writes `Project.checkpoints`
and `Project.outputs` and moves no cache key — Phase 2's reason those two fields
sit on `Project` rather than on `Node` (`pipeline/cache_key.py`). The sinks are
carried through rather than composed here: nothing on this screen names a format
or a directory, and `SetOutputs` writes the pair together because the screen
decides them together.

**A checked row records its node, not its product.** `Project.checkpoints` is
node ids, so two products of one node check independently and write the same
entry — `todo/a-checkpoint-does-not-record-which-product-it-holds.md` is where
that is answered, and it is a schema question rather than a screen's. What the
screen can do honestly it does: a reopened document shows the checked node
against the product its parameters select, so the row that is ticked is the one
a run would actually write.

**Run is the saved file handed to `sieve run`.** Not a call into `sieve.cli`,
which the layers contract puts beside this package rather than under it, and not
a second execution path: the GUI spawns the same command a cluster node would,
against the same artifact, which is the HPC handoff VISION promises and the first
thing in the product that exercises it. The program is named, not located — a
GUI launched from the environment SIEVE is installed in inherits that
environment's PATH, and resolving the script here would be this module deciding
which of two installs a user meant.

What comes back is surfaced whichever way the run ends: the CLI's own words on
`finished`, and the command's own name when there is no such program to start —
the one failure that would otherwise be indistinguishable from a long run.

What stays unbuilt: the overview and the time estimate VISION puts on this
screen, which is the consumer that revives the spec's cost declarations
(`adr/declared-means-verified.md`) and arrives with it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from PySide6.QtCore import QProcess, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sieve.core.pipeline_model import Pipeline
from sieve.core.tool_base import Emission, ToolSpec, resolved_schema
from sieve.gui.walk import node_order
from sieve.session.intents import SetOutputs, issue
from sieve.session.session import Session

#: The console script, spelt as `pyproject.toml` declares it and as a cluster
#: node types it. One string, so the command the GUI issues and the command a
#: handoff runs cannot come to differ.
CLI_PROGRAM = "sieve"


@dataclass(frozen=True, slots=True)
class OutputRow:
    """One product of one node: what a checkbox on this screen stands for."""

    node_id: str
    emission: Emission


def run_command(project_path: str) -> tuple[str, ...]:
    """The invocation that runs the saved file at `project_path`."""
    return (CLI_PROGRAM, "run", project_path)


def output_rows(pipeline: Pipeline, specs: Mapping[str, ToolSpec]) -> tuple[OutputRow, ...]:
    """Every product of every node, in the order the walk visits them.

    Walk order rather than document order so the list reads as the pipeline the
    user has been moving through, and so `checkpoints` comes out in an order that
    does not depend on which box was clicked first.

    Raises:
        KeyError: if a node's spec is not among `specs`.
    """
    return tuple(
        OutputRow(node.node_id, emission)
        for node in node_order(pipeline)
        for emission in specs[node.node_id].emissions
    )


def _selected(spec: ToolSpec, emission: Emission, params: Mapping[str, object]) -> bool:
    """Whether `emission` is the product this node's parameters currently pick."""
    if emission.selected_by is None:
        return True
    described = resolved_schema(spec.params_model)["properties"][emission.selected_by]
    value = params.get(emission.selected_by, described.get("default"))
    return str(value) == emission.name


class SaveScreen(QWidget):
    """The checkoff, the run button, and whatever the last run said.

    The specs are handed in rather than looked up, for `param_form.py`'s reason:
    this module never learns which tool it is drawing, and a registry lookup
    here would be the one import that made a `tool_id` branch possible to write.
    """

    #: The argv handed to the CLI, emitted as the process is started. Carried so
    #: a placement can log or echo the handoff without re-deriving it.
    run_issued = Signal(tuple)

    def __init__(
        self,
        session: Session,
        specs: Mapping[str, ToolSpec],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._rows = output_rows(session.project.pipeline, specs)
        self._boxes: dict[tuple[str, str], QCheckBox] = {}
        self._running = False

        self._process = QProcess(self)
        self._process.finished.connect(self._finished)
        self._process.errorOccurred.connect(self._failed_to_start)

        self._message = QLabel("")
        self._message.setWordWrap(True)
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run)

        layout = QVBoxLayout(self)
        kept = set(session.project.checkpoints)
        for row in self._rows:
            spec = specs[row.node_id]
            box = QCheckBox(self._label(row, spec))
            box.setChecked(
                row.node_id in kept
                and _selected(spec, row.emission, session.project.params_for(row.node_id))
            )
            # Connected after the initial state is set: the document already
            # holds it, and writing it back would push a value onto the undo
            # stack for opening a screen.
            box.toggled.connect(self._checkoff)
            self._boxes[row.node_id, row.emission.name] = box
            layout.addWidget(box)
        layout.addWidget(self.run_button)
        layout.addWidget(self._message)

    @staticmethod
    def _label(row: OutputRow, spec: ToolSpec) -> str:
        """The row's text: the node, and the product in the tool's own words."""
        labels = (
            {}
            if row.emission.selected_by is None
            else spec.param_value_labels.get(row.emission.selected_by, {})
        )
        return f"{row.node_id} — {labels.get(row.emission.name, row.emission.name)}"

    @property
    def rows(self) -> Sequence[OutputRow]:
        """What is on offer, in walk order."""
        return self._rows

    def checkbox(self, row: OutputRow) -> QCheckBox:
        """The box standing for `row`."""
        return self._boxes[row.node_id, row.emission.name]

    def message(self) -> str:
        """What the last run said, or `""` before one has spoken."""
        return self._message.text()

    def running(self) -> bool:
        """Whether a run is in flight and has yet to report."""
        return self._running

    def run(self) -> None:
        """Save the document, then run the saved file the way a node would."""
        self._session.save()
        command = run_command(str(self._session.path))
        self._message.setText("")
        self._running = True
        self._process.start(command[0], list(command[1:]))
        self.run_issued.emit(command)

    def _checkoff(self) -> None:
        checked = [row.node_id for row in self._rows if self.checkbox(row).isChecked()]
        issue(
            self._session,
            SetOutputs(
                checkpoints=tuple(dict.fromkeys(checked)),
                outputs=self._session.project.outputs,
            ),
        )

    def _finished(self, exit_code: int, _status: object) -> None:
        self._running = False
        stderr = bytes(self._process.readAllStandardError().data()).decode(errors="replace")
        stdout = bytes(self._process.readAllStandardOutput().data()).decode(errors="replace")
        # Refusals go to stderr and results to stdout, so a failed run reads as
        # its own message rather than as the last line before it gave up.
        said = (stderr if exit_code else stdout).strip()
        self._message.setText(said or f"{CLI_PROGRAM} exited with code {exit_code}")

    def _failed_to_start(self, error: object) -> None:
        if self._process.error() is not QProcess.ProcessError.FailedToStart:
            return
        self._running = False
        self._message.setText(
            f"could not start {CLI_PROGRAM!r} ({error}) — it is the console script this "
            "install declares, and a run here is the same command a cluster node types"
        )
