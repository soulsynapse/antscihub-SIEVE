---
title: Guidance is promoted to the spec, and the expander reads it
step: "07.10"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -q -k guidance_is_spec_data && uv run pytest tests/gui/test_expander.py -q -k the_expander_reads_the_spec"
opened: 2026-08-08
---

# Guidance is promoted to the spec, and the expander reads it

What a tool is for has lived in its module docstring since Phase 3, because
the porting discipline holds guidance until "the expander that shows it
exists" — this is that expander, the wizard reimagined as a down-arrow on the
step (VISION.md). The promotion is a `ToolSpec` field the docstrings feed,
arriving with its consumer like every other declaration
(`adr/declared-means-verified.md`), and the expander renders it per step with
no per-tool code.

The order inside the phase is deliberate: nothing in the tuning loop stands on
guidance, so it lands after the loop closes and before the gate — a capability
of the first cut's *comprehensibility*, not of its machinery.
