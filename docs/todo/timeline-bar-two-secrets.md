---
title: timeline_bar.py holds two secrets
status: open
priority: unassessed
gated_on: >
  nothing structurally
reads: [src/sieve/gui/timeline_bar.py, src/sieve/gui/timeline_model.py]
---

# timeline_bar.py holds two secrets

`gui/timeline_bar.py` was picked up for the docstring-convention pass
(`docs/todo` guardrail: one module docstring stating the file's one secret,
no docstrings elsewhere, 400-word prose cap) and does not fit — not because
it is long, but because it is two widgets, each hiding a different decision,
sharing one file:

1. **`TimelineStrip`** (lines 137–474): the painted band itself. Its secret is
   the geometry/state-ownership model — the strip owns no window or playhead
   state, only a per-paint `Geometry` mapping and a transient drag `_draft`;
   the three-mouse-event classification (press commits, move scrubs, release
   commits) and why a window drag is two-tier (paint-only until release,
   because `commands.SetClip` has no `mergeWith`). The existing module
   docstring is entirely about this class.
2. **`TimelineBar`** (lines 477–713): the strip plus the row of controls
   above it (play button, start/length spin boxes, timecode label), wired
   straight to `ReplicateDocument` and `VideoPlayer`. Its secret is the
   feedback-loop discipline: `_updating` guards spin-box `valueChanged` while
   the boxes are being written *from* the document so a rounding round-trip
   doesn't push a spurious undo command, `_on_window_changed` is the single
   place that tells the player about a window change (because a mark, a
   strip click, a typed number, and an undo all converge on `clip_changed`
   and a transport told from two places would be bounded by whichever spoke
   last), and why the document rather than the player owns the binding order
   in `_connect`.

These are not two views on one idea — they'd change for unrelated reasons
(a new hit-test zone on the band vs. a new control in the row) and one
already contains most of the file's prose on its own: `TimelineStrip`'s
docstrings alone (class + 13 methods) run to 753 words, more than the
400-word whole-file cap by itself, before its share of the file's 643
comment words is even counted. Bringing the file to the convention by
picking one secret and deleting/moving the other's prose isn't available —
both are real and neither has anywhere else to go.

**Co-change check**: not applicable in the form CLAUDE.md prescribes — the
two classes have never existed as separate files, so there is no git history
of them being edited together or apart to count. What the 9 commits touching
this file show instead: every commit's diff has hunks in both classes,
because the whole point of `TimelineBar` is to push `TimelineStrip`'s output
(the drag results, the clicks) at the document/player, so a change to what a
gesture means routinely touches both the emitting method in `TimelineStrip`
and the receiving slot in `TimelineBar`. That is arguably load-bearing
coupling in the *code*, but it does not make the *prose* one secret, and it
does not by itself argue against a file split — a signal/slot boundary
between two files is exactly what Qt widget composition already looks like
elsewhere in `gui/` (e.g. `player.py` and the tabs that wire to it).

**Recommendation**: split into a new `timeline_strip` module under `gui/`
(the `TimelineStrip` widget, `Grab`, `format_timecode`, the module docstring
already written) and keep `gui/timeline_bar.py` for `TimelineBar` alone
with its own new module docstring stating the wiring-discipline secret. This
is an architecture call (new module, a `SCAFFOLD.md` entry, import-linter is
unaffected since both stay in `sieve.gui`) and belongs to Kendrick, not to
this pass.
