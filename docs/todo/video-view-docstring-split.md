---
title: video_view.py docstring split
status: open
priority: unassessed
gated_on: >
  a Kendrick decision on whether VideoView should be split along the
  geometry/gesture seam, or whether the file should join CONTRACT_MODULES
  instead of splitting
reads: [src/sieve/gui/video_view.py, src/sieve/gui/zoom.py, tools/docstring_audit.py]
---

# video_view.py docstring split

`gui/video_view.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep. It is flagged rather than brought to the
convention: the module docstring cannot be reduced to one sentence naming one
secret, because the class hides several.

**The docstring already admits this.** It is organized as three separately
bolded sections after the lead paragraph — the source-pixel-vs-proxy
coordinate rule and the `content_rect`/`view_rect` split, crop-mode
single-ownership (the widget, not the tools panel, decides `DRAW` vs
`STAMP`), and adjustment-restricted-to-the-selected-replicate — plus a fourth,
undeclared in the module docstring's own structure but present at length in
method docstrings and comments: the gesture-interpretation state machine
(click-vs-drag via `MIN_DRAG_PX`, handle-before-containment hit-test
ordering, the draw-then-flip-to-stamp workflow, and per-drag undo-token
collapsing in `_Adjustment`/`roi_adjusted`). The file's own section comments
(`# ---- content`, `# ---- tools`, `# ---- geometry`, `# ---- input`,
`# ---- painting`) already partition it along the same lines.

**The measurement.** 1,994 words of prose against the 400-word cap (410-word
module docstring alone, over the 250 cap by itself; 39 symbol docstrings
totaling roughly 1,020 words; 564 words of comments) — over by 1,594, close to
5x.

**Co-change check.** `git log --no-merges -- src/sieve/gui/video_view.py`
shows 12 commits touching the file; `git log --no-merges --name-only` on that
same path list shows every one of those 12 commits touched `video_view.py`
alone — no other file in the repo has ever changed in the same commit as
`video_view.py`. As with `player.py`'s prior flag, this is not evidence *for*
a specific split seam (there is no candidate file it already co-changes
with, because there is no second file yet), and it does not argue against
splitting either — read it as: the check has nothing to confirm or refute
here.

**Candidate seams, unranked** — offered as material for the split decision,
not a recommendation:
1. **Coordinate/geometry mapping** (`content_rect`, `view_rect`, `source_at`,
   `to_source`, `to_widget`, `_placed`) depends only on `_source_size` and
   `_magnifier` — never on selection, mode, or an in-progress gesture. It is
   already the thing `gui/zoom.Magnifier` is described as the other half of
   in the current module docstring ("this widget owns the fit and the
   source-pixel units, and the magnifier owns everything between them"),
   which is itself a hint the seam is real and one side of it already lives
   in its own file.
2. **Crop-mode and gesture interpretation** (`mode`, `set_mode`, `stamp_size`,
   `set_stamp_size`, `_take_stamp_from_selection`, the mouse/key event
   handlers, `_Adjustment`, `_handle_at`/`_handle_rects`,
   `_over_movable_selection`, `_release_click`, `_cancel_gesture`) is the
   interactive state machine proper — it would change for workflow reasons
   (a new gesture, a new mode) unrelated to why the geometry math would
   change (a new zoom/pan rule).
3. **Painting** (`paintEvent` and the four `_paint_*` methods) reads state
   from both of the above and from `Replicate`/`_selected` but decides
   nothing — it is the one axis where a Qt widget's own paint override
   staying with the widget is the ordinary shape of Qt code, so this is the
   weakest candidate for extraction of the three.

**What this item is asking Kendrick to decide**, one of:
1. Split `VideoView` along the geometry/gesture seam (or a different one),
   each new file getting its own one-secret docstring under the ordinary
   250/400 caps.
2. Add `gui/video_view.py` to `CONTRACT_MODULES` in `tools/docstring_audit.py`
   (600/900-word caps) on the reasoning that the coordinate-precision
   argument (source pixels, never the proxy) is a contract every future
   crop-drawing code must honor, closer to `cache_key.py` than to an
   ordinary view.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `video_view.py` was changed by this pass.
