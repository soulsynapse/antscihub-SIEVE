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


def test_a_wordier_tool_asks_for_no_more_of_the_step(qapp) -> None:
    """The cap is on the body, and the body is what a wordy tool grows.

    Two tools whose guidance both overflow the cap ask their parent for the same
    height — the module's opening sentence, that a widget grown to fit its text
    would let the wordiest tool on the shelf decide the layout of every other
    one. The expander's own maximum is that cap plus the arrow, so it bounds
    what the widget is *given*; this is what it *asks for*, which is the number
    that matters where `step_pane.py` puts it, inside a scroll area whose extent
    is the column's request.

    The bound is asserted as well as the equality: a widget's own
    `maximumHeight` does not clamp its own `sizeHint`, and `QScrollArea` caps
    its hint internally at a height both of these texts exceed, so without the
    bound the two hints agree whether or not the body cap exists.
    """
    from sieve.gui.expander import _BODY_HEIGHT, GuidanceExpander

    wordy = GuidanceExpander(_spec("stir", "Stir the pot.", "Turn speed up.\n" * 200))
    wordier = GuidanceExpander(_spec("settle", "Let it settle.", "Wait longer.\n" * 800))

    wordy.arrow.click()
    wordier.arrow.click()

    assert wordy.sizeHint().height() == wordier.sizeHint().height()
    ceiling = wordy.arrow.sizeHint().height() + wordy.layout().spacing() + _BODY_HEIGHT
    assert wordy.sizeHint().height() <= ceiling


def test_a_long_line_wraps_rather_than_scrolling_sideways(qapp) -> None:
    """Guidance written as prose stays inside the width it was given.

    The vertical scroll is what the test above is about; this is the axis the
    body must *not* scroll on. A label left to its own size hint inside the
    viewport lays a paragraph out as one line and the user drags sideways to
    read a sentence, which is the failure the `setWidgetResizable` call is
    there for and which word wrap alone does not prevent.
    """
    from PySide6.QtWidgets import QScrollArea

    from sieve.gui.expander import GuidanceExpander

    prose = "Turn the speed up until the pot moves and the ants scatter. " * 40
    expander = GuidanceExpander(_spec("stir", "Stir the pot.", prose))
    expander.resize(300, 400)
    expander.show()
    expander.arrow.click()
    # Widget geometry is assigned by the layout when the events queued by show()
    # and the click are delivered, not by the calls themselves.
    qapp.processEvents()

    viewport = expander.findChild(QScrollArea).viewport()
    assert expander.body().width() <= viewport.width()
