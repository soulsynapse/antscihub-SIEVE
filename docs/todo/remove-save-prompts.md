---
title: Take the save prompts out, now that rollback exists
status: open
opened: 2026-07-28
gated_on: >
  nothing — the autosave half landed 2026-07-28
  (docs/completed-todo/2026.07.28-no-save-prompts-keep-history.md), which was
  the only thing this waited on: the reason `confirm_discard` exists is now
  transferred, not retired
reads:
  - src/sieve/gui/main_window.py
  - src/sieve/gui/history.py
  - docs/completed-todo/2026.07.28-no-save-prompts-keep-history.md
---

# Take the save prompts out, now that rollback exists

The back half of `no-save-prompts-keep-history`, split off when that item was
scoped to the autosave subsystem. Everything here was decided there; nothing
new is being chosen.

**The order was the whole argument.** `confirm_discard` exists because every
path it guards silently destroyed a session's work. Deleting it first would
have opened a window in which *neither* net was in place. Rollback now is that
net: an edit reaches `<project>.sieve.yaml.history/` within one event-loop turn
of the command that made it, and File ▸ History restores any of them as an
undoable action.

## What comes out

`confirm_discard` (`main_window.py`) and its four call sites —
`open_video_dialog`, `open_project_dialog`, `close_video`, and `closeEvent`.
Each becomes an unconditional proceed. `UNSAVED_PROMPT` goes with it.

The neighbour-project modal is already gone: it became `_open_neighbour_project`
in the same round, announcing the restore in the status bar rather than asking.

## What has to be checked on the way out, not assumed

- **`closeEvent` currently flushes a pending snapshot before shutting the
  player down.** That flush is not part of the prompt and must survive: it is
  what keeps the last edit of a session in the history. The `confirm_discard`
  call above it is what goes.
- **`save_project`'s return value exists for `confirm_discard`.** With the
  prompt gone, `save_project` and `save_project_as` no longer need to report
  whether anything was written — but Save and Save As stay, because a project
  file the user chose the location of is a different artifact from a session
  history, and nothing here replaces it.
- **`tests/gui/test_project_io.py` has two tests that deliberately refuse a
  close.** They assert the prompt's behaviour and will have to be rewritten as
  assertions that the close proceeds and the work is in the history.
- **`tests/gui/conftest.py`'s `no_modal_dialogs` fixture** answers
  `QMessageBox.warning` with Discard specifically so teardown can finish. Once
  nothing asks, that answer stops being load-bearing; the fixture still earns
  its place for the failure dialogs `_warn` raises.

The estimate in the parent item was ~70–90 lines. That was a reading of the
code, not a measurement, and it did not include the test rewrites above.
