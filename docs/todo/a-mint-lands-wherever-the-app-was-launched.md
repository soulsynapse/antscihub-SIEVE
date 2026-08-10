---
title: A mint lands wherever the app was launched, and the library is that folder
phase: 9
priority: high
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_project_cards.py -k library_root -q"
opened: 2026-08-09
---

# A mint lands wherever the app was launched, and the library is that folder

`main` builds the window with `projects_in(Path.cwd())` and `library=Path.cwd()`,
so the library is whatever directory the process started in and NEW PROJECT
writes `untitled_N.sieve.yaml` there. Launched the way it is launched during
development that is the repository root, which means the one gesture the project
pane exists for drops an untracked file next to `pyproject.toml`, and the shelf
the pane draws is a scan of the source tree.

What lands: a `projects/` folder under the launch directory is the library.
`project_select.py` gains the one function that answers where — given a
directory, it returns the `projects/` inside it, creating the folder if it is
not there — and `main` asks it rather than naming `Path.cwd()` twice. Every
project file sitting directly in the launch directory is moved into the folder
on the way past, which is the "automatically find their way there" half: a
project minted before this item exists must still be on the shelf after it, and
a scan that covered both folders would put the same file on two cards the day
someone opened one of them. A name the folder already holds is left where it is
rather than overwritten — the two are different documents that happen to share
`untitled_1`, and losing one to a relocation nobody asked for is worse than a
stray file. `projects/` joins `.gitignore`, since a mint is a user's document
and not a fixture.

The window is not the subject. `MainWindow` already takes `library` and derives
it from the scan when it is not given (`library_folder`), and both remain true;
what moves is the one caller that had been answering with the process's working
directory. Keeping the resolution a function rather than a line inside `main` is
what lets the criterion drive it at all — `main` opens a `QApplication`.

"For now" is the user's word and it is the right one: this pins the default in
the one place the app decides it, and it is not a ruling that a library is a
folder relative to the launch directory forever. What supersedes it is a project
pane that can be pointed at a folder — at which point this function is where the
remembered choice is read, and the `projects/` default is what it falls back to.

## Folded 2026-08-09 (review of 09.10): it has already happened once

An `untitled_1.sieve.yaml` holding an empty `Project()` was sitting untracked in
the repository root during that review, minted at 18:10 by something launched
there — not by the tests: neither `tests/gui` nor the full suite reproduces it
from a clean tree. The review deleted it. So the `.gitignore` clause above wants
both spellings, `projects/` and a project file directly in the launch directory:
until the relocation lands, the form that actually appears is the second one, and
`git status` showing it is the only thing that catches a mint nobody meant.

## 2026-08-09, again: a second one, and deleting it is not the remedy

An `untitled_1.sieve.yaml` was untracked in the repository root at the start of
the seeding pass below, one day after the section above recorded the first and
deleted it. Twice in two days, from a clean tree, by something launched at the
root. That is the recurrence rate the `.gitignore` clause is up against, and it
is also the argument that a stray mint is not a nuisance to be swept: the second
one appeared while the item describing the first was open, so the remedy has to
be the relocation and not a habit of deleting what `git status` shows.

## 2026-08-09, Kendrick: the relocation landed, the migration did not

Asked for directly and done in his session rather than through the queue.
`project_select.library_root` is the one function this item names — given a
directory it returns the `projects/` inside it, creating it if absent — and
`main` asks it instead of naming `Path.cwd()` twice. `projects/` is tracked by a
`.gitkeep` and its contents are ignored (`projects/*`), so the folder is part of
the tree and what a user mints into it is not.

An intermediate spelling was tried and withdrawn in the same pass, and it is
worth recording because it is the tempting wrong answer: ignoring the root-level
`*.sieve.yaml` too. That hides a stray mint instead of preventing one, and this
item's own reasoning is the argument against it — `git status` showing the file
is the only thing that catches a mint nobody meant, so an ignore there spends
the net and leaves the cause. It came out; only the folder's contents are
ignored.

**Not done, and the criterion never reached it.** Project files sitting directly
in the launch directory are not moved into the folder, so a project minted
before this landed is off the shelf rather than on it — the "automatically find
their way there" half of the paragraph above, including the name-collision rule
that says a clash is left where it is rather than overwritten. The `untitled_1`
from the two recurrences above is still at the root, now invisible to the pane
and visible to `git status`, which is the state this half exists to end.
`library_root` is green and this item is not done; the review decides whether
the remainder stays here or is split.

## Folded 2026-08-09: what the function is going to be asked to read

The supersession this item names for itself — "a project pane that can be pointed
at a folder, at which point this function is where the remembered choice is read"
— is VISION's, stated in the same breath as two other claims about the opening
screen: the user is "back on the last project this user had open", the selector
lists a folder that "is theirs to change", and beside the selection sit "the ones
they have pinned".

The first two land here rather than anywhere else, because both are a remembered
answer read by the same function this item is creating: which folder to list, and
which card the selection starts on. Neither is a scan result — a folder chosen
last session cannot be found by scanning, and `project_select.py` already argues
that the card's foot says *written* rather than *opened* because an mtime cannot
carry a claim about the user's history. So this item's one function acquires a
second job the moment either lands, and knowing that now is worth more than
knowing it after the signature is fixed: it takes a launch directory today, and
what it will want is a place to have written last session's answer down.

The third claim is not folded. Pinning needs the same store and is a different
question — the mockup's project-selector row settles the pane in detail and has
no pin in it, so VISION and the referent disagree and something has to rule —
[pinning-a-project-is-state-the-library-has-nowhere-to-put.md](pinning-a-project-is-state-the-library-has-nowhere-to-put.md)
carries that, and the two are worth deciding together even though only one of
them can be satisfied by this item's criterion.

`done_when` above is untouched and reaches none of this: `library_root` is the
`projects/` default, not a remembered choice. The review that takes this item
decides whether to widen it or leave the remembered half to its own item once the
folder chooser has a surface.
