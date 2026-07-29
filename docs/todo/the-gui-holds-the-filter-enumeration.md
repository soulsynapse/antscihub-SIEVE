---
title: The GUI holds the enumeration rule 3 forbids
status: superseded
superseded_by: [presentation-is-a-channel-not-a-switch, a-filter-id-spelled-twice]
priority: unassessed

gated_on: >
  superseded 2026-07-29 — the literal sites this item catalogued are now the
  exception list of `a-filter-id-spelled-twice`, and the caption/card question
  is decided in `presentation-is-a-channel-not-a-switch`

reads:
  - src/sieve/gui/param_form.py
  - src/sieve/gui/chain_model.py
  - src/sieve/gui/wizard_model.py
  - docs/ARCHITECTURE.md
---

# The GUI holds the enumeration rule 3 forbids

> **Superseded 2026-07-29.** The catalogue below became the seeded exception
> set of `a-filter-id-spelled-twice`, and the presentation question was
> decided the other way from this file's last section: hints go on the spec's
> *presentation channel* (REWORK.md ## Decided). The objection below — that
> UI hints on `FilterSpec` put presentation on the identity line — was the
> right objection and is answered rather than overruled: the spec-channel
> partition (`the-spec-has-three-channels`) makes "a presentation edit moves
> no cache key" a test result, which is what the objection was missing. The
> body stays as the argument's record.

Rule 3: *discovery is automatic; nothing enumerates filters. Adding one must
require no edit to a registry.* `filters/__init__.py` names nothing, a test
enforces that, and the rule holds where it is checked.

It does not hold in `gui/`. Filter ids appear as string literals in five
modules:

- `gui/filter_tab.py` — `"block_signal"` at six sites, `"rescale"` at five,
  `"normalize"` at three, and one membership test over the whole five-step set
  (`("rescale", "normalize", "block_signal", "morlet_band", "windowed_count")`).
- `gui/chain_model.py` — the default chain is constructed from literal ids, and
  `describe` branches on them to render a step's caption.
- `gui/wizard_model.py` — the shelf's entries carry `filter_id` literals and one
  special case reads the chain's fps for `block_signal`.
- `gui/block_spin.py` and `gui/density_plot.py` — each reasons in prose about
  `block_signal`'s specific arithmetic.

Two of those five step ids — `morlet_band` and `windowed_count` — are not
filters at all. They are the tab-side temporal suffix (parity plan § 2), and
there is no module for discovery to find.

Adding a filter today therefore requires no registry edit and no GUI edit *only
if the user is content to reach it through the wizard's generic path*. Giving it
a place in the default chain, a caption, or a card body means editing three GUI
modules. The rule's own words — "adding one must require no edit to a registry"
— are satisfied by the letter; what the rule exists to prevent has simply moved
one layer up, into files no test looks at for this.

## Why not now

**`gui/param_form.py` already made this decision, deliberately and with its
reason recorded**: "The five parity steps have hand-built card bodies in
`gui/filter_tab.py`; this is for everything else the wizard can insert." The
generic path exists and works — `param_rows` builds a settings surface from the
registered params model, bounds and all, with no per-filter code. The five
exceptions are exceptions on purpose, because their card bodies are the *v1
parity surface*: the downsample knob that writes `rescale.scale` and
`block_signal.scale` in one gesture, the block spinbox with its derived floor,
the signal quick-switch. Those are not parameter rows and generating them from a
params model would mean inventing UI-hint metadata on `FilterSpec` — a
vocabulary designed against five instances, four of which are about to be
renegotiated.

**And it cannot be finished while two of the five have no module.** However good
a generic card body gets, `morlet_band` and `windowed_count` have nothing to
discover. Removing the enumeration requires the temporal chain to become real
pipeline nodes, which is `Mode.WINDOWED` in
`docs/todo/kernel-protocol-beyond-one-frame.md`, still deferred and still
waiting for a filter that needs it. Doing the GUI half first would leave three
ids discovered and two enumerated, which is the same enumeration with a longer
justification.

## What to not get wrong when it lands

**The temptation will be UI hints on `FilterSpec`, and that is the expensive
mistake.** `FilterSpec` is hashed into cache keys through its version, and
`core/filter_base.py` is deliberately free of anything a headless run does not
need. A `widget:` or `step_of:` field there puts presentation on the identity
line — rule 7's "nothing straddles" — and the first person to change a label
would face the question of whether to bump the version. The home for a chain's
presentation is `gui/chain_model.py`, which already exists to be exactly this
and already carries `kind_in`/`kind_out` for the same reason: *kinds are a
chain-model concept, not `FilterSpec` metadata*, in that file's own words. The
answer this item wants is the same answer one step further: **card bodies are a
chain-model concept too**, declared per step in one table under `gui/`, rather
than branched on by `filter_id` in three widgets.

That reframes the work and makes it much smaller than "make the GUI generic":
the enumeration does not have to disappear, it has to stop being *five copies*.
One table that a reader can check against the shelf is not what rule 3 forbids;
three widgets each branching on a different subset of the same ids is.
