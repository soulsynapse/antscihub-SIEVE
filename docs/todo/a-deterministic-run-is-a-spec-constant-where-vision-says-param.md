---
title: A deterministic run is a spec constant where VISION says the author selects it
phase: 2
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -q -k 'a_determinism_choice_is_a_param_not_a_constant'"
opened: 2026-08-09
---

# A deterministic run is a spec constant where VISION says the author selects it

VISION's reviewer scenario states it as a choice with a consequence: "where
necessary, the author had selected 'deterministic run', and because that choice
changes outputs it is a param and was saved to the file", citing
[adr/param-not-preference.md](../adr/param-not-preference.md). In the tree it is
`ToolSpec.deterministic`, a `bool = True` on `Channel.EXECUTION` — a constant the
tool author writes once, not something a user selects and nothing that reaches
the saved file. `cache_key` reads it to decide whether a node is keyable at all
and `inspect_cmd` prints it; no param can express it, so the sentence VISION
promises the reviewer has no mechanism under it.

The ADR the sentence cites is the one that decides this, and it decides against
the current shape by its own rule: a choice that changes outputs is a param, and
a param is saved. So either a tool that has a fast non-deterministic path
declares that path as a param field and the spec constant becomes the ceiling
(the tool can refuse to offer the choice, never widen it), or VISION's sentence
is wrong and comes out. The item is which — and the first reading is the one the
ADR argues for, so the second needs a reason.

It is filed in phase 2 rather than 1 because the saved-file half is the schema's:
a param that reaches the file is a `Node.params` entry, and the interesting case
is whether it is a per-replicate deviable one, which is
[whether-a-recorded-input-hash-is-keyed-per-replicate.md](whether-a-recorded-input-hash-is-keyed-per-replicate.md)'s
question over a different field.

No tool on the shelf has a non-deterministic path today, so the criterion is
about the contract's ability to express the choice rather than about any tool
exercising it — the first `-k` name says so, and a spec that cannot express it is
red whatever the shelf holds.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/unit/test_tool_contract.py -q -k 'a_determinism_choice_is_a_param_not_a_constant'
    97 deselected in 0.12s
    exit: 5
