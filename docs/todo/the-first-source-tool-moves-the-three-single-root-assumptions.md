---
title: The first source tool moves the three places one root is assumed
status: open
gated_on: nothing
priority: normal
phase: "04"
done_when: 'uv run pytest tests/unit/test_source_tool.py -k "two_roots_order_and_execute or swapping_the_picked_file_moves_only_its_own_key or a_pattern_matching_several_files_is_refused" -q'
opened: 2026-08-07
---

# The first source tool moves the three places one root is assumed

[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
settles that a picked file enters as a source tool — a node with no upstream
keying from its own file — and closes by saying "That migration is an item."
It was not one: nothing under `docs/todo/` and no line of `PLAN.md` mentions a
source tool, a picker, or a second root, so the ADR discharged its own
unfinished half onto a referent that does not exist. This is that referent.
The ADR is the decision; what is owed here is the first tool that exercises it.

Three sites assume the single root, and all three are real today rather than
predicted. `dag.linear_order` raises `expected one root, found N` — that is
the tool stack's redraw, so a two-root project cannot be *drawn* before it
fails to run. `cache_key.source_key` is "the ancestor of every root", one
value the whole graph folds in, which is the wrong shape the moment two roots
have different content identities. And the executor binds a node with no
upstream to the reader (`executor.py`, the root-is-the-reader comment), which
is the binding a source tool replaces rather than shares.

The ADR names two more consequences that land with the tool and not before. A
sixth `ParamStereotype` for a path: `ParamStereotype`'s own docstring says the
vocabulary is closed and a sixth member is a deliberate decision forced by a
tool that cannot be expressed in five — ADR-18 is that decision, so the tool is
what spends it, and `ToolSpec` refusing an unknown kind is what would otherwise
stop it. And the resolution policy stays out of the key: a pattern resolving to
nothing is a run that cannot happen, one resolving to several is refused rather
than ordered, and what is hashed is the file each replicate resolved to and
never the rule that found it.

The two VISION scenarios that wait on this are the picker and the folder
([VISION.md](../VISION.md)), and whether VISION also states an A/B of two
backgrounds is
[a separate question for Kendrick](whether-vision-states-the-background-ab.md).
