---
title: One sentence naming the outcome
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
# Name the claim, not the file. A criterion pointing at a whole test module is
# met by any weak case added to it, which is how a green command certifies work
# that was not done — so name the test, or the count the module goes to, or the
# mutation that has to die. Whether it is red today is a smell and not a rule:
# a criterion can be red only because the file it names does not exist yet, and
# for a refactor "the suite still passes" is the entire claim.
done_when: "uv run pytest tests/... -q"
opened: 2026-08-06
---

# The title again, as a heading

What should be different when this is done, in a few sentences, and anything
the session could not work out from the tree. Not a plan and not a file list —
the item runs against a tree that has moved on.
