---
title: A surface carries its values and not the axis they sit on, so one band of three cannot be dragged
status: deferred
deferred_for: decision
phase: 9
priority: high
gated_on: whether a display surface declares an axis alongside its column — a revision of ADR 23 rather than a second vocabulary beside it — or whether a band whose parameter is in units the picture does not carry is a band the user types, permanently
opened: 2026-08-10
---

# A surface carries its values and not the axis they sit on

`adr/a-band-declares-the-surface-it-is-dragged-on.md` rests on one sentence:
naming the picture rather than the unit is honest because "units ride with the
data at run time, where the upstream node has already run". Building the panel
and the handles
([a-declared-surface-is-drawn-by-nothing.md](a-declared-surface-is-drawn-by-nothing.md))
cashed that sentence in and it paid for two of `detect`'s three bands.

A surface arrives as a `Frame` per frame — `data`, `index`, `channels` — so what
rides with it is the *values*, and the axis they are indexed on rides with
nothing. For `count_frac` that costs nothing: the axis is a fraction of a whole
and the whole is the top of the plot by definition. For `value_band` it costs
nothing either, because the parameter is denominated in the same numbers the
column holds, so a y coordinate is already the value. `freq_band` is where the
sentence runs out: the scalogram's rows are `default_freqs(params.fps)` and the
parameter is Hz, and nothing in the column says which row is which frequency. A
cut placed on it has no value to commit.

The panel therefore draws the scalogram and refuses it handles
(`gui/surface_panel.EDITABLE_AXIS`), which is `RegionEditor`'s refusal one kind
over — an editor is offered only where the gesture's coordinates are the ones
the value is denominated in. That is a correct placement and it is not the same
thing as a decision. What is undecided is whether the channel should carry the
axis at all.

The two answers are not close together:

**Widen the channel.** A surface's fill returns its coordinates beside its
values — one array of length `N`, in whatever unit the parameter is stored in —
and every panel maps y through it. That makes `freq_band` draggable, makes the
scalogram's tick labels possible, and makes the value axis of a `TRACE` a
declaration rather than something read off the data with headroom. It is a
revision of ADR 23 rather than a second vocabulary beside it, which the ADR's
own last-but-one paragraph anticipates. The cost is that `Frame` is not the
shape for it, so the display channel stops being "a `Frame` per surface" and
becomes something of its own — and the ADR's whole argument for the channel is
that it is *not* a second product stream, which a richer type makes harder to
keep true.

**Or leave it.** A band the user types is what every band was until this week,
`freq_band` is the one of three that is a fixed physical unit and therefore the
one a user can reason about numerically, and the form's control already accepts
it. Under this answer the refusal above is permanent and `EDITABLE_AXIS` stops
being a gap and becomes the vocabulary's own shape.

What the measurement says, in case it bears: filling all three surfaces costs
about six times a warm re-render and the drag budget holds with room
([2026.08.10](../findings/2026.08.10-the-display-channel-costs-a-watched-nodes-re-use-and-the-band-budget-holds.md)),
so an axis array per surface would not be paid for in latency. This is a
question about what the declaration means, not about what it costs.

No criterion, for the template's one exemption: what the command would assert —
that a scalogram takes handles — is the thing being decided.
