---
title: The third BOUNDED tool is keyed and gated by nothing
priority: high
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_admission.py -k every_bounded_tool_is_covered -q"
opened: 2026-08-07
---

# The third BOUNDED tool is keyed and gated by nothing

`adr/cache-admission-is-bounded-warmup.md` keys a node on a declaration its
author makes about their own tool, and `tests/unit/test_cache_admission.py`
knows it — its docstring says a tool making that claim falsely is "keyed,
served, and wrong with no symptom anywhere", and answers by running the
declaration instead of reading it. Two hand-built graphs do that, over
`block_signal` and `detect`.

Nothing carries it to the third. A tool landing with
`warmup_kind=WarmupKind.BOUNDED` is keyed by `cache_policy` and served by the
executor on the strength of its own say-so, and the file that exists to refuse
exactly that will not notice — it is `test_the_two_epsilon_warmup_tools_are_still_refused`
that names tool ids, and it names them on the side of the rule that recomputes.
The gap is on the side that serves.

What closes it is coverage derived rather than a row added: collect the tool ids
the served-equals-cold cases actually put through the executor, take the
`BOUNDED` set from `discover()`, and fail when the second is not contained in
the first, naming the tool that is keyed with no case. A row per tool in this
file is the shape `adr/a-tool-is-one-file.md` refuses — a shared list every tool
after has to enter — and it would also be a declaration checked by a copy of
itself, which is `adr/declared-means-verified.md`'s subject.

The failure message is the whole value: "declares BOUNDED, no served case" is
what tells the next tool's author that the parity graph is part of admitting
their tool, and a bare count assertion tells them nothing. Which case covers a
tool is a fact the run has — the plan names its nodes — so this reads what
happened rather than what the file says it does.

The epsilon half stays named by hand and this does not touch it. That tuple
asserts a measurement nobody has taken has not been quietly assumed, which is a
claim about three specific tools and not a property of the shelf.
