









from __future__ import annotations

from collections.abc import Callable

import pytest
from PySide6.QtCore import QPointF
from pytestqt.qtbot import QtBot

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import Sample
from sieve.gui.graph_hud import MIN_CEILING_MS, REPAINT_MS, GraphHud
from tests.gui import qt_input

pytestmark = pytest.mark.gui


def _capture(dest: list[tuple[float, float]]) -> Callable[[float, float], None]:


    def slot(lo: float, hi: float) -> None:
        dest.append((lo, hi))

    return slot


def _hud(qtbot: QtBot) -> GraphHud:
    hud = GraphHud()
    qtbot.addWidget(hud)
    hud.resize(600, 150)
    hud.set_span(0, 100)
    return hud


def test_begin_replaces_the_series_instead_of_appending(qtbot: QtBot) -> None:

    hud = _hud(qtbot)
    hud.add_cost(3, 40.0)
    hud.add_cost(4, 55.0)
    assert hud.ceiling_ms == 55.0

    hud.begin()

    assert hud.costs() == ()
    assert hud.ceiling_ms == MIN_CEILING_MS
    hud.add_cost(10, 2.0)
    assert hud.costs() == ((10, 2.0),)


def test_points_are_keyed_by_source_index_not_arrival_order(qtbot: QtBot) -> None:


    hud = _hud(qtbot)
    hud.add_cost(7, 12.0)
    hud.add_cost(3, 8.0)
    assert hud.costs() == ((3, 8.0), (7, 12.0))

    hud.add_cost(7, 5.0)
    assert hud.costs() == ((3, 8.0), (7, 5.0))


def test_a_burst_of_points_coalesces_to_one_trailing_repaint(qtbot: QtBot) -> None:

    hud = _hud(qtbot)
    repaints: list[int] = []
    hud.update = lambda *args: repaints.append(1)

    for index in range(100):
        hud.add_cost(index, 5.0)

    assert not repaints, "the repaint ran inside the burst instead of trailing it"
    qtbot.waitUntil(lambda: len(repaints) >= 1, timeout=1000)
    qtbot.wait(REPAINT_MS * 3)
    assert len(repaints) == 1
    assert len(hud.costs()) == 100


def test_the_budget_line_carries_the_watched_verdicts_and_their_misses(qtbot: QtBot) -> None:
    hud = _hud(qtbot)
    assert hud.budget_line() == ("", False)

    hud.show_sample(Sample(budget=BUDGETS["full_preview_render"], elapsed_ms=4200.0))
    line, missed = hud.budget_line()
    assert "render 4200/3000 ms" in line and missed

    hud.show_sample(Sample(budget=BUDGETS["full_preview_render"], elapsed_ms=812.0))
    line, missed = hud.budget_line()
    assert "render 812/3000 ms" in line and not missed


    hud.show_sample(Sample(budget=BUDGETS["scrub_to_repaint"], elapsed_ms=1.0))
    assert hud.budget_line() == (line, False)


def test_the_attribution_names_the_span_worst_against_its_own_ceiling(qtbot: QtBot) -> None:








    hud = _hud(qtbot)
    assert hud.attribution_line() == ("", False)

    hud.show_sample(Sample(budget=BUDGETS["full_preview_render"], elapsed_ms=1200.0))
    hud.show_sample(
        Sample(budget=BUDGETS["density_rebuild"], elapsed_ms=340.0, detail="B = 65,536")
    )
    line, over = hud.attribution_line()
    assert "density_rebuild" in line and "B = 65,536" in line and "340 ms" in line
    assert "3.4x its 100" in line
    assert over


def test_the_attribution_persists_when_nothing_is_over(qtbot: QtBot) -> None:






    hud = _hud(qtbot)
    hud.show_sample(Sample(budget=BUDGETS["density_rebuild"], elapsed_ms=12.0, detail="B = 1,024"))
    line, over = hud.attribution_line()
    assert "density_rebuild" in line and "B = 1,024" in line
    assert not over


def test_every_drag_scrubs_because_there_is_no_handle_to_grab(qtbot: QtBot) -> None:





    hud = _hud(qtbot)
    presses: list[int] = []
    hud.pressed.connect(presses.append)
    bands: list[tuple[float, float]] = []
    hud.band_changed.connect(_capture(bands))

    top = QPointF(float(hud.plot_rect().center().x()), hud.handle_y("hi"))
    qt_input.press(hud, top)
    qt_input.move(hud, QPointF(top.x() + 30.0, top.y()))
    qt_input.release(hud, QPointF(top.x() + 30.0, top.y()))

    assert presses and not bands
