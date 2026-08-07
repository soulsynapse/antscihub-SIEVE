---
title: Presentation stereotypes are spec data
step: "01.4"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -k stereotype -q"
opened: 2026-08-06
---

# Presentation stereotypes are spec data

Each param field declares a population kind — `scalar-range`, `enum`, `span`,
`region`, `point` — as Qt-free spec data, unread until Phase 7's generator.
Early declaration is the licensed shape in `adr/declared-means-verified.md`:
the vocabulary is closed and an unknown kind is refused at registration by
name, so the check stands in as the consumer until the generator lands.
Kinds grow slowly and deliberately (`adr/gui-knows-kinds-not-tools.md`) — the
five above are the whole vocabulary until a Phase-7 tool forces a sixth.
Test names carry `stereotype` for the `-k` gate.
