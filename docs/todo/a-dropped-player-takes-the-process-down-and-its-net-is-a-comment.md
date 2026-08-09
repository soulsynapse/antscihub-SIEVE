---
title: A dropped player takes the process down and its net is a comment
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k dropped_player"
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
