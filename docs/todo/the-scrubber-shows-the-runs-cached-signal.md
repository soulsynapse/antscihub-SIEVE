---
title: The scrubber's band is reserved for the cached signal and draws nothing
phase: 9
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_timeline.py -q -k 'the_band_draws_the_cached_signal or the_band_is_empty_before_a_run'"
opened: 2026-08-09
---

# The scrubber's band is reserved for the cached signal and draws nothing

VISION describes the scrubber as v2's, much taller, doing v1's job: "it shows the
selected signal that was cached, like how v1 did it, so if the user scrubs the
footage or does a full length detection, it'll give them the detection
information for that run". `gui/timeline/bar.py` already names the space — a
comment marks the band as "where the cached signal for the current run is read
(v1's habit)" — and nothing fills it.

The producer exists. `pipeline/series_collector.py` assembles a node's per-frame
outputs into the series a graph is drawn from, and 07.7 gave the graph panel that
series. What the strip wants is the same series at a different density and over a
different span: the graph panel draws the window, the strip draws the whole clip
and is how a user finds the part worth windowing. So this is not a second
collector, and an item that grows one has gone wrong.

The question it has to answer rather than assume is which signal, and what the
strip shows before there is one. `MOCKUP-MAP.md`'s scrubber row settles the drag,
the handles and the seam and is silent on the contents, so the referent does not
decide this. The pinned step is the obvious candidate — it is already the one
step held under the canvas — but a run's cached extent and the pinned step's
extent are not the same thing, and a band that draws a partial run as if it were
a whole one is the three-state collapse v1 was faulted for. The second `-k` term
is the honest empty state, and it is the half worth getting right first.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui/test_timeline.py -q -k 'the_band_draws_the_cached_signal or the_band_is_empty_before_a_run'
    50 deselected in 0.13s
    exit: 5
