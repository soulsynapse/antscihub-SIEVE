"""The down arrow on a step, and the guidance it opens onto.

The two specs below are tools that do not exist and are never registered, for
`test_param_generator.py`'s reason: an expander handed a spec it has never seen
is what shows that the text came off the declaration rather than out of a table
keyed by tool. Two of them, differing only in what they say, because one would
leave open whether the widget read the spec or a constant.

`sieve.gui` and Qt are imported inside the test bodies for the reason
`conftest.py` gives — a module-scope import here runs during collection and puts
Qt in the process the headless loop budget is measured in.
"""

from __future__ import annotations

from sieve.core.tool_base import (
    ArraySpec,
    ElementRelation,
    Emission,
    ParamsBase,
    ParamStereotype,
    ToolSpec,
)


class StirParams(ParamsBase):
    speed: int = 3


def _spec(tool_id: str, summary: str, guidance: str) -> ToolSpec:
    return ToolSpec(
        tool_id=tool_id,
        version="1.0.0",
        summary=summary,
        guidance=guidance,
        params_model=StirParams,
        accepts=ArraySpec(),
        emits=ArraySpec(),
        emissions=(Emission("out"),),
        element=ElementRelation.PRESERVED,
        param_stereotypes={"speed": ParamStereotype.SCALAR_RANGE},
    )


def test_the_expander_reads_the_spec(qapp) -> None:
    """The step's help text is the tool's declaration and nothing else.

    Which is the whole of what this widget knows: two tools that share a params
    model and differ only in their guidance get different text out of the same
    code path, so a third tool arriving on the shelf needs no edit here — the
    generator's property (`adr/gui-knows-kinds-not-tools.md`) on the surface
    VISION describes as "all the help text they need".

    The summary is asserted absent rather than merely different, because the
    cheap wrong version of this widget is one that shows the line the collapsed
    step already carries and calls the promotion done.
    """
    from sieve.gui.expander import GuidanceExpander

    stir = _spec("stir", "Stir the pot.", "Turn speed up until the pot moves.")
    settle = _spec("settle", "Let it settle.", "Wait longer than the slowest ant.")

    assert GuidanceExpander(stir).text() == stir.guidance
    assert GuidanceExpander(settle).text() == settle.guidance
    assert stir.summary not in GuidanceExpander(stir).text()


def test_the_arrow_opens_it_and_the_text_scrolls(qapp) -> None:
    """Closed until asked, and long guidance scrolls rather than growing.

    VISION's expander is a down arrow the user hits, so the text is not on the
    step until they do — a step that opened with a page of prose under it would
    be the wizard rather than the wizard reimagined. Scrolling is the other half
    of that sentence, and it is what keeps a tool with a long explanation from
    deciding how tall the step position is.
    """
    from sieve.gui.expander import GuidanceExpander

    expander = GuidanceExpander(_spec("stir", "Stir the pot.", "Turn speed up.\n" * 200))

    assert not expander.is_expanded()

    expander.arrow.click()

    assert expander.is_expanded()
    assert expander.maximumHeight() < expander.body().sizeHint().height()

    expander.arrow.click()

    assert not expander.is_expanded()
