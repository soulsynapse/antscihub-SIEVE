"""The widget generator: one control per population kind, none per tool.

The fixture below is a tool that does not exist and is never registered. That
is the point of the file — the generator is handed a spec it has never seen,
declaring every kind in the vocabulary at once, and builds the panel anyway. A
tool on the shelf would prove the same thing less well: it would leave open
whether the generator recognised the tool or the kinds.

`sieve.gui` and Qt are imported inside the test bodies for the reason
`conftest.py` gives — a module-scope import here runs during collection and puts
Qt in the process the headless loop budget is measured in.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import pytest
from pydantic import Field

from sieve.core.pipeline_model import Node, Pipeline, Project, SourceRef
from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
)
from sieve.core.types import ROI
from sieve.session.session import Session

_NODE = "n0"


class Flavour(StrEnum):
    SALT = "salt"
    PEPPER = "pepper"


class EveryKindParams(ParamsBase):
    """One field per member of the stereotype vocabulary."""

    count: int = Field(default=4, ge=2, le=64)
    # Exclusive on both sides, which the shelf declares (`fps` is `gt=0`) and a
    # spin box cannot express: the control has to take the step inside.
    fraction: float = Field(default=0.5, gt=0.0, lt=1.0)
    # Bounded by nothing, which the shelf also declares. Qt's own default range
    # for a real-valued spin box stops at 99.99, so a field with no bound of its
    # own is the one that needs a control the widest.
    rate: float = 30.0
    # Not the first choice: a combo that ignored the stored value would still
    # show the right thing if the right thing were the one it opens on.
    flavour: Flavour = Flavour.PEPPER
    frames: tuple[int, int] = (0, 100)
    band: tuple[float, float] = (0.0, 1.0)
    region: ROI = ROI(x=0, y=0, width=8, height=8)
    point: tuple[int, int] = (0, 0)


def _spec() -> ToolSpec:
    return ToolSpec(
        tool_id="stereotypical",
        version="1.0.0",
        summary="A tool that exists to declare every kind at once.",
        params_model=EveryKindParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        element=ElementRelation.PRESERVED,
        param_stereotypes={
            "count": ParamStereotype.SCALAR_RANGE,
            "fraction": ParamStereotype.SCALAR_RANGE,
            "rate": ParamStereotype.SCALAR_RANGE,
            "flavour": ParamStereotype.ENUM,
            "frames": ParamStereotype.SPAN,
            "band": ParamStereotype.BAND,
            "region": ParamStereotype.REGION,
            "point": ParamStereotype.POINT,
        },
        param_value_labels={"flavour": {"salt": "salted", "pepper": "peppered"}},
    )


@pytest.fixture
def session(tmp_path: Path) -> Session:
    """One node of the tool above, with every parameter left at its default."""
    project = Project(
        source=SourceRef(path="clip.mp4"),
        pipeline=Pipeline(nodes=(Node(node_id=_NODE, tool_id="stereotypical", version="1.0.0"),)),
    )
    return Session(tmp_path / "clip.sieve.yaml", project)


def test_a_widget_per_kind_never_per_tool(qapp, session: Session) -> None:
    """Every kind gets a control, and which control is the kind's answer.

    Two claims, and the second is the one that decays quietly. The map being
    total over `ParamStereotype` is what makes a new kind cost a widget rather
    than a blank row, and it is asserted against the enum rather than against a
    list here so that minting a member is what turns it red.

    The scalar's range is checked because it is where the other half of the
    property lives: the bounds are read out of the params model's own schema
    through `resolved_schema`, so a tool arriving with tighter ones needs no
    edit here either.
    """
    from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QLabel, QSpinBox

    from sieve.gui.param_form import _BUILDERS, ParamForm

    assert set(_BUILDERS) == set(ParamStereotype)

    form = ParamForm(session, _NODE, _spec())

    assert isinstance(form.widget("count"), QSpinBox)
    assert isinstance(form.widget("fraction"), QDoubleSpinBox)
    assert isinstance(form.widget("flavour"), QComboBox)
    for name in ("frames", "band", "region", "point"):
        assert isinstance(form.widget(name), QLabel)

    assert (form.widget("count").minimum(), form.widget("count").maximum()) == (2, 64)
    assert 0.0 < form.widget("fraction").minimum() < form.widget("fraction").maximum() < 1.0
    assert form.widget("rate").maximum() >= 1e6
    assert form.widget("flavour").currentText() == "peppered"


def test_an_unknown_kind_is_refused_by_name(qapp, session: Session, monkeypatch) -> None:
    """A kind with no widget is a loud refusal, not a parameter left off a panel.

    `ToolSpec` already refuses a kind that is not in the vocabulary; what this
    holds is the other side of the same rule, which only the generator can
    enforce — a kind that *is* in the vocabulary and has no control. The
    vocabulary is closed and every member is mapped, so the case is written by
    unmapping one: a member minted without an entry is exactly this state, and
    the refusal has to name the kind for the next author to know what to write.
    """
    from sieve.gui import param_form

    monkeypatch.delitem(param_form._BUILDERS, ParamStereotype.REGION)

    with pytest.raises(ValueError, match="region"):
        param_form.ParamForm(session, _NODE, _spec())


def test_an_edit_enters_as_a_set_param(qapp, session: Session) -> None:
    """A spin box moves the document through the command layer, or not at all.

    The form holds no project of its own and writes to none: what a widget
    produces is an intent at an address, which is what makes a typed number and
    a dragged box the same mutation (`adr/gui-knows-kinds-not-tools.md`). Undo
    is the evidence that it went through that layer rather than around it — a
    value written directly onto the session would leave nothing to step back
    to.
    """
    from sieve.gui.param_form import ParamForm

    form = ParamForm(session, _NODE, _spec())
    form.widget("count").setValue(8)
    form.widget("fraction").setValue(0.25)

    assert session.project.params_for(_NODE) == {"count": 8, "fraction": 0.25}
    # A rebuilt form is how a new value arrives, so the second one shows what
    # the document holds rather than what the field defaults to.
    assert ParamForm(session, _NODE, _spec()).widget("count").value() == 8
    assert session.undo().params_for(_NODE) == {"count": 8}


def test_building_a_form_is_not_an_edit_of_the_document_it_was_built_from(
    qapp, session: Session
) -> None:
    """Showing a value must not write it back.

    Every control is populated from the document as it is built, and Qt's
    obvious signals do not distinguish that from a user acting: a combo box
    emits `currentIndexChanged` for its own first item. A form built on the
    node the walk just moved to would then push a value nobody typed onto the
    undo stack, once per redraw, and the first undo of the session would step
    back to a document identical to the one on screen.
    """
    from sieve.gui.param_form import ParamForm

    ParamForm(session, _NODE, _spec())

    assert not session.can_undo()
