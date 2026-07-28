---
title: Block signal free measures
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — every candidate below reads from arrays the kernel
  already forms; the work is choosing which earn a Signal entry, and the
  screening experiment is the choosing
reads:
  - src/sieve/filters/block_signal.py
  - src/sieve/filters/block_signal.md
---

# What else falls out of the structure tensor — padding out block_signal

Raised 2026-07-27: "what other forms of signal extraction can we essentially
get for free, or relatively cheaply? The three we have now are excellent."

The kernel already forms, for flow_speed and coherence, everything expensive:
`it`, `ix`, `iy`, the six blurred products, the per-pixel LK solve `(u, v)`,
and the block-reduced 3x3 tensor with its eigenvalues. A new measure is "free"
exactly when it is one more arithmetic read of those arrays; it costs a new
blur tier when it is not. Candidates, cheapest first:

**Free (reads of existing arrays):**

- **flow direction** — `atan2(v, u)` block-reduced as a *circular* mean
  (mean of unit vectors, else opposite flows average to a direction nobody
  moved in). The block's ant is walking *somewhere*; direction is the obvious
  companion to speed, and directional bands ("toward the nest entrance") are
  a detector nobody can build from speed alone.
- **flow agreement** — the resultant length of those unit vectors in [0, 1]:
  do the pixels of this block move the same way? This is coherence's question
  answered from the LK field instead of the eigenspectrum; it may be redundant
  against coherence (screening decides) but it is differently robust — the
  eigensolve sees all change, this sees only above-determinant flow.
- **texture / gradient energy** — block mean of `Jxx + Jyy` (two already-blurred
  products summed). Not a motion signal: a *conditioning* signal, the aperture
  problem quantified per block. Its immediate use is as a companion trace
  explaining when flow_speed's zeros mean "still" vs "unmeasurable" — rule 6
  for the flow field.
- **eigen-derived alternates** — total space-time energy `trace = lam1+lam2+lam3`,
  or v1-style edge/corner discriminants from the 2x2 spatial block. Same
  eigensolve, different scalar.

**Cheap but not free (new blur or new state):**

- **divergence / curl of the block flow field** — finite differences of
  block-mean `(u, v)` across *neighbouring blocks*, O(B). Expansion/contraction
  and rotation signatures — grooming vs walking vs the whole-arena lighting
  breathing. Needs block-mean u and v to leave the kernel, so it wants the
  multi-channel emission below.
- **temporal texture** — variance of `it` within the block
  (`<I_t²> - <I_t>²`; the second moment is change_energy already, the first is
  one more blur of `it`). Flicker vs coherent luminance change.

**The structural question, which is the real work of this item:** a `Signal`
enum entry per measure means N re-renders to see N measures, and the cost
argument is upside down — the products are shared, so computing one measure at
a time is the expensive way to get several. The alternative is `block_signal`
emitting a multi-channel block grid (one plane per requested measure) with the
detector choosing its plane. That touches `emits` (`ChannelSpec`), the
composite's heat read, and the detector's series plumbing — real surface, and
`kernel-protocol-beyond-one-frame.md` territory if it drags in named ports.
Decide it *after* the screening below says how many measures earn a place; a
protocol change for one new signal is not worth it, for four it is.

**Screening experiment (the hypothesis test, and the gate for each measure):**
one pass over the reference footage computing every candidate per block —
throwaway script against the kernel's internals, findings-grade output, no new
filter surface. For each: (a) separation between hand-identified event windows
and quiet windows, (b) redundancy against the existing three (correlation on
the block-time matrix). **A measure earns a `Signal` entry only if it separates
events and is not explained by change_energy/flow_speed/coherence.** Danger to
pre-state: agreement-vs-coherence and texture-vs-change_energy are the likely
redundancy casualties; direction is the likely survivor since nothing existing
carries orientation at all.
