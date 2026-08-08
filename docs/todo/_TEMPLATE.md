---
title: One sentence naming the outcome
# An *unquoted* value may not open with a backtick or a quote: YAML reserves
# both at the head of a plain scalar, so the file stops being YAML and the
# error names a character rather than this field. Quote the whole scalar or
# lead with a word. ``gated_on: `ruff` being pinned`` is not valid YAML; the
# scanner stops on the backtick. The same value quoted whole,
# ``gated_on: "`ruff` being pinned"``, parses — and so does
# `done_when: "uv run pytest tests/... -q"` below, because its quote closes.
# `title` and `gated_on` are the two here that carry prose about code.
# Sequenced item: `step` orders it and its first component is the phase.
# An aside that must precede the next planned step is inserted with a decimal
# ("02.3.1" runs between "02.3" and "02.4"); an aside that can wait gets no
# step at all — give it `priority` (high | normal | low | unassessed) and,
# optionally, `phase`, and it lives in the phase's pool instead.
# The phase is the decision that matters and `priority` only breaks ties
# inside one: an earlier phase outranks a later phase's steps and its `high`
# alike, so a `high` filed a phase too late runs after everything.
# A phase whose steps all read `done` is not shut, and reopening one is the
# design rather than an exception: the number is the ordering, not a record of
# what is finished. So the phase is the one the work belongs to, which is
# behind the current phase as often as ahead of it — an item is filed forward
# when a later phase is what makes a regression visible, and filed back when
# it is groundwork the later phases stand on. A step minted into a closed
# phase is taken before the current phase's next; the doc-index tests assert
# that, so it is a property of the selector and not a promise made here.
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
# Name the claim, not the file, and prove it red. A criterion pointing at a
# whole test module passes today and is met by any weak case added to it, which
# is how a green command certifies work that was not done — so name the test
# the work will add, with `-k` or a node id, even though it does not exist yet.
# Red because nothing matches is red for the right reason. Run it when you
# write it and paste the output; `sieve-v3-specify` holds the same rule for the
# criteria written later, and this is the same sentence at minting time.
done_when: "uv run pytest tests/... -q"
opened: 2026-08-06
---

# The title again, as a heading

What should be different when this is done, in a few sentences, and anything
the session could not work out from the tree. Not a plan and not a file list —
the item runs against a tree that has moved on.
