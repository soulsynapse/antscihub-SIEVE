# Detection graphs & interactions

A clickable mockup of the visualization widgets — since shipped as
`src/sieve/gui/band_plot.py` and its subclasses — plus the color-gate stretch
goal, which is the only part of this folder not yet built.
Unlike a layout sketch, the data under these plots is real math on synthetic
footage — 64 blocks, three 12 Hz bursts in a 4x4 cluster, one single-frame
spike, and a true Morlet transform — so every drag honestly recomputes what
the real widget would recompute. That is the point: the interaction tiers
are felt, not asserted.

## Run

```
uv run python mockups/graphs/detect_graphs.py --variant detect
uv run python mockups/graphs/detect_graphs.py --variant color
```

PNG review: `--shot {tuned,solo,sampled} --png out.png`.

## The four linked views (variant `detect`)

| view | shows | drag does |
|---|---|---|
| scalogram | pooled Morlet power, log-f axis, COI faded | frequency band (clamped to bank edges) |
| band power by block | time x value density heatmap of all blocks, log1p axis | value band (off the top = unbounded) |
| blocks in band | windowed count line + green detection spans | count threshold |
| block heat | frame + block grid: fill = band power at playhead, outline = in band | click = solo that block's trace in the density plot |

## The interaction contract (what is being pinned)

1. **One drag gesture, two meanings.** A drag that starts within 8 px of a
   handle moves the handle; any other drag scrubs the shared playhead across
   all views. No modes, no toolbars.
2. **Two event tiers per handle.** `band_changed` fires per mouse-move and
   drives only cheap re-derivation (re-sum, re-count, repaint);
   `band_committed` fires on release and is the hook for anything expensive.
   The footer narrates both so the split stays felt.
3. **Unset ≠ unbounded for the count threshold.** An unset threshold means
   the detector is *disarmed*: no green anywhere, footer says so. This is a
   deliberate deviation from v1, where unset meant unbounded and a fresh tab
   painted everything as a detection. Value/frequency bands, by contrast, do
   default to wide open — they shape a signal, they don't claim an event.
4. **Handles read out at the right margin** (dot + value; `inf` when
   unbounded, dimmed when unset). The title bar carries the *effective* band
   — for frequency that is the snapped bank rows, which may differ slightly
   from the handle positions, and showing the truth there is intentional.
5. **Gate spans are floored to 1 px** so a single-frame detection cannot
   vanish at any zoom.
6. **Green is a status color.** It appears only as detection (spans, count
   line when armed, summary text) and never as a data series. Magnitude is
   one sequential ramp per surface: warm for the scalogram, cyan for the
   density plot. Text stays in text colors.
7. **Plots own no detector state.** The window owns one `Detector` value;
   `derive()` is the whole chain as a pure function; `_apply()` is the one
   place state becomes pixels. Widgets get setters and emit drags.
8. **The density plot is all blocks at once** (per-frame value histogram),
   not a mean line — the detector counts blocks, so the graph the user tunes
   against must show the population the count comes from. Solo exists for
   the opposite question ("what is *this* block doing").

## Variant `color` — the stretch goal

Configure a "detected color" channel by pointing at the paused frame:
click = this color counts, Shift/right-click = this color must not count.
Samples become removable swatch chips (red edge = exclusion), one tolerance
slider widens the gate, the mask repaints live, and the headline reads the
coverage. The panel's caption states the integration contract: the gate
becomes one more per-block channel (fraction of the block's pixels in gate),
feeding the same temporal filter and detector as every other signal.

Not built, deliberately: a hue/saturation map of the samples, per-sample
tolerance, and any real color-space distance (the mockup uses RGB distance;
the real channel should use a perceptual space — that is a filter-design
question, not an interaction question).

## What is fake

The block series, the costs of nothing (no budgets here), the palette. The
Morlet transform, the detection chain, the COI fade, and every interaction
are the real proposal in miniature.

## What survives

Per `mockups/README.md`: the contract above, recorded in the TODO items that
build `band_plot.py` / `scalogram_plot.py` / the tab (plan items 5-6), and
the chosen answers to the open questions; then this folder is deleted.
