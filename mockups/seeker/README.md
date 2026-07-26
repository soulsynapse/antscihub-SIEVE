# Bottom seeker bar

A clickable refinement of the cross-tab timeline (`gui/timeline_bar.py`),
loaded with everything docs/filter-tab-parity-plan.md routes to it: the
Length control, detection marks, and the coverage story v1's navigator strip
proved necessary (which spans have been examined, and under which settings).

## Run

```
uv run python mockups/seeker/seeker_bar.py --variant lanes
uv run python mockups/seeker/seeker_bar.py --variant split
```

PNG review: `--shot {hover,drag} --png out.png`.

## The two variants

- `lanes` - one strip carries it all: log-height signal bars tinted by
  coverage (lit = examined under current settings, gray = other settings,
  dark = never), green detection ticks along the top edge, the working
  window as a teal bracket. Compact (64 px); ticks and the window header
  share the top edge.
- `split` - a thin status lane (detections + coverage echo) above a scrub
  lane. Nothing overlaps; costs 14 px and a hairline of separation.

## The interaction contract (what is being pinned)

1. **Scrub semantics are unchanged from v2**: press = seek (commitment),
   move = scrub (guess), release = commit. The narration line names each
   phase as it fires.
2. **The window is directly manipulable on the strip**: drag an edge handle
   to resize, drag the header band (the darker strip along the window's top)
   to move it whole; anywhere else is a scrub. Hit order: edge (6 px) >
   header > scrub. Minimum window: 1 s - shorter is treated as a misclick.
3. **The Length spinbox and the bracket are two views of one value** and
   stay in lockstep; editing Length pins the window start and moves the end.
4. **Window drags are two-tier** like every band drag in this UI: continuous
   moves update the outline only; release commits (and would trigger the
   re-render). The narration names the tier.
5. **Detection ticks are floored to 1 px** (the 1-frame detection at 4,210
   stays visible); `|<` / `>|` jump the playhead to the previous / next
   detection start. Green remains a status color, used for nothing else.
6. **Coverage is a first-class encoding, not decoration**: three states
   (current settings / other settings / unexamined) tint the signal bars,
   and the hover bubble states it in words - "examined - OTHER settings" is
   the honesty v1 encoded with lit/gray/dark bars.
7. **The hover bubble** shows timecode + frame, the coverage state, and the
   nearest detection within 1.5 s; it floats at the strip's top and clamps
   to the widget, never following the cursor off-screen.
8. **The strip owns no truth** - window and playhead are set in, drags
   signal out; identical to the `TimelineStrip` discipline it replaces.

## What to feel for

Whether `lanes`'s top edge gets crowded where detection ticks, the window
header, and the playhead flag coincide - that is the case `split` exists
for. And whether grabbing the header band to move the window is
discoverable enough without a tooltip.

## What is fake

Signal, coverage spans, detections, palette, and the play button (it
toggles a label; transport belongs to `VideoPlayer`). The scrub/window/
detection/coverage interactions are the real proposal.

## What survives

Per `mockups/README.md`: the contract above, folded into the TODO item that
extends `gui/timeline_bar.py`; then this folder is deleted.
