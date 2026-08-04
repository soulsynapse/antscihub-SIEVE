---
title: player.py docstring split
status: open
priority: unassessed
gated_on: >
  a Kendrick decision on whether VideoPlayer should be split along the
  render-feed/tracing seam, or whether the file should join CONTRACT_MODULES
  instead of splitting
reads: [src/sieve/gui/player.py, src/sieve/gui/coalescer.py, src/sieve/gui/scrub_policy.py, src/sieve/gui/timeline_model.py, tools/docstring_audit.py]
---

# player.py docstring split

`gui/player.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep. It is flagged rather than brought to the
convention: the module docstring cannot be reduced to one sentence naming one
secret, because the class hides several.

**The docstring already admits this.** It is organized as four separately
bolded sections — Request coalescing, Adaptive coarse scrubbing, A bounded
transport, Wall-clock playback — plus a fifth paragraph on the retention
tracer, plus (undeclared in the docstring's own structure but present in the
method docstrings) a sixth: render-feed gating, spread across `_feed_ring`,
`set_render_filling`, `_display_from_ring`, and `render_fed`. Four of six are
each already delegated to their own module (`RequestCoalescer`,
`ScrubPolicy`, `timeline_model.py`'s `feed_bounds`/`playback_step`,
`TraceRecorder`) — `VideoPlayer` is the thing that wires them to Qt, a
decode thread, and each other. That wiring is itself a real decision, but it
is not *one* decision; it is "here is how N independently-owned policies
compose against one thread and one cache," which is why no single sentence
covers it.

**The measurement.** 2,077 words of prose against the 400-word cap (494-word
module docstring alone, 34 symbol docstrings, 490 words of comments) — over
by roughly 5.2x, the worst in the repo by absolute overage.

**Co-change check.** `git log --no-merges -- src/sieve/gui/player.py` shows
18 commits touching the file; `git log --name-only` on that same path list
shows every one of those 18 commits touched `player.py` alone — no other file
in the repo has ever changed in the same commit as `player.py`. This is not
evidence *for* a specific split seam (there is no candidate file it already
co-changes with, because there is no second file yet), and it does not argue
against splitting either — a file that has never had a sibling to co-change
with is exactly what "the wiring class swallowed several policies instead of
being split from the start" looks like. Read it as: the co-change check has
nothing to confirm or refute here, not as a seam that "held."

**Candidate seams, unranked** — offered as material for the split decision,
not a recommendation, since which of these (if any) should move is an
architecture call:
1. **Render-feed gating** (`_feed_ring`, `render_fed`, `set_render_filling`,
   `_display_from_ring`, the `_viewport_luma` interaction) is the newest
   addition by feel — it is the one policy not already factored into its own
   module, and its three gates (`render_fed` preference, wiring, luma) are
   already self-contained enough to be described in one paragraph, which is
   what a `RenderFeedGate` class's docstring would be.
2. **The retention-tracing hook** (`_trace`, `_record`, the `AccessEvent`
   construction in `_on_frame_ready`/`_go_to`) is instrumentation, off by
   default, and already described as querying a file the render ring also
   writes to — it reads like a cross-cutting concern threaded through the
   request path rather than part of transport logic proper.
3. **Wall-clock playback + bounded transport** (`play`, `pause`, `timerEvent`,
   `_anchor_playback`, `_bounds`, `_clamp`, `set_window`, `set_playback_rate`)
   are the two sections most entangled with each other (the clock's target is
   folded through the window's bounds every tick) and are the best candidate
   for staying together as "the transport."

**What this item is asking Kendrick to decide**, one of:
1. Split `VideoPlayer` along one or more of the seams above (or a different
   one), each new file getting its own one-secret docstring under the
   ordinary 250/400 caps.
2. Add `gui/player.py` to `CONTRACT_MODULES` in `tools/docstring_audit.py`
   (600/900-word caps) on the reasoning that a Qt wiring class integrating
   five already-factored policies is structurally closer to a contract module
   than to an ordinary filter or view.
3. Leave it flagged permanently.

No code or docstring in `player.py` was changed by this pass.
