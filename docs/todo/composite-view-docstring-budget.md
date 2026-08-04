---
title: composite_view.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file,
  or fold it into CONTRACT_MODULES alongside cache_key.py
reads: [src/sieve/gui/composite_view.py, tools/docstring_audit.py]
---

# composite_view.py docstring budget

`gui/composite_view.py` was picked by `tools/docstring_audit.py --next` for
the docstring-convention sweep (module docstring stating the file's one
secret; no class/function docstrings elsewhere; 250/400-word caps). It is
flagged rather than brought to the convention.

**The secret is genuinely one.** `StepCompositeView` shows the *contribution*
of the selected step — the pixels it removed, kept, or invented — as either
two images blended by opacity (`base`/`over`, the step's input and output) or,
when the composed output is a block grid, a heatmap-plus-detection overlay
drawn directly instead of a second image. Both renderings share one rectangle
(`view_rect`, fed by the same `Magnifier` the replicate tab's viewport uses)
so image, grid, and hit-test cannot register against different pixels, and one
gesture discipline: the pane only *emits* what the pointer is doing
(`solo_toggled`), never applies it — the state model decides what is actually
soloed, and the widget redraws only once told. That is one widget's one job,
not several.

**What does not fit is the budget.** The tool's own measurement: 788-word
module docstring alone (over the 250 cap by itself), 38 symbol docstrings, 507
words of comments, 2,346 words of prose total against the 400-word cap — over
by roughly 6x. The excess is not restated signature or control flow; it is
one-off, underivable reasoning specific to one method or constant:
- why `grid_edges` rounds the *line* rather than each cell's own origin and
  extent (two neighbouring cells reading the same rounded number is what
  closes the seam; computing each cell's edge independently reintroduces a
  one-ULP gap that shows up as an unblended row across the heatmap);
- why `block_at` runs two containment tests, not one (a magnified grid extends
  under the letterbox where nothing is painted, so the fit rectangle has to
  gate the grid rectangle or a click on bare panel solos a cell that isn't
  visible);
- the wall-ownership asymmetry in `_paint_grid` (every cell owns its top and
  left pixel line and gives up bottom/right to its neighbour unless there is
  no detected neighbour to give them to) and why that trade is made — one
  wall pixel painted exactly once so the ring alpha means one thing on screen,
  at the cost of an asymmetric rule;
- the emit-not-apply gesture protocol split across `_solo_now`, `_emit_solo`,
  `_set_hover`, and `clear_solo_gesture` — why `_emit_solo` compares against
  `self.solo` (the model's last-applied value) rather than a private record of
  what was last sent, why hover fires per block *crossing* rather than per
  mouse sample, and why `clear_solo_gesture` emits rather than going silent
  (rule 6's mirror direction: a stale pin over a vanished grid must not read
  as still-soloed);
- why `mousePressEvent` treats unpinning while still hovering as asking for
  nothing new (hover already solos the block; the click only changes what
  `leaveEvent` reverts to);
- the VISION-history note that raw video and full current state are not modes
  of this widget but degenerate cases of "the composite at the selected step"
  (first step at full opacity; tail step selected), which is why the widget
  has no mode switch to document elsewhere.

Each of these is local to its one symbol or one paragraph, underivable from
the code, and has no other natural owner — there is no `docs/findings/` entry
these numbers come from, no filter `.md` this belongs beside, no architecture
rule this restates. Folding 38 of these into one 250-word module docstring
would not compress them, it would delete them — clause (c) of the flag path:
"the prose is load-bearing in a way the budget would destroy... it records
why the code is the shape it is in a way the code cannot."

**No split is proposed.** The image-compositing path and the block-grid path
share the one rectangle and the one gesture protocol by construction — that
sharing (`view_rect`, `_content_rect`, the hover/latch state machine) is
exactly the thing a split would have to duplicate or thread across a new
file boundary, and duplicating it is the failure mode the shared rectangle
exists to prevent. There is no candidate second file with its own git history
to run CLAUDE.md's co-change check against.

**What this item is asking Kendrick to decide**, one of:
1. Add `gui/composite_view.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed) — it is the one place a reader learns the pixel-registration
   contract between the grid, the image, and the hit test, and the
   emit-not-apply gesture rule the density plot's soloing depends on.
2. Accept the loss and force the file to the convention anyway, moving
   whatever survives triage into the module docstring and accepting that the
   rest (the per-method rounding, wall-ownership, and gesture reasoning) is
   deleted rather than relocated, since nothing else in the doc tree owns
   per-method rendering rationale at this grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `composite_view.py` was changed by this pass.
