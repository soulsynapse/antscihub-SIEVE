---
title: A mint asks where the project goes, and nothing defaults anywhere
phase: 9
priority: high
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui/test_project_cards.py -q -k 'new_project_asks_where_the_project_goes or a_cancelled_ask_mints_nothing'"
opened: 2026-08-09
---

# A mint asks where the project goes, and nothing defaults anywhere

[adr/a-project-lives-where-the-user-put-it.md](../adr/a-project-lives-where-the-user-put-it.md)
rules on this item by path: a project file's location is the user's, chosen when
it is minted, and no directory is the library. So NEW PROJECT asks — a file
dialog whose answer is the path the empty document is written to — and there is
no location it falls back to when the user gives none. A cancelled ask mints
nothing, which is the whole of "nothing defaults anywhere": a default location is
the only thing that can produce the stray mints recorded twice below, so removing
it rather than relocating it is what ends them.

`library_root` is the default the ADR removes, and `main`'s `Path.cwd()` is where
it is asked. Both come out with the ask, not before it — a pane with no library
and no picker lists nothing. What replaces the scan is the remembered list of
locations the app has been shown, and where that list is stored the ADR
deliberately leaves open; the storage question and the pin that shares it are in
[pinning-a-project-is-state-the-library-has-nowhere-to-put.md](pinning-a-project-is-state-the-library-has-nowhere-to-put.md),
which the ADR names as the claimant that should land with it. This item's
criterion asserts the ask and the absence of a default, and deliberately says
nothing about the list, because a criterion over the list would pin a decision
nobody has made.

## As minted 2026-08-09: the launch directory's folder, superseded

Kept rather than cut: the sections after it are dated records that argue against
it and refer back to it, and the recurrences they hold are ADR 35's evidence.

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

## 2026-08-09: repointed under ADR 35, criterion replaced

ADR 35 settled the day this item's last section was written and overrules it by
path. The head of the file is the item under that ruling; everything from "As
minted" down is the record it replaces, left in place because two of its sections
are the evidence the ADR cites — two stray `untitled_1.sieve.yaml` files from a
clean tree in two days — and a successor file would lose them.

`done_when` was replaced rather than widened, on Kendrick's instruction and not by
a worker's judgement. The old criterion (`-k library_root`) is green on the
unchanged tree against two tests that already exist, and it pins the very default
the ADR removes: widening it would have made this item assert the thing it now
exists to delete. The new one names the ask and the cancelled ask, red at
repointing because nothing matches:

    $ uv run pytest tests/gui/test_project_cards.py -q -k 'new_project_asks_where_the_project_goes or a_cancelled_ask_mints_nothing'
    12 deselected in 0.13s
    exit: 5

The remembered half folded above — which folder to list, which card the selection
starts on — goes with the storage question to the pinning item, which ADR 35 names
as the other claimant and which now carries a dated section for it. It is not
this item's criterion for the reason the ADR gives: the list's home is undecided.

Two things for whoever implements this, found while repointing and left here
rather than fixed, since they are the implementation's to change:

`project_select.mint`'s docstring argues against the decision. "A modal at mint
time would be the one form in the surface that blocks the walk" is the cost ADR 35
takes deliberately, calling it a revision of the surface rather than a cleanup
([a-position-is-asked-for-in-the-chain](../adr/a-position-is-asked-for-in-the-chain.md)).
The sentence is still true about the *name* — the ask is for a location, and the
name comes from it — but as written it reads as an argument against a settled
decision, and the ask lands in that function's caller.

The same docstring cites `adr/a-document-may-name-no-footage.md`, which `b3aff03`
moved to `docs/adr/superseded/`. That commit's citation sweep missed it because
the path is hyphen-wrapped across two lines. The argument still holds — ADR 34
dissolves that subject rather than reversing it — so it is the citation that is
stale and not the reason it gives.

## 2026-08-10: the ask is for a folder, and two readings of this item disagreed

`ask_where` asks for a directory (`QFileDialog.getExistingDirectory`) and `mint`
is untouched, so the name is still the first `untitled_N` the folder does not
hold. The head of this item says "the path the empty document is written to",
which reads as a save dialog and would have taken the name off the user; the
section above says the mint docstring's no-name argument "is still true about
the *name* — the ask is for a location, and the name comes from it", which is a
folder. The second was written by the session that repointed this item under ADR
35 and is the more specific of the two, and it is also what the ADR's own
arithmetic needs — a source path is relative to the document's *directory* — so
that is the fork taken. A save dialog remains reachable without touching
anything but `ask_where`.

What the answer does to the shelf is the part no criterion here reaches. The
mint's folder becomes the folder `MainWindow` lists and titles the library card
with, re-scanned as before, because the alternatives were to append one path to
a shelf that is otherwise one folder's sorted scan — the invariant
`new_project`'s own docstring argues for — or to invent the list ADR 35 leaves
undecided. It is the smallest thing that keeps the one folder true, and it is
what
[pinning-a-project-is-state-the-library-has-nowhere-to-put.md](pinning-a-project-is-state-the-library-has-nowhere-to-put.md)
replaces when the store lands.

Gone with the default: `library_root`, `LIBRARY_FOLDER`, their two tests, the
tracked `projects/.gitkeep` and the `.gitignore` stanza that ignored what a mint
wrote into it. `main` builds `MainWindow(())` — no scan, no folder — and the NEW
PROJECT button is drawn whether or not a folder is being listed, or the empty
shelf that launch now opens on would have no way out.
