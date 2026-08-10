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
