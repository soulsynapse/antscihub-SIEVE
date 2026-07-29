---
# ---- identity -------------------------------------------------------------
title: Sink writers                       # short name, under five words
status: deferred                          # open — takeable now | deferred — timing is the decision
                                          # | superseded — scope moved; name it in superseded_by
                                          #   and keep the file so references resolve
opened: 2026-07-27                        # the day the item was written

# How much it matters, which is a different axis from `status`: a deferred
# item can be `high` and an open one `low`. Ordering everything the tools
# generate — both index tables and the primer's lists.
#
#   high        the cost of not doing it is already being paid, or it makes
#               something else unsafe to build on
#   normal      real work with no reason to jump the queue
#   low         worth doing, cheap to keep not doing
#   unassessed  nobody has ranked it — the honest default, and it sorts last
#
# `unassessed` is spelled out rather than left blank because an absent field
# is invisible: nobody reading the table can tell it from `normal`, and nobody
# editing the file ever sees the question.
priority: unassessed

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
- **Re-ranking** is a one-line edit to `priority:`. It is the same kind of
  edit and deliberately independent of it: a trigger firing does not make an
  item matter more, and an item mattering more does not make its trigger fire.
- **Completion is a move, never a mark**:
  `uv run python tools/complete_item.py <slug>` moves the file to
  `docs/completed-todo/YYYY.MM.DD-<slug>.md` and swaps in the completion
  frontmatter. The body written here is *not* carried across — fill the entry's
  `summary` and stop. This body stays in git.
- **This folder is not a second `SCAFFOLD.md`.** A module that merely does
  not exist yet is SCAFFOLD's line, not an item. An entry here is work with
  reasoning — open work, or a deferred decision with a trigger.
- **Measurements go to `docs/findings/`**, from here as from everywhere.

Required frontmatter: `title`, `status`, `priority`, `gated_on`. `reads` is
close to mandatory in practice. `tests/docs/test_todo_hygiene.py` enforces both
vocabularies; `.index.md` and `docs/.state.md` are generated from these fields.
