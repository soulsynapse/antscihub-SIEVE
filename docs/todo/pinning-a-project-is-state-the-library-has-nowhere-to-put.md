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
