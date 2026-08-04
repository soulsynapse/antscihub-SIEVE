---
title: A filter id spelled outside its module is an enumeration
status: open
opened: 2026-07-29
priority: high
gated_on: nothing
reads: [tests/bench/test_budget_producers.py, src/sieve/core/filter_registry.py]
---

# A filter id spelled outside its module is an enumeration

REWORK.md R4's literal half. Rule 3 says nothing enumerates filters, and the
discovery test enforces it for imports — but `filter_tab.py` switches on
`"block_signal"` at six sites, `"rescale"` at five, and `chain_model.py` and
`wizard_model.py` carry more. Each literal is a hand-typed enumeration the
discovery contract cannot see.

Re-aim `test_budget_producers.py`'s AST skeleton (top-level string constants,
checked against a reference set, with a shrink-only exception list checked in
both directions): collect every string literal under `src/sieve/`, flag any
equal to a registered `filter_id` in a module other than the filter's own.
Exception set of `(module, filter_id)` pairs seeded from the real sites, with
the grown-and-shrunk checks copied in shape from `WITHOUT_PRODUCER`'s.

Second check, vacuous today, governing from the first table emitter (the
parenthesized-layer idiom): no name declared in any `TableSpec.columns` is
spelled as a literal in two top-level packages. Derive the package list from
the tree; type nothing.

Deliberately narrow. A *generic* two-layer duplicate-literal detector would
seed an exception list the size of the codebase (`"in"`, `"array"`, every
StrEnum value), which is enumeration rot re-encoded in Python — REWORK.md
R4's Gate line records the rejection.
