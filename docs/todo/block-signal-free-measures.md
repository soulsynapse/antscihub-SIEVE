---
title: flow_direction, and whether a signal is a plane or a parameter
status: deferred
priority: unassessed
opened: 2026-07-27
gated_on: >
  two decisions, both Kendrick's. (1) How a *circular* signal bands and
  renders — flow_direction is orthogonal to everything existing and is the
  screening's other survivor, but a value band and a heat ramp over an angle
  are wrap-around objects the GUI has no shape for. (2) Whether block_signal
  keeps emitting one plane chosen by a parameter or emits several at once —
  the screening promoted one measure, not the four that would have paid for
  the protocol change, so the case for it is now weaker than when this item
  was written and it should be reopened by a *second* survivor, not by this
  one. Recommendation for both in the body.
reads:
  - src/sieve/filters/block_signal.py
  - src/sieve/filters/block_signal.md
  - docs/findings/2026.07.28-four-free-block-measures-two-survive.md
  - docs/completed-todo/2026.07.28-flow-agreement-signal.md
---

# What is left of the free-measures item after the screening

Raised 2026-07-27: "what other forms of signal extraction can we essentially
get for free, or relatively cheaply? The three we have now are excellent."

The screening ran 2026-07-28 and is
`docs/findings/2026.07.28-four-free-block-measures-two-survive.md`. It killed
four candidates outright (`trace` and `temporal_texture` are change_energy
restated; `texture` and `spatial_coherency` separate nothing) and promoted
`flow_agreement`, which shipped as a `Signal` entry the same day. What is
left here is the one survivor the experiment could not judge, and the
structural question the experiment was supposed to settle and instead
answered in the direction of "not yet".

## Decision 1 — flow_direction, and what a band over an angle means

`atan2` of the block's circular-mean unit vector. The screening says it is
orthogonal to everything existing: OLS R² of 0.002–0.006 on the three, rank
correlations of 0.03–0.07. That is not a surprise — nothing existing carries
orientation at all — and it is the strongest such number in the table. The
ethological case is also the clearest of any candidate: directional bands
("toward the nest entrance", "against the flow of the trail") are a detector
nobody can build from speed alone.

What blocks it is not the kernel — it is four lines — but everything
downstream of it, all of which assumes a linear scalar:

- **The value band.** `[lo, hi]` on an angle is wrong at the seam. A band
  from 170° to −170° is a 20°-wide interval through the wrap, and the
  existing `inband_count` (`lo <= m <= hi`) reads it as empty.
- **The heat ramp.** A sequential ramp renders −179° and +179° at opposite
  ends of the colour scale for two blocks moving 2° apart. That is rule 6 in
  its rendering form: the picture asserts a difference that is not there.
- **The band plot.** Its y-axis is a magnitude with a meaningful zero. A
  circular axis has neither, and the drag gesture that sets a band would have
  to be able to cross the seam.
- **Magnitude-free-ness, which coherence already has and this is worse at.**
  Direction is not merely unitless, it is *undefined* for a block that did
  not move — and unlike agreement, there is no honest zero to fall back on:
  0 rad is a real direction. Refusing (rule 6) means direction needs a
  companion mask in a way no existing signal does, which is the one place
  this decision touches decision 2.

**Options.**

1. **Ship it as a plain signal and accept the seam.** Cheapest. Costs a
   documented lie at the wrap and a heat ramp that is misleading exactly
   where the data is most continuous. Forecloses nothing, but a tuned band
   saved before the fix and reinterpreted after it is a silent change of
   meaning, which is the foot-gun `_value_band_memory` exists to prevent.
2. **Make bands wrap-aware and the ramp cyclic, for this signal only.** A
   `circular: bool` on the signal's descriptor, `inband_count` taking the
   wrap when set, a cyclic (HSV-hue) ramp in the composite. Real surface —
   detection, the band plot, the composite heat read — but all of it
   additive, and it is the honest rendering.
3. **Don't ship direction as a `Signal` at all; ship it as an overlay.**
   Direction is arguably not a scalar field to threshold but a quiver to draw
   over the footage. This sidesteps every problem above and gives up
   directional *detection*, which was the entire argument for it.

**Recommendation: (2), and only once something wants to detect on direction.**
The circular machinery is small and additive and it is the only option that
does not make the GUI assert something false. But it is the first signal that
needs a *type*, not just a label, and building that machinery ahead of a
detector that uses it is speculative. The trigger to promote this item is a
directional question somebody actually has — "which way across the arena",
"toward or away" — not the availability of the measure.

## Decision 2 — one plane by parameter, or several at once

The original argument: a `Signal` enum entry per measure means N re-renders
to see N measures, and the cost is upside down, because the products are
shared. The alternative is `block_signal` emitting a multi-channel block grid
(one plane per requested measure) with the detector choosing its plane. That
touches `emits` (`ChannelSpec`), the composite's heat read, and the
detector's series plumbing — real surface, and
`kernel-protocol-beyond-one-frame.md` territory if it drags in named ports.
It is also rule 7 territory: which requested-measures set is hashed, and
whether a plane the user is not looking at changes what a result *is*.

The item pre-stated the threshold as "a protocol change for one new signal is
not worth it, for four it is." The screening produced one shipped and one
blocked. **That is the answer to this decision as stated, and it is no.**

**Recommendation: leave the enum alone, and let this be reopened by evidence
rather than by count.** Two things would reopen it, and neither has happened:

- **A survivor that needs a companion plane to be honest.** flow_direction is
  the live candidate — it has no honest zero, so it wants a validity mask
  beside it. If decision 1 goes to option (2), this one comes back with it,
  because "direction plus its mask" is a two-plane emission by nature.
- **A measured cost.** Nobody has timed a two-signal tuning pass. The
  argument that N re-renders is wasteful is arithmetic, not a measurement,
  and `block_signal` is ~realtime and uncacheable by contract — the redundant
  work may be small against the decode it rides on. A `full_preview_render`
  budget miss traced to duplicated tensor products would make this concrete.

Until one of those, the enum is the cheaper thing to be wrong about: adding
an entry forecloses nothing, and if multi-channel ever lands, every existing
signal is one more plane in it.

**Start decision 1 by drawing it, not by arguing about it.** A value band and
a heat ramp over an angle are wrap-around objects the GUI has no shape for,
and that is a *representation* question — the one kind a mockup answers
cheaply. The seeker taught the limit: `mockups/seeker/` was about gesture
semantics, which no static picture settles, and it outlived its question and
produced a phantom regression that cost a session to disprove
(`docs/completed-todo/2026.07.27-seeker-upgrades.md`). So if a mockup is
checked in for this, it carries the date and the item it belongs to, and it
is deleted when this item resolves.

## Still unbuilt, and unaffected by either decision

Two candidates were named but never screened, because both cost a new blur or
new state and the screening was scoped to the free ones:

- **divergence / curl of the block flow field** — finite differences of
  block-mean `(u, v)` across *neighbouring blocks*, O(B).
  Expansion/contraction and rotation signatures — grooming vs walking vs the
  whole-arena lighting breathing. Needs block-mean u and v to leave the
  kernel, so it waits on decision 2 either way.
- (`temporal texture`, the third of that group, was screened anyway and
  killed — it is change_energy to a rank correlation of 0.99.)
