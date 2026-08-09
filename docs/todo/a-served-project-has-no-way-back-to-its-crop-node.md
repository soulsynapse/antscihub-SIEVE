---
title: A served project has no way back to its crop node
status: done
gated_on: nothing
priority: high
phase: "05"
done_when: 'uv run pytest tests/integration -k "a_served_project_can_be_cut_again or a_replicate_added_to_a_served_project_runs" -q'
opened: 2026-08-09
---

# A served project has no way back to its crop node

Measured in
[findings/2026.08.09-a-served-project-cannot-grow-a-replicate-or-be-cut-again.md](../findings/2026.08.09-a-served-project-cannot-grow-a-replicate-or-be-cut-again.md);
this is the work, not a second copy of the argument. `b63f43f` made the serving
substitution a document edit and the offer whole-document, both of which are
right — one pipeline serves every replicate, so a crop node cannot be a
`footage` node for one arena and a crop for another. What did not land beside it
is the reverse.

Two states a user reaches immediately after the last arena is cut, since that
cut is also the invocation that takes the edit. `sieve materialize` on a served
project refuses — there is no root crop node left, so there is no region to cut
— which is honest but permanent: a project cannot be re-cut after the parent
changes, and a thirteenth arena cannot be added to twelve. And a replicate added
to a served project carries the `region` override a front end writes for a crop
node, `Project`'s validator accepts it because the node id still exists, the
document saves, and every plan built from it afterwards fails with pydantic's
`extra_forbidden` on a field the user never typed.

`pipeline/crop_serving.py`'s header already states the property this item owes:
"the records stay in the document, so re-wiring the crop node back costs nothing
but the edit". The records do survive — that is what makes the reversal possible
at all — but nothing performs it, so the cost today is a hand edit of YAML.

What is open and is this item's to settle: whether the reverse is an
`unserving_edit` beside `serving_edit` (the crop node restored from the record
the document still holds, region and all) or something `materialize_cmd` does
implicitly when asked to cut a served project; and whether `Project`'s validator
should refuse an override naming a parameter the node's tool does not have,
which would move the second failure from run time to save time for every such
edit rather than only this one. The second is the wider fix and touches
documents this item is not about, so it is a call to make deliberately rather
than a line to add.

`done_when` names two cases and neither exists, so it is red because nothing
matches. It does not prejudge the first fork — an implicit un-wire in
`materialize` and an explicit `unserving_edit` both satisfy
`a_served_project_can_be_cut_again`. It does rule on the second, and
deliberately: the second case asserts that the added replicate *runs*, because a
save-time refusal is a better error and not a fix. Whoever takes the validator
fork owes the working path beside it.
