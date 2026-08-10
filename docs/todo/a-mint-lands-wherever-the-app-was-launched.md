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
