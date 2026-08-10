---
title: Only Run writes the document, so closing the window discards every edit
phase: 9
priority: high
status: done
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

## Built 2026-08-09 (worker)

The session holds a third whole value beside the two stacks — the one the file
is known to hold, set by `open` and by `save` — and `edited` is the comparison
against it rather than a flag a commit sets, so an undo back onto the opened
value is clean again. `save_if_edited` is that guard around the existing write,
and `MainWindow.closeEvent` is the wire. `open_project` calls it too, on the
project being left: opening a second project is the other way a session ends,
and it is the same one-line call.

A `Session` built over a file it has never read is `edited` from the start,
which is the constructor's `on_disk=False` default. The alternative — taking the
caller's word that the file agrees — would decline the only write that could
make it true, and the one thing in the tree that composes a project in memory
and hands it a path is `project_select.mint`.

Both criterion cases proved red independently: dropping the `closeEvent` wire
fails `an_edit_survives_a_close`, and dropping `save_if_edited`'s guard fails
`a_clean_document_writes_nothing` — which asserts the file's bytes rather than
its value, against a hand-written comment line appended to the fixture, so a
rewrite that round-trips to the same document is still caught. The undo leg of
`edited` and the unread-file default are `tests/unit/test_session.py`'s, where
the comparison lives.

    $ uv run pytest tests/gui/test_save_and_run.py -q -k 'an_edit_survives_a_close or a_clean_document_writes_nothing'
    2 passed, 4 deselected in 1.76s

Full suite 1215 passed, `ruff format --check` and `ruff check` clean.

## Reviewed 2026-08-10

Criterion re-run independently: `2 passed, 4 deselected`, exit 0. Both cases
proved red here rather than on the transcript's word — the `closeEvent` wire
deleted fails `an_edit_survives_a_close`, and `save_if_edited`'s guard forced
through fails `a_clean_document_writes_nothing` on the file's bytes. Full suite
1236 passed. `done_when` untouched and `status` moved only to
`awaiting-review`.

Set `done` with residue elsewhere, not covered here: the `open_project` half of
the save-back is a survivor against the whole suite, and `Session.__init__`'s
`on_disk=False` leg has no production caller — both homed in
[the-other-way-a-session-ends-writes-nothing-a-case-reads.md](the-other-way-a-session-ends-writes-nothing-a-case-reads.md),
which is red at minting. The shape is recorded in
`docs/findings/loop/2026.08.09-a-loud-deferral-covers-for-a-silent-one-in-the-same-sentence.md`.
