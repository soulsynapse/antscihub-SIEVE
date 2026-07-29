---
title: Every declarable shape runs or is refused by name
status: open
opened: 2026-07-29
priority: high
gated_on: nothing
reads: [src/sieve/pipeline/executor.py, src/sieve/core/filter_base.py]
---

# Every declarable shape runs or is refused by name

REWORK.md R2's gate. A spec field the contract can express but the executor
neither runs nor refuses is worse than an absent field — `emits=TableSpec(...)`
is that case today: `_bind` checks `mode` and `rate_changing` by name and never
looks at `emits`, so a table emitter fails at the author's desk (no kernel
protocol returns anything but `Frame`) with no message naming the field.

Three parts, one sitting:

1. Extract the refusal logic from `_bind` into a pure
   `unrunnable_reason(spec) -> str | None` — the one enumeration of what the
   contract can declare and the executor cannot do. `_bind` calls it and
   raises `UnrunnableNodeError`.
2. Close the `emits` gap in the same commit — a named refusal is a few lines,
   which is strictly better than declaring the gap in an exception set.
3. `tests/unit/` gains a walk over the declarable shape space *derived from
   the enums* (`itertools.product` over `Mode`, `rate_changing`, stream
   kinds): every shape either binds-and-runs with a minimal kernel or is
   refused by a message containing the declaration's own field name. A new
   enum member then fails the suite until someone says what happens to it —
   the property that made `MergingKernel` additive and that `emits` never had.

No exception set. The refusals shrink later as `a-kernel-that-sees-a-span`
and `a-kernel-that-changes-the-rate` land execution for the refused shapes.
