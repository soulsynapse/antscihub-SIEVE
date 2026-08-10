---
title: Five files say a complete GUI emits every intent kind, and nothing says which they are
phase: 7
priority: high
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_intents.py -q -k 'the_kinds_are_the_modules_own or a_new_kind_fails_the_list'"
opened: 2026-08-09
---

# Five files say a complete GUI emits every intent kind

VISION's reshuffle scenario rests on a list: "there is a list of required
bindings for the app to be equally operational — the intent kinds the command
layer is keyed by are that list — and any layout that emits them all is a
complete GUI". Four ADRs restate it
([a-position-is-asked-for-in-the-chain.md](../adr/a-position-is-asked-for-in-the-chain.md),
[the-mockup-is-the-gui-end-state.md](../adr/superseded/the-mockup-is-the-gui-end-state.md),
[one-field-is-one-populated-value.md](../adr/one-field-is-one-populated-value.md),
[the-walked-step-owns-the-canvas.md](../adr/the-walked-step-owns-the-canvas.md)),
each as the reason its own ruling does not narrow the surface. Nowhere is the
list. There is no enumeration in `src/`, no assertion over one, and no test that
would notice a kind arriving or leaving.

It has already drifted. `PLAN.md`'s Phase 7 names four — SetParam, SetOutputs,
AddNode, RemoveNode — and `session/intents.py` defines five: 09.10 added
`RetoolNode` and no line of prose anywhere gained a member. So the claim five
files lean on is, today, checked by nothing and already a member short in the
one place a reader would look it up.

What lands is the enumeration in `session/intents.py`, derived from the module
rather than typed beside it — the kinds are the module's own dataclasses, and a
list restated by hand is the defect above wearing a shorter name. The second
`-k` term is the half that makes it worth having: a sixth kind added without
joining the list has to go red, which is what turns VISION's completeness claim
from prose into something a run can fail. This is the same shape as
[the-admission-argument-is-retold-in-four-modules.md](the-admission-argument-is-retold-in-four-modules.md)
— a claim restated everywhere and held nowhere — and the two are worth reading
together, though the remedies differ: that one deletes restatements, this one
gives the restatements a referent to cite.

Taken now rather than at its number because its value decays. Written while
Phase 9 and 10 are still adding surfaces, the list constrains what they emit;
written after, it describes what they emitted.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/unit/test_intents.py -q -k 'the_kinds_are_the_modules_own or a_new_kind_fails_the_list'
    7 deselected in 0.13s
    exit: 5

## 2026-08-10 review: green, and one conjunct of the rule no fixture reaches

`done_when` re-run against `1768531`: `2 passed, 10 deselected`, exit 0, and the
item file's own diff in `60f99fa` carries `status` alone. The clauses hold --
`INTENT_KINDS` is derived from the module's namespace rather than typed beside
it, and `KIND_NAMES` in `test_intents.py` is the hand-typed list an eighth kind
reddens.

What the criterion does not reach is the exclusion half of the membership rule:
drop `issubclass(member, Intent)` from `intent_kinds` and both cases stay green
([findings/loop/2026.08.07-a-workers-hand-enumerated-mutation-sweep-held-under-an-independent-one.md](../findings/loop/2026.08.07-a-workers-hand-enumerated-mutation-sweep-held-under-an-independent-one.md)
carries the sweep). The obligation is folded into
[choosing-among-sources-is-a-move-no-intent-kind-makes.md](choosing-among-sources-is-a-move-no-intent-kind-makes.md),
which adds the eighth kind and is the cheap moment to put a namespace member in
front of the rule that it has to refuse.
