---
title: The per-sample gate sees every sample the run published
phase: 6
priority: high
status: open
gated_on: nothing
done_when: "uv run pytest tests/bench/test_loop_budget.py -k every_sample_the_run_published -q"
opened: 2026-08-07
---

# The per-sample gate sees every sample the run published

`test_loop_budget.py`'s fixture clears the recorder between the window renders
and the drags so the cold first frame stays out of `slider_to_preview`'s median.
That narrowing is right for the median and wrong for everything else, because it
narrows the collection rather than the statistic: the five samples it drops
never reach `Reading`, so `test_no_single_sample_missed_its_ceiling` cannot read
them either. The dropped cold sample is 15.59 ms against a 100 ms ceiling — 5.4x
the gated median and the largest `slider_to_preview` in the run
(`docs/findings/2026.08.07-the-per-sample-gate-cannot-see-the-cold-first-frame.md`).

What should be different: `Reading` holds every sample the run published, the
per-sample gate reads all of them, and the median gates keep naming the narrowed
series they argue for. Two readings of one series is what the module docstring
claims and it should become true — today it is two readings of two series, one
of which is a subset nobody chose for this purpose.

06.6 added a third stage to the same fixture and made the narrowing wider rather
than differently shaped: the `GRAPH_EDITS` refills clear the recorder for the
same reason the drags do, so the five `full_preview_render` and five
`slider_to_preview` samples those renders publish are dropped before `Reading` is
built, on top of the five the drag stage already drops. Nothing new is wrong —
the same fix reaches all of them, and it is one more reason the fix is in the
collection rather than in any one gate's statistic.

The open question the finding leaves is the one to settle first, because it
decides the shape: `preview.py` publishes `FIRST_FRAME_BUDGET` around a window
render's first frame, and that interval is not a drag, while the budget's label
is "Slider drag → preview repaint". If the ceiling covers both gestures then the
gate must judge both and this is a collection fix. If it does not, then the
publisher is wrong and the fix is in `preview.py` — in which case say so and the
gate follows.
