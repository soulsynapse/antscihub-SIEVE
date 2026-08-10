---
title: Pinning a project is per-user state a scanned folder has nowhere to put
phase: 9
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_project_cards.py -q -k 'a_pinned_project_leads_the_stack or pinning_survives_a_relaunch'"
opened: 2026-08-09
---

# Pinning a project is per-user state a scanned folder has nowhere to put

VISION's opening screen has three claims about the project selector, and two of
them are folds into
[a-mint-lands-wherever-the-app-was-launched.md](a-mint-lands-wherever-the-app-was-launched.md),
which already names itself as where a remembered choice would be read. This is
the third and it is a ruling rather than a fold: the user is "back on the last
project this user had open… alongside the ones they have pinned".

A pin is not derivable from the folder. Everything the pane shows today comes off
the filesystem — the projects are what a scan found, and the card's foot says when
the file was last written, deliberately not when it was opened, because
`project_select.py` argues that saying "opened" off an mtime would be a claim
about the user's history that nothing in the tree can make. A pin is exactly such
a claim, and there is nowhere for it: a scanned directory has no slot for "this
user cares about this one", so pinning is the first thing in the GUI that needs
per-user state beside the projects rather than inside them.

`MOCKUP-MAP.md`'s project-selector row is the reason this is an item and not an
assumption. That row is post-mockup and settles the pane in detail — NEW PROJECT,
OPEN LOCATION, the `→`/`✕` in the head, last-opened at the foot — and has no pin
in it. So the referent and VISION disagree, and which one is right is the
decision here: either pinning arrives with the store it needs, or VISION's
sentence is superseded by the mockup and comes out. The store, if it lands, is
the same one the remembered library folder wants, which is why the two are worth
deciding together even though only one of them is minted here.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui/test_project_cards.py -q -k 'a_pinned_project_leads_the_stack or pinning_survives_a_relaunch'
    10 deselected in 0.13s
    exit: 5

## 2026-08-09: the premise is answered, and the store is now this item's whole of it

[adr/a-project-lives-where-the-user-put-it.md](../adr/a-project-lives-where-the-user-put-it.md)
rules on the disagreement above rather than leaving it: the library is the list
of locations the app has been shown, held as per-user state, and the ADR cites
this item's own argument as part of why — a scan has nowhere to put a pin, a list
has somewhere for both. So VISION's sentence is not superseded by the mockup; the
mockup's row is a pane drawn over a scan, and the scan is what goes. The ✕ in
that row is the ADR's own evidence, since taking a project out of the library
with the folder untouched is not something a scan can do.

What that leaves here is the store, and the ADR names this item as where it is
decided: "v3 holds no per-user state at all today, and the first thing that needs
it decides its home; the pinning item above is the other claimant and should land
with it rather than beside it." Landing *with* it is the constraint — a pin file
minted beside a separately-invented library file is two homes for one kind of
state.

Folded from [a-mint-lands-wherever-the-app-was-launched.md](a-mint-lands-wherever-the-app-was-launched.md),
which repointed under the same ADR and can no longer carry them: the remembered
library folder, and which card the selection starts on. Both are the same shape as
a pin — an answer the user gave that no scan can rediscover, and specifically not
an mtime, which is why `project_select.py` makes the card's foot say *written*
rather than *opened*. Three claimants, one store, and this item is where it is
chosen.

`done_when` above is untouched and does not reach the folds: it names the pin
alone, and a run that satisfies it will have had to decide the store anyway. The
review that takes this item decides whether to widen it to the remembered folder
and the remembered selection, or to leave those to their own items once the store
exists.

## 2026-08-10: the scan is the other half of the store, and three things collide with it

Asked for as "the todos to get pinning working", and the answer is that they are
this item — what follows is what a run implementing it walks into, gathered here
rather than minted beside it, because ADR 35 says the store and its first
claimant land together and a second file is how they land apart.

**Nothing in v3 reads or writes per-user state at all.** `QSettings`,
`QStandardPaths`, `platformdirs` and an `AppData`/`XDG` path appear nowhere in
`src` or `tests`, so the ADR's "v3 holds no per-user state today" is still
literally true and the store is a module that does not exist rather than a field
added to one that does. What it has to answer beyond where the file sits: what a
launch does when the file is absent (a first launch, and an empty library is a
reachable state the pane already draws), and what it does when the file is there
and will not parse — `project_select._holds` already rules that one unreadable
document must not take the whole shelf down, and a store that raises on a bad
line takes the window down instead.

**The scan is what the list replaces, and no criterion covers its removal.**
`library_root`, `projects_in` and `library_folder` are the three functions, and
`app.py`'s `main` is the caller that names the first two together; `MainWindow`
derives `_library` from the paths it was handed and re-scans inside
`new_project`. That last one carries the argument that dies first: it re-scans
rather than appending "so the shelf stays the folder's own answer in the
folder's own order", and under a list there is no folder to answer, while under
a pin the order is not sorted at all.
[a-mint-lands-wherever-the-app-was-launched.md](a-mint-lands-wherever-the-app-was-launched.md)
disclaims the list in prose and this item's `done_when` names only the pin, so
today the scan's removal is argued in two places and asserted in neither.

**Pinning reorders a stack whose currency is the index.** `ProjectSelect` emits
`selected`/`opened`/`revealed` as `int`, `_project_card` binds its own index into
three closures, and `MainWindow` indexes `self._projects` with what comes back —
one number, which is the pane's whole answer to which project was pressed.
"Pinned leads the stack" makes that number a position in an order the store
decides, so the store keys by path and the index is derived after ordering, or a
pin quietly opens the neighbour. The remembered selection folded in above is the
same shape read at the other end: a path between launches, an index within one.

**A pinned project whose file is gone is a row a scan could never produce.** The
list can hold a path that no longer resolves, and pinning is what makes it
likely, since a user pins the one they mean to come back to. `_holds` has a word
for a document that will not parse and absent is a different word — and the ✕
in [the-project-card-acts-in-its-head-and-reads-at-its-foot.md](the-project-card-acts-in-its-head-and-reads-at-its-foot.md)
is the gesture that clears such a row, unblocked by ADR 35 and gated on this
store.

`done_when` is untouched again and now reaches less of the item than before: it
names the pin, and the store, the list and the ordering are what a run must build
under it. The review that takes this widens it to the list — a criterion that
green-lights a pin sitting on top of a surviving scan would certify the half that
did not land.

## 2026-08-10: two of the three functions are gone, and half the scan with them

`dc4ae8c` deleted `library_root` under
[a-mint-lands-wherever-the-app-was-launched.md](a-mint-lands-wherever-the-app-was-launched.md),
so the paragraph above naming three functions and a `main` that calls the first
two together is stale in both halves. `main` now builds `MainWindow(())` and
scans nothing at all: the launch-time scan this item was going to remove has
already gone, and what is left of the scan is one call inside `new_project`,
which sets `_library` to the folder the mint's own ask returned and re-scans it.

That narrows this item rather than satisfying it. The re-scan is still the
argument that dies first — under a remembered list there is no one folder to
answer — and it now has a second reason to go, because the folder being listed
is whatever the last mint chose, which is a list of one kept by accident.
`projects_in` and `library_folder` are the two functions the store's landing has
to account for, not three.

`done_when` here is untouched and still names only the pin. It reached less than
the item before this section and reaches less again: the list, the ordering and
now the mint-sets-the-shelf behaviour above are what a run must replace under
it. The review that takes this widens it.
