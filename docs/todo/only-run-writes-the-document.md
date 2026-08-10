---
title: Only Run writes the document, so closing the window discards every edit
phase: 9
priority: high
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_save_and_run.py -q -k 'an_edit_survives_a_close or a_clean_document_writes_nothing'"
opened: 2026-08-09
---

# Only Run writes the document

`Session.save()` has exactly one caller in the whole tree: `SaveScreen._run`,
which saves the document and then hands the file to `sieve run`. `project_select`
writes a `Project()` at mint and never again. So every mutation the command layer
issues — every `SetParam`, every `AddNode`, the `RemoveNode` 09.4 added and the
`RetoolNode` 09.10 added — lives in memory until the user presses Run, and is
gone if they do anything else. Tune six params, close the window, and the project
on disk is the one that was opened.

Nothing marks the gap either. There is no dirty state in `gui/` or `session/`, no
save action on any surface, and the mockup has none to port — the referent settles
Run on the output card's form and says nothing about saving, because in the mockup
there is no document to lose. That is a mock limitation reading as a decision,
which is the class `MOCKUP-MAP.md`'s last bullet already warns about.

What lands is the write, not a policy debate about when. The session knows when
its present value last differed from the one on disk — that is what two stacks of
whole values makes cheap, and it is the same comparison an undo already does — so
a save on close, or on a settled edit, is a call into `Session` and a wire in
`app`. The second `-k` term is the guard against the obvious overcorrection: a
document nobody edited must not rewrite its own file, because `Project.save`
already argues (`pipeline_model.py`) that rewriting bytes on every save is what
makes version control useless on these files.

Not the history dialog, which
[the-first-gui-cut-names-its-surfaces.md](the-first-gui-cut-names-its-surfaces.md)
ruled out on a stated reason and which this does not reopen: the safety net is
not the dialog, and a snapshot ring is a second decision that can be argued after
the file stops being lost outright.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui/test_save_and_run.py -q -k 'an_edit_survives_a_close or a_clean_document_writes_nothing'
    4 deselected in 0.13s
    exit: 5
