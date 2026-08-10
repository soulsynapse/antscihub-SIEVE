---
title: The + names a region off the count, so dropping a middle one makes two of a name
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k a_region_added_after_a_drop_is_named_something_the_document_has_not_got"
opened: 2026-08-09
---

# The + names a region off the count, so dropping a middle one makes two of a name

`MainWindow.add_region` mints `f"region {len(replicates) + 1}"`, which is the
count and not a name the document has been asked about. Three clicks and one
drop reach a project holding two replicates called the same thing (probe under
the review of `868692f`, a window over `crop -> downsample -> detect`):

    + + +                          ['region 1', 'region 2', 'region 3']
    select region 2, −, +          ['region 1', 'region 3', 'region 3']

`replicate_id` is generated, so the document is valid and nothing refuses the
write — which is what makes this land in a saved file rather than in a dialog.
What breaks is downstream, where the name is the handle: `materialize_cmd`
resolves `--replicate` by name and refuses an ambiguous one outright (it prints
the ids, so the user is not stuck, but the name they read off the fan is not a
thing they can pass), `run_cmd._label` reports two runs under one word, and
`checkpoint_writer` records `replicate_name` into the artifact. And the GUI has
no rename intent at all, so the surface that mints the collision offers no way
to undo it except dropping the region and losing its box.

The fix is a name the document does not already hold — the count is the right
*start* and the collision is what has to be resolved, whichever way. Worth
deciding rather than patching blind: whether the ordinals are stable identities
the user reads off the fan (in which case a drop leaves a gap and the next + is
"region 4"), or whether they are positions (in which case the fan renumbers on
every drop and the item's own argument against insertion — "the user's region 3
would become somebody else's" — applies to removal too). The referent settles
neither; it refuses to drop the last crop and does not otherwise renumber.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k a_region_added_after_a_drop_is_named_something_the_document_has_not_got
    216 deselected in 0.69s
    exit: 5
