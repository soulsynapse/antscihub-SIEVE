---
title: The named-gate scan's `deferred` clause has no case
priority: low
phase: 0
status: open
gated_on: nothing
done_when: "uv run pytest \"tests/docs/test_doc_index.py::test_a_gate_sentence_on_an_item_that_is_not_deferred_flags_nothing\" -q"
opened: 2026-08-09
---

# The named-gate scan's `deferred` clause has no case

`named_gate_done` opens on `i.status == "deferred"`, and that clause is the
whole of what separates the table from "any item whose `gated_on` sentence
happens to hold a done item's filename". Nothing tests it. Widening it to
`i.status != "zzz"` leaves `-k named_gate` green — all four fixtures put the
gate sentence on a deferred item and `gated_on: nothing` on everything else,
so the clause is never asked to exclude anything.

The other three claims do have cases; the review that closed
[the-index-surfaces-a-deferral-whose-named-gate-is-done.md](the-index-surfaces-a-deferral-whose-named-gate-is-done.md)
swept them and all three died — the `status == "done"` lookup, the
`name in gate` substring, and the `render` call site. This one survived, and it
is the one the function's own docstring leads with.

It has no live consequence today: `validate` refuses `deferred_for` on an
undeferred item but says nothing about `gated_on`, so an item that goes `open`
while still carrying its gate sentence is legal, and there is none in the tree
right now. The 2026-08-09 reopening of four subject-deferrals cleared
`gated_on` to `nothing` by hand as it went; nothing makes that mandatory, and
the day one is reopened without that step the table would name it.

The case is one fixture: a gate sentence citing a `done` item, on an item whose
status is `open`, asserting `named_gate_done` returns `[]`.

Worth knowing before writing the mutant: `(i for i in items if i.status ==
"deferred")` is byte-identical to the generator `_render_waiting` builds at the
head of its own body, so no single-line anchor for it is unique and
`mutation_sweep` refuses it. Either anchor across two lines or hoist the shared
list — `_render_waiting` and `named_gate_done` both want the same
`queue_key`-sorted deferrals and each builds it.
