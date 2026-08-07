---
title: A tool declares what it can emit
step: "05.4"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py tests/unit/test_cli_inspect.py -q"
opened: 2026-08-07
---

# A tool declares what it can emit

VISION's save screen shows *all the possible* outputs the tools could emit,
declared on the specs so the list cannot lie. That is a `ToolSpec` field, and
it arrives now rather than in Phase 1 because a declaration arrives with its
consumer (`adr/declared-means-verified.md`) — the consumer is 05.3's
checkpoint writer and the `inspect` command that prints the list.

The field says what a tool can emit, not what it does emit on a given run:
the difference is the whole point of a save screen that cannot lie. A tool
declaring an emission it never produces fails at registration, in the shape
Phase 1 established for every other forgettable declaration, or the guarantee
is prose.

Every tool on the shelf gains its declaration in this item, which is nine
files of one field each and no other change — a tool that needs more than a
field is a tool whose emissions were not understood, and that is a
stop-and-write.

The criterion is the contract test plus `inspect`'s, because the list being
*printable* is what makes it checkable before a widget exists.
