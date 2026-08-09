---
title: A dropped player takes the process down and its net is a comment
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'dropped_player or no_orphaned_pane'"
opened: 2026-08-09
---

# A dropped player takes the process down and its net is a comment

[findings/2026.08.09-the-players-destroyed-net-does-not-catch-a-window-nobody-closed.md](../findings/2026.08.09-the-players-destroyed-net-does-not-catch-a-window-nobody-closed.md)
measured it and left it owned by nobody, which is why this exists: a finding is
not in `--next`'s queue and nothing goes red for one that sits open.

`VideoPlayer.__init__` connects `destroyed` to a closure holding the `QThread`,
with a comment claiming the slot runs "while the thread object is still valid".
It does not. By the time it fires the wrapper is gone, `_stop` raises
`libshiboken: Internal C++ object (PySide6.QtCore.QThread) already deleted`,
Qt swallows it to stderr, and the running thread the net exists to stop is
still running — so a `MainWindow` that is dropped rather than closed aborts the
interpreter with `0xC0000409` after every test in the file has passed. The
finding's second probe is the falsification: if the net worked, hand-closing
the window could not change the exit code, and it changes it from an abort to
zero.

What keeps the suite green today is that every window but `test_skeleton.py`'s
is closed by hand in a fixture, which is a discipline with no enforcement — the
next GUI test that forgets is a whole-directory abort attributed to whatever
ran last. `app.closeEvent` takes the orderly `shutdown()` path and every caller
in `src/` goes through it, so the net's only clients are tests and a future
front end.

The decision this item carries, and the reason it is not a one-line fix: either
the connection goes and the requirement is stated where a caller reads it, or
the thread is reached through a handle that survives finalisation. The finding
declines to pick because the traceback count does not scale with the number of
players — four closed windows produce one, one unclosed window produces none —
which says the object graph at exit is not understood well enough yet. Settle
that first; whichever lands, the false sentence in the comment goes with it.

The criterion wants a case that drops a player without closing its window and
survives — the shape the finding's first probe used, run as a test rather than
as a probe.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k dropped_player
    132 deselected in 0.90s
    exit: 5

## Folded 2026-08-09 at 09.4: the panes a rebuild discards are top-level windows

The sentence above about the object graph at exit has a second, measured
symptom, and it is not the thread's:
[findings/2026.08.09-an-orphaned-pane-takes-activation-from-the-window-offscreen.md](../findings/2026.08.09-an-orphaned-pane-takes-activation-from-the-window-offscreen.md).
`control.py` replaces a pane by reparenting the old one to nothing and deferring
its deletion, and a widget whose parent is `None` is a *top-level widget* — one
open project leaves a screenful of them alive at once, counted in the finding.
Offscreen Qt then hands
`activeWindow()` to one of those rather than to the `MainWindow` that was just
shown and activated, which silently retires every `Qt.WindowShortcut` in the
window for the next case that runs.

It belongs here because the remedy is the same decision this item is already
holding open: whether a discarded child is reached through something that
survives, or is never orphaned in the first place. Reparenting a replaced pane
to the window rather than to `None` hides it instead of promoting it, and would
close both the stray-activation symptom and one class of what is alive at exit
— but which handle a torn-down child should be reachable through is exactly what
the finding behind this item says is not understood yet, so it is one answer and
not two.

`done_when` (`-k dropped_player`) is not widened here and does not reach this: a
case asserting that a rebuild leaves no new top-level widget is the part of this
paragraph a criterion can hold.

## Folded 2026-08-09 at 09.5: the suite is not green today, it is green sometimes

"What keeps the suite green today is that every window but `test_skeleton.py`'s
is closed by hand" is the sentence this item opens on, and it is measured false
in the amendment dated 09.5 on the finding above. Five consecutive
`uv run pytest tests/gui -q` on the pristine tree, nothing edited between them,
abort twice with the same `0xC0000409` after every test has passed. The
discipline did not remove the abort; it made it a per-run coin flip, which is
why it reads as green — nobody runs the directory five times.

What that changes about this item is its urgency and one of its constraints, not
its subject. The urgency: a random abort is a CI red attributed to whatever
commit was pushed, and no bisect finds it. The constraint: a case that "drops a
player without closing its window and survives" cannot be judged by one run of
itself, because a passing run is what the current tree already produces three
times in five — whatever lands has to be checked over repeated runs, and the
criterion as written does not say so.

## Widened 2026-08-09 at 09.4's review

Taking the sentence above at its word: `done_when` now selects
`dropped_player or no_orphaned_pane`, so the criterion covers the folded half
rather than certifying the thread teardown alone. Both disjuncts name nothing in
the tree today and the criterion stays red at exit 5, which is what it was
before — the widening adds a second thing the work has to make green, not a
green one it can hide behind.
