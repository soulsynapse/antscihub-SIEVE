---
# ---- identity -------------------------------------------------------------
title: Replicate tab                      # short name, under five words
up: (not sure, you'll have to fill this out)
status: deferred                          # open — takeable now | deferred — timing is the decision
opened: 2026-07-27                        # the day the item was written

# The one-line gate. For an open item this is usually
# `nothing structurally`; for a deferred item it is the trigger — the event
# that makes it the right time, compressed to a line the .state.md table can
# carry. The full argument stays in the body; this line must not replace it.
gated_on: >
  the first filter that emits a TableSpec, or materialization landing

# The files to open before the first edit, so starting is opening rather than
# searching. An item needing three documents read before the first edit is
# not scoped yet.
reads: [src/sieve/core/pipeline_model.py, src/sieve/cli/run_cmd.py]
---

# Sink writers

Body is free prose and is the item. What belongs here, by status:

**Every item**: scoped to fit one context window, written so the work can
start without loading the whole doc tree.

**A deferred item** additionally says *why not now* — the actual reason, not
"no time": nothing exercises it yet, the design question needs a workload to
answer, or it is downstream of work that has not happened. Where the argument
rests on arithmetic rather than a measurement, it says so; the first step of
acting on it is taking the measurement, and an unflagged extrapolation is how
a guess becomes a premise. Constraints worth recording before the work starts
("the thing to not get wrong when it lands") go here too — they are the part
that costs a day if re-derived.

---

## How to use this file

Copy to `docs/todo/<short-kebab-name>.md`, delete this section, fill it in,
run `uv run nox -s docs`. One file per item.

- **Promotion** (deferred → open) is a one-line edit to `status:` when the
  trigger fires — plus rescoping the body if it has aged.
- **Completion is a move, never a mark**:
  `uv run python tools/complete_item.py <slug>` moves the file to
  `docs/completed-todo/YYYY.MM.DD-<slug>.md` and swaps in the completion
  frontmatter. The body written here is *not* carried across — fill the entry's
  `summary` and stop. This body stays in git.
- **This folder is not a second `SCAFFOLD.md`.** A module that merely does
  not exist yet is SCAFFOLD's line, not an item. An entry here is work with
  reasoning — open work, or a deferred decision with a trigger.
- **Measurements go to `docs/findings/`**, from here as from everywhere.

Required frontmatter: `title`, `status`, `gated_on`. `reads` is close to
mandatory in practice. `tests/docs/test_todo_hygiene.py` enforces the status
vocabulary; `.index.md` and `docs/.state.md` are generated from these fields.
