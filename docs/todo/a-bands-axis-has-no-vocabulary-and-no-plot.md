---
title: A band's axis has no vocabulary and no plot to be dragged on
priority: normal
phase: "07"
status: deferred
deferred_for: decision
gated_on: how a band names its axis, which one enum cannot carry across Hz, a runtime-dependent unit, and a fraction — and which two of detect's three bands have no plot to name at all
opened: 2026-08-08
---

# A band's axis has no vocabulary and no plot to be dragged on

`ParamStereotype.BAND` is defined on the pair and not on the plot: an ordered
lo/hi on a value axis rather than the time axis. Its docstring says *which* plot
the handles are grabbed on "is undeclared and arrives with the generator that
has to know". Two generators have now arrived —
[the widget generator](the-generator-builds-widgets-from-stereotypes.md) (07.5)
and [the editors](composite-kinds-get-their-editors.md) (07.8) — and neither can
carry it. This is where it waits, so the docstring's promise has a referent
rather than a generator that will never claim it.

The shelf's only band-carrying tool is `detect`, with three: `freq_band` in Hz
over the Morlet bank, `value_band` as per-block band power in the incoming
signal's units, `count_frac` as a fraction of the region's blocks. Two things
are true about all three at once, and either alone would be enough to stop a
declaration:

**No vocabulary covers them.**
[a-band-has-no-stereotype-of-its-own.md](a-band-has-no-stereotype-of-its-own.md)
ruled this at phase 1 while minting the kind: an axis enum cannot be honest
across a fixed physical unit, a unit that is not knowable until the upstream
node runs, and a dimensionless fraction. 07.8 as opened proposed the missing
declaration be a named emit of the tool's own `emissions` list, which fails for
a second reason — `detect.emissions` is exactly `("gate",)`, and its own
registration comment says the three band series never leave the node. That
binding would have `detect` name `"gate"` three times: well-formed, verified,
and false, which is what `adr/declared-means-verified.md` refuses. Widening
`emissions` is closed off by `_check_emissions`, which requires a multi-product
list to be exactly one closed-set selector's values; these are intermediates
nobody selects.

**No plot holds two of them.** `pipeline/series_collector.py` assembles one
node's per-frame *outputs* and `gui/graph_panel.py` draws exactly that, one
value per frame or nothing. `value_band` could sit on the upstream node's trace
under that rule. Hz over the Morlet bank is not a per-frame series at all, and a
fraction of a region's blocks is not one either — so even a perfect vocabulary
would leave two of three bands with handles and nowhere to grab them.

So the question is not "what does a band declare" alone. It is whether SIEVE
grows a surface that plots what a tool computes and does not emit — which is a
second display vocabulary, not a field — or whether `BAND` stays a widget with
no handoff surface and the tuning loop's `Band drag → graphs repaint` row in
VISION's budget table is answered by the value band alone. That is a decision,
which is why this carries no criterion: what the command would assert is the
thing being decided.
