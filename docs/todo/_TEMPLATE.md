---
title: One sentence naming the outcome
# Sequenced item: `step` orders it and its first component is the phase.
# An aside that must precede the next planned step is inserted with a decimal
# ("02.3.1" runs between "02.3" and "02.4"); an aside that can wait gets no
# step at all — give it `priority` (high | normal | low | unassessed) and,
# optionally, `phase`, and it lives in the phase's pool instead.
step: "00.1"
status: open          # open | awaiting-review | deferred | done
# A worker moves open -> awaiting-review, or -> deferred when the criterion
# contradicts the tree. Only a review sets done or edits done_when.
# `deferred` requires a real trigger in gated_on.
gated_on: nothing
# Sequenced items only, and required there: the executable completion
# criterion, written when the item is written and never edited by the session
# doing the work. The worker runs it and pastes its output; the reviewer
# re-runs it.
done_when: "uv run pytest tests/... -q"
opened: 2026-08-06
---

# The title again, as a heading

What should be different when this is done, in a few sentences, and anything
the session could not work out from the tree. Not a plan and not a file list —
the item runs against a tree that has moved on.
