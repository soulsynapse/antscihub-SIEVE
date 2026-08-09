---
title: A band's axis has no vocabulary and no plot to be dragged on
priority: normal
phase: "07"
status: done
gated_on: nothing
done_when: "uv run pytest tests -q -k declared_surface"
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

## Ruled 2026-08-09: declared display surfaces

Kendrick's ruling: SIEVE grows the display surface, as a declaration. A band
param names the surface kind that edits it — scalogram, threshold-on-trace,
count — and the execution side grows a preview-only display channel the tool
fills: not a product, not cache-keyed, never selectable. The enum names the
surface and not the unit; units ride with the data at runtime, which is what
the phase-1 vocabulary objection cannot reach. `gui` stays kinds-not-tools —
a surface kind is a kind — and `declared-means-verified` holds by refusing at
registration a declared surface nothing fills, or a filled channel nothing
declared. The referent's tuning centerpiece
([adr/the-mockup-is-the-gui-end-state.md](../adr/the-mockup-is-the-gui-end-state.md))
is what this mechanism feeds.

Boundaries the ruling sets rather than leaves open: splitting detect into
smaller tools is *not* part of this — if the display channel makes that
attractive later it is a separate decision against 04.8. And the mechanism is
minted once: the canvas-ownership problem (what a tool shows on the canvas,
MOCKUP-MAP.md's first non-settlement) should be answered by this same
declaration vocabulary or by a revision of it, not by a second parallel one.
Minted at the review that landed the mechanism as
[adr/a-band-declares-the-surface-it-is-dragged-on.md](../adr/a-band-declares-the-surface-it-is-dragged-on.md),
which is the home for what binds; this section is the argument that reached it.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k declared_surface
    1000 deselected in 0.89s
    exit: 5
