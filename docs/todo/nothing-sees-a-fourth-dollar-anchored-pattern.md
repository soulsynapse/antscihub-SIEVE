---
title: Nothing sees a fourth `$`-anchored pattern, and the record says nothing could
status: open
priority: normal
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pattern_anchors.py -q"
opened: 2026-08-08
---

# Nothing sees a fourth `$`-anchored pattern, and the record says nothing could

Three whole-string id patterns have been corrected from `$` to `\Z` in three
separate commits — `NODE_ID_PATTERN` (`e0da6ca`, `0297f49`), then
`TOOL_ID_PATTERN` and `SEMVER_PATTERN` together (`38271aa`). Each was found by a
person noticing, not by a check. A fourth would be found the same way, and
silently: `$` is `(?=\n?\Z)`, so the field admits a trailing newline and the
document loads clean.

`38271aa`'s item asked whether the honest fix was broader than the two constants
it named. It settled that against a class-level guard, and the reason it recorded
is false: "a check that could see it would read the module's source for
`re.compile` and judge the literal, which is a lint rather than a case, and this
tree has no lint that reads Python as text". A compiled pattern carries its own
source at runtime. Walking `sieve` with `pkgutil.walk_packages` and collecting
every `re.Pattern` bound in every module's namespace enumerates the class with no
hand-written tuple, and sees a member nobody remembered — measured in
[findings/loop/2026.08.08-a-runtime-check-was-refused-as-a-lint-the-tree-does-not-have.md](../findings/loop/2026.08.08-a-runtime-check-was-refused-as-a-lint-the-tree-does-not-have.md),
which holds the probe and its output: nine bindings over five distinct patterns,
none ending `$`, so the rule has zero exemptions today.

The criterion says land it, and the argument the work has to make is the one the
criterion cannot: a rule over *every* compiled pattern in `sieve` is wider than
the three id fields that motivate it. `_SLUG_STRIP` and `_RAW_FORMAT_LINE` are
neither anchored nor whole-string, so they satisfy the rule by accident rather
than by agreeing with it, and a `$` that is one day deliberate needs an
exemption — which is an allow-list, the shape that let the first one through.
Two ways out to weigh: state the rule over patterns that *are* whole-string
(`^`-anchored, so the accidental members leave the population rather than pass
it), or keep it universal and make the exemption a named constant with the
reason at its definition. Whichever way, the case must fail for a pattern
introduced anywhere in the package, not only in `core` — that is the whole
difference between this and the hand-written tuple the previous run correctly
refused.

The amendment in
[findings/loop/2026.08.08-consolidating-two-guards-onto-one-constant-narrows-the-stricter-one.md](../findings/loop/2026.08.08-consolidating-two-guards-onto-one-constant-narrows-the-stricter-one.md)
is the argument a later reader will find for why no such guard exists; it carries
a dated correction pointing here.
