---
title: Deferral should expire by default, not persist by default
status: open
opened: 2026-07-28

gated_on: >
  nothing — 23 deferred items against 7 open, and the 2026.07.28 guardrail
  audit found a trigger that had fired unbuilt because nobody polls triggers

reads:
  - docs/todo/_TEMPLATE.md
  - tools/doc_index.py
  - tests/docs/test_todo_hygiene.py
  - docs/AUTO-GUARDRAILS.md
---

# Deferral should expire by default, not persist by default

23 deferred items, 7 open, 87 completed. The deferred pile is more than three
times the open pile, a deferred item costs nothing to write, and each one is a
claim about the future that ages whether or not anyone rereads it.

The failure mode is not volume. It is that **writing the item feels like
progress**: the item file is where the thinking happens, so a well-argued
deferred item delivers most of the satisfaction of solving the problem and
none of the solution, and then sits there being slowly wrong.

## Three dangers, each with evidence in this tree

**Silent triggers.** A trigger nobody polls makes an item a lottery ticket.
Demonstrated on 2026.07.28: AUTO-GUARDRAILS §2's trigger ("the next item that
touches serialization") fired when schema v3 landed and nothing was written
until a hand audit went looking, at which point it became
`docs/todo/gui-cli-execution-parity.md`. §4's fired the same way for three
budgets. Both had been sitting fired for a day or more with the file reading as
though they had not.

**Maintained items.** Read the `.state.md` lines for
`docs/todo/ledger-measurements.md` and
`docs/todo/block-signal-free-measures.md`: both now carry paragraphs explaining
how the item's own premise changed after it was written. That is an item being
*maintained* — a recurring cost nobody budgeted, paid to keep a claim about the
future accurate rather than to build anything. This is the strongest of the
three and the one the mitigation should target.

**Prose gates.** `gated_on` is a sentence, so no tool can ask whether a trigger
has fired. `after:` edges became machine-readable on 2026.07.28
(`docs/completed-todo/2026.07.28-the-todo-dag-is-prose.md`) and that is the
model, but `gated_on` is genuinely harder: most triggers are not items at all
("a machine nobody owns", "a session that scrubs"). Some are, and those are the
ones worth structuring first.

## What to build

Not a WIP limit and not a count. Three things, smallest first:

1. **`deferred_on:` in the frontmatter**, so age is derivable. Today `opened:`
   is the only date and it does not distinguish a promotion from a deferral.
2. **`.state.md` names deferred items past ~30 days with an unfired trigger**
   as a decision to make: promote, rewrite, or delete. Not a gate — a gate here
   manufactures busywork and teaches people to backdate.
3. **Deletion as the normal outcome.** Completion-by-move already proves git is
   a fine home for item text (`git log --diff-filter=D -- docs/todo/<slug>.md`
   finds it), so a deleted deferred item loses nothing but its maintenance
   cost. The current default is the opposite and nothing argues for it.

## The thing to not get wrong

The half of `gated_on` that *is* an item should become a slug and reuse the
`after:` machinery rather than growing a second edge type. Two graphs over the
same nodes is how the prose version got here.
