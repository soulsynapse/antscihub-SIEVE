---
title: The project file is what the screen says, unless the user says otherwise
status: open
opened: 2026-08-05T22:46:28-07:00
priority: normal
gated_on: nothing — the open question was answered 2026-08-05 (below)
reads:
  - src/sieve/gui/main_window.py
  - src/sieve/gui/preferences.py
  - src/sieve/gui/document.py
  - docs/completed-todo/2026.07.28-no-save-prompts-keep-history.md
---

# The project file is what the screen says, unless the user says otherwise

**SIEVE already autosaves — just not to the file you opened.** Every undo-stack
step writes a whole `Project` into `<project>.sieve.yaml.history/`, debounced to
the event loop so one gesture is one snapshot, and File ▸ History rolls back to
any of them. Nothing automatic writes `<project>.sieve.yaml` itself; only Ctrl+S
does. So a session that opens a project, tunes for an hour and quits has every
parameter on disk and the opened file exactly as the last explicit save left it,
with `[*]` in the title throughout.

**Done looks like:** the project file matches the screen without anyone pressing
anything, and a preference turns that off for someone who wants the old
behaviour. Write-through is the default. `_history_timer` already fires on
precisely the right event — one user-meaningful action, drags pre-merged by
`SetReplicateROI.mergeWith` — so the write hangs off the same tick, with the
same flush in `close_video` and `closeEvent`.

**The one thing that has to change shape rather than be reused.**
`_write_project` announces `Saved <name>` in the status bar and pops a modal on
failure. Neither survives running per edit: the status line is where the render
summaries live, and a modal per keystroke into a read-only directory is the
failure the history writer already avoids by disabling itself once and saying
so. This needs a quiet variant carrying the history writer's discipline, with
Ctrl+S left as the explicit gesture that still warns modally.

## What was decided, and what it costs

The open question when this was investigated was whether write-through should be
unconditional, since **the project file is what the CLI reads** — `sieve run`
and the HPC handoff take that artifact, and Ctrl+S is currently the only gesture
that says *this* is the version I mean. Write-through removes that gesture: a
run launched while somebody is still dragging a threshold reads whatever the
knob happened to be at, and a CLI user gets no signal.

Answered by Kendrick, 2026-08-05: **a preference, defaulting to write-through.**
Not the third option the investigation raised — write-through plus a separate
explicit commit marking a version as the one meant for a run — because that
introduces a new concept into the model rather than changing GUI behaviour. The
concept is not dead: `checkpoints` and `outputs` on `Project` are already shaped
like it, and if the CLI ever needs a named version to run against, that is where
it lands and it should be argued there rather than smuggled in here.

The preference is what makes the cost recoverable: someone who relies on the
commit point turns write-through off and keeps it.

## Why this is an item and not just a queue entry

Two things will need to name this decision before it is old. `sieve detect
collapses into sieve run` and the deferred `HPC handoff, and review mode` both
consume the project artifact, and both inherit whatever answer this gives about
what "the version I meant" means. A conclusion reached in a session reply and
implemented without a slug leaves them nothing to point at.
