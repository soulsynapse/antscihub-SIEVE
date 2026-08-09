"""Every mutation of the open project, named by what it changes.

One layer, and the document's only writer: a front end holds no `Project` it
edits, it names the mutation and this applies it. What lands on the session is
a new whole value, which is what lets `session.py` stay ignorant of what an
edit *was* — the pair v2's `document.py` and `commands.py` co-changed as.

**Keyed by intent kind, and a kind is a mutation of the saved file.** Not by
emitting surface: `adr/gui-knows-kinds-not-tools.md` makes a drawn region an
editor bound to a param field, so a canvas drag and a typed number are one
`SetParam` at one address. A `DrawRegion` kind would key this layer by which
widget produced the value, which is the coupling the layer exists to dissolve,
and every consumer below — undo, validation, save — would then have two paths
to the same write.

Each kind carries its own application rather than a dispatch table doing it for
them, so a kind arriving with the surface that emits it adds no branch to
anything already written. What a kind may *do* is bounded: it composes the
document's own edit methods, because how a parameter edit is expressed in
schema v1 — which pin moves, which default follows — is `pipeline_model`'s
answer and a paraphrase of it here would be a second one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sieve.core.pipeline_model import Project, Sink
from sieve.session.session import Session


class Intent(Protocol):
    """One mutation of the open project, able to state its own result."""

    def applied_to(self, project: Project) -> Project:
        """The document `project` becomes under this intent.

        Pure, and total in the sense that matters: an intent it cannot apply
        raises rather than returning `project` unchanged, so a no-op edit and a
        refused one are never the same outcome to the caller.
        """
        ...


@dataclass(frozen=True, slots=True)
class SetParam:
    """One parameter of one node, optionally on one replicate.

    The replicate is the tail of the address, not a second kind: an override is
    the same mutation at a longer address (`PLAN.md`, Phase 7). What it buys is
    that no editor branches on selection state — a canvas drag on a replicate
    emits this exactly as a spinbox on the baseline does, and which of
    `pipeline_model`'s two writes runs is decided here, once.

    One field per intent. A form submitting its whole field set would drag
    values the user never touched into the baseline, which
    `Project.with_param_edit` warns about from the other side; the address is
    the field, so what is submitted is what was edited.
    """

    node_id: str
    param: str
    value: Any
    replicate_id: str | None = None

    def applied_to(self, project: Project) -> Project:
        """The document with this field set, and the baseline moved with it.

        Raises:
            KeyError: if the node, or the replicate, names nothing.
        """
        params = {self.param: self.value}
        if self.replicate_id is None:
            return project.with_param_default(self.node_id, params)
        return project.with_param_edit(self.node_id, self.replicate_id, params)


@dataclass(frozen=True, slots=True)
class SetOutputs:
    """What the run keeps: the checkpoints, and the sinks that are written.

    The save screen's checkoff enters here or it becomes a second writer of the
    document. Both lists at once because the screen decides them together, and
    neither may reach a cache key — the reason Phase 2 records them on `Project`
    rather than on `Node`, and the claim `test_intents.py` pins.
    """

    checkpoints: tuple[str, ...]
    outputs: tuple[Sink, ...]

    def applied_to(self, project: Project) -> Project:
        """The document keeping exactly these results.

        Raises:
            ValidationError: if a checkpoint or a sink names no node in the graph.
        """
        return project.with_outputs(self.checkpoints, self.outputs)


def issue(session: Session, intent: Intent) -> bool:
    """Apply `intent` to `session`'s project and commit the result.

    The new value is built before anything is committed, so an intent that
    cannot apply leaves the history where it was rather than pushing a value
    the document never held.

    The session's answer is passed straight back: an intent whose result equals
    the document already held is dropped there (`Session.commit`), and a surface
    that announced the edit anyway would be announcing a write that did not
    happen. The present value is not returned because it is `session.project` to
    anyone holding the session, and returning it made a dropped write and a real
    one indistinguishable to every caller.

    Returns:
        Whether the document moved.

    Raises:
        KeyError: if the intent addresses something the document does not hold.
        ValidationError: if the result would not be a valid document.
    """
    return session.commit(intent.applied_to(session.project))
