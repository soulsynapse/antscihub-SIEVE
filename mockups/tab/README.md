# The whole filter tab: the stack hosts the graphs

The frame from `docs/filter-tab-parity-plan.md` - video left with the green
blocks-in-band graph and detection window D under it, seeker (with Length)
across the bottom - with the **operation stack** as the right column and
the graphs and parameters living inside its blocks.

## Run

```
uv run python mockups/tab/whole_tab.py
uv run python mockups/tab/whole_tab.py --shot wizard --png out.png
# shots: tuned, lk, conflict, wizard, wizard-spatial
```

Startup precomputes two Morlet cubes, so the signal swap genuinely changes
every graph.

## What lives where

| step card | body |
|---|---|
| rescale | Downsample spinbox |
| normalize | mode combo |
| block signal · … | Block spinbox + the quick-switch (two checkable swaps) |
| morlet band | the scalogram (and, when the wizard is closed, the band-power density graph) |
| windowed count | threshold/D caption; a note that its graph and D live under the video |

## The wizard (this revision's change)

A seam click - or a card's `swap` - opens a near-full-window inset helper.
It is the *configuration surface for the provisional step*, not a picker
with a description. Success criteria it was built to (2026.07.26):

1. **The video stays visible and live.** Center-top: the current frame
   (playback mocked as a still) with the provisional chain's spatial ops
   genuinely applied - `denoise` blurs it, `rescale` pixelates it,
   `zscore` restretches it. Hovering candidates visibly re-edits the
   picture.
2. **The graphs below it**, fully live: the band-power view with draggable
   value handles, and below that the green detection graph - gate spans,
   count threshold handle, D slider, centered toggle, and the detections
   summary - borrowed whole from the left column while the wizard is open
   and returned on close. A candidate is judged by what it does to the
   green, so the green is in the room.
3. **The filter's own settings** - the same widgets its stack card owns -
   in the right column, **with the guidance below them**. (The success
   criteria stacked settings+md under the video; on a wide window that
   starved everything, so they moved to a right column - judgement call,
   2026.07.26.)
4. **The selector is also the equivalents switcher**: the left list holds
   what fits this seam, hover/click swaps the provisional step in place,
   so comparing candidates and configuring one are the same surface.
5. **The wizard cannot break the chain**: operations that would break the
   step below, or duplicate a step already present, are listed but
   disabled with the reason ("breaks below" / "in chain"). The suggested
   category leads the list. The full inference ruleset is real-
   implementation work; this pins its UI shape.
6. Add commits; Cancel or Esc restores everything exactly as it was.
   While the wizard is open the whole tab behind it is the preview - the
   dashed provisional card sits in the chain, and the count plot under the
   (dimmed) video keeps painting detections.

## Other decisions carried

- Quick-switch on the block-signal card: one click swaps Jtt/LK, bands
  kept, no wizard.
- Removal visible: hover any card for `swap` / `x`; conflicted cards
  (now only reachable via removals or loaded files) keep inline
  Swap/Remove and the permit-then-repair treatment.
- Graphs belong to the step that produces them; no reachable step, no
  graph, and the left column says why.
- Reset is parameters-not-structure.
- One narration line (in the seeker); two playheads locked through the
  working window.

## Open questions

- Bands across a signal swap are kept; `--shot lk` shows the consequence.
  v1 remembered value bands per channel.
- Hover-preview recompute wants the coalescer tier against real render
  costs (here it is synchronous against precomputed cubes).
- Seeker scrub outside the window: clamp (current) vs. move the window.

## What is fake

Everything the component mockups fake, plus: the wizard's video effects
are numpy approximations (pixelate / affine restretch / box blurs), the
temporal helpers act post-transform, playback is a still, and inserted
steps without effects join the chain without transforming data.

## What survives

The assembly decisions and the answers to the open questions, recorded in
plan item 6 when the real tab is built; then this folder is deleted.
