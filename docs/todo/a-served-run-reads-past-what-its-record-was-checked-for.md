---
title: A served run reads past what its record was checked for
step: "08.1"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/integration/test_crop_serving.py -q -k lead_in && uv run pytest tests/integration/test_crop_serving.py -q -k lookahead && uv run pytest tests/integration/test_crop_serving.py -q"
opened: 2026-08-07
---

# A served run reads past what its record was checked for

`resolve` is handed `plan.span` as `want` and declines a record that does not
cover it. The run then reads `plan.decode_range` — the span widened by
`lead_in` at the near end and `lookahead` at the far one — so every frame the
window adds was certified by nobody. Both ends raise, measured in
`findings/2026.08.07-a-served-run-is-resolved-against-its-span-and-decoded-over-its-window.md`:
`OffsetFrameSource` refuses the near end in source numbering, `VideoReader`
refuses the far end in the artifact's own, and the second message names a
frame index the user's project never mentions.

`want` becomes the decode range. `lead_in` and `lookahead` fold over `dag` and
`params` alone and `source` enters `ExecutionPlan.build` only to key with, so a
caller builds a plan to learn `decode_range`, resolves against that, and
rebuilds on whichever identity comes back — two passes over an object that
opens no container. The elision 05.10 adds does not perturb the arithmetic,
because the only node a served run elides is `crop` and it declares no window.

**This replaces the item that stood here, and reverses it.** That one read the
near end as an unfixable shortfall like a span near frame 0, and would have
clamped `decode_start` at the record's start and reported the difference
through `lead_in_shortfall`. Source frame 9 is in the parent. Clamping would
answer with a truncated warm-up where the same project unserved answers warm,
which breaks the claim the whole feature rests on and that
`test_crop_serving.py` asserts frame for frame — a written crop is a faster
route to pixels the graph would have computed anyway, not a different answer.
Declining is the only reading available: the missing frames can only come from
the parent, and artifact and parent pixels in one run under one root key is the
failure `resolve_source.py` spends a paragraph refusing.

So `plan.SOURCE_FRAME_ZERO` stays zero and its comment — which promises Phase 5
makes a written crop's own start the floor — is now wrong and goes. The same
sentence is in `plan.py`'s module docstring and in `preview.py`'s.

The two v2 rows `the-plan-is-rederived.md` deferred here come with it and are
answered the other way: `lead_in_before_the_artifact_begins_is_a_shortfall_not_a_request`
and `a_span_beginning_before_the_artifact_clamps_rather_than_raising` both
describe a floor this no longer has. They were rows about a plan that knew it
was reading an artifact; under the child-source model the plan never learns
that, and the decision moved one layer up before either could be built.

**Four cases**, two per end, and the pairing is the point: for each end, a
record that covers the window serves and one that covers only the span falls
back to the parent with its keys unmoved. A single case per end would pass
against a resolver that had simply stopped serving anything. The graph needs a
tool with a window — `block_signal` declares a warmup of 1 and `detect` at a
10–14 Hz band declares 12 either side, which is what the finding's probes used
and why the existing five cases never reached this.

Whether the far end also wants `OffsetFrameSource`'s guard and translated
message is this item's to settle rather than assume: once a record too tight
for the window stops serving, the message may be unreachable, and a guard no
case can reach is what `adr/declared-means-verified.md` refuses.
