---
title: The save-back on switching projects is a survivor, and the unread-file default has no caller
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_save_and_run.py -q -k an_edit_survives_switching_projects"
opened: 2026-08-10
---

# The save-back on switching projects is a survivor, and the unread-file default has no caller

`only-run-writes-the-document` wired `Session.save_if_edited` at two call
sites, not one: `MainWindow.closeEvent`, which the criterion covers on both
legs, and the head of `MainWindow.open_project`, which writes the project being
left. The second is a survivor — deleting it leaves the whole suite green
(review of `833703e`):

    if self._session is not None:
        self._session.save_if_edited()          ==> (deleted)   (gui/app.py, open_project)

    oracle: uv run pytest tests/ -q  —  1236 passed, SURVIVED

The mutant is the pre-`833703e` behaviour on the gesture the item's own body
never mentioned and the run added: tune six parameters, press Left, open the
neighbouring card, and the first project is the one that was opened. It is the
harder half to notice by hand, because unlike a close there is still a window
on screen afterwards saying nothing went wrong.

One case: a window over two library projects, opened on the first, an edit the
document carries (`remove_step` is what the close case uses and it is the least
deniable), `open_project` onto the second, and the first file asserted to hold
the edit. `chain_file` in `tests/gui/test_save_and_run.py` is the fixture minus
its second project; the `_MARKER` trick it already carries is what says the
*second* project was not rewritten in passing.

The second half, which the criterion above does not reach. `Session.__init__`
takes `on_disk: bool = False`, and the `False` leg — `self._on_disk = None`, so
a fresh session is `edited` and owes its file a write — has no production
caller: `Session.open` passes `on_disk=True` and it is the only construction
under `src/`. The item's build note justifies the default by naming
`project_select.mint` as the thing that "composes a project in memory and hands
it a path", and `mint` does neither for a `Session` — it calls `Project().save`
itself and returns the path, which the window then reopens with `Session.open`.
So `test_a_session_over_a_file_it_has_not_read_is_edited` stands over a branch
nothing reaches, which is the guard-with-a-test-and-no-caller shape. Either the
default gets the caller its own argument describes — `mint` handing the window
a composed session rather than a path to reread — or it goes, and the
constructor stops offering a state the tree cannot be in.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui/test_save_and_run.py -q -k an_edit_survives_switching_projects
    6 deselected in 0.13s
    exit: 5
