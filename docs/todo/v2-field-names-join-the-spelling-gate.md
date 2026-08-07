---
title: The v2 field names join the spelling gate
step: "02.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_id_spelling.py -q"
opened: 2026-08-07
---

# The v2 field names join the spelling gate

Phase 2's gate is two claims and 02.1 only carries one. "A v2 field name
appears nowhere in `src/`" is not something `test_pipeline_model.py` can
check — a re-derived model passes its own round-trip tests while spelling
whatever it likes — so it lands where the other half of ADR-1's rename
already lives: `DEAD_IDENTIFIERS` in `tests/unit/test_tool_id_spelling.py`,
which is a table of `(dead word, the one live spelling that contains it,
the verdict)` and grows a row per buried word.

The rows are v2's saved field names that schema v1 replaced with nodes, read
off v2's `pipeline_model.py` at `main`. Each row cites
`adr/v2-does-not-import.md`, and a name that schema v1 keeps deliberately
because it is the right name gets no row — the gate is about names v3
inherited without deciding to, not about a vocabulary ban.

The exception list stays empty and the assertion that it is empty stays, for
the reason its docstring already gives.
