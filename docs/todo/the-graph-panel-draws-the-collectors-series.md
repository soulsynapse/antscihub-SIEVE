---
title: The graph panel draws the collector's series
step: "07.7"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui/test_graph_panel.py -q -k 'the_panel_draws_the_series_it_is_handed or a_stale_series_is_labeled_stale'"
opened: 2026-08-08
---

# The graph panel draws the collector's series

The panel renders the series 06.6's collector assembles — the first consumer
that is not a benchmark, retiring the one-phase admission
`the-series-collector-gives-slider-to-graph-a-subject.md` recorded against
`adr/declared-means-verified.md`. Assembly stays below `gui`: the collector
runs in `pipeline`, the panel draws what it is handed, and a frame the
collector has not refilled yet is labeled stale rather than drawn as current —
VISION's honesty half, which holds outside the budget scope too.

Collector and panel are two items across two phases deliberately, and the
ruling is in 06.6: the budget number had to be taken headless first to be
attributable, so the split is not granularity but the measurement's chain of
custody. What this item does not do: no band overlay and no axis declaration —
a panel drawing a series needs no axis binding, and the editor that does is
07.8, where the declaration lands with its reader.
