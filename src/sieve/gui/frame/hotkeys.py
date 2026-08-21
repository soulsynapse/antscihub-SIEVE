"""The keys the window answers, and never what answering them does.

Two tables, each read top to bottom, so what a key is bound to is a fact about
the frame that can be checked by reading a list — the alternative is a
`QShortcut` created wherever the verb happens to live, and then no file can say
what the keyboard does. The verbs themselves are the window's, named here only
as strings: this file decides what a key means and nothing about how the frame
carries it out, which is the same division `menu.py` makes for the bar.

A binding is written only for something the frame can already do. The menu bar
shows disabled entries for what has not landed because a menu is a picture of
the application's shape; a key is not — a bound key that does nothing is
indistinguishable from a key that is broken, and there is nothing greyed out to
look at.

**Two tables and not one, because the frame owns two kinds of key.** `_KEYS` is
what the frame answers wherever focus is: nothing else in the tree wants Ctrl+R,
so a shortcut that fires first is exactly right. `_YIELDED_KEYS` is what the
frame answers only if nothing in front of it did. ← and → mean *along a line*
and the frame's line is the track, but a segmented bar and a tab row are lines
too, and they are the lines the user is looking straight at. So the frame takes
the axis last rather than first.

That difference is the whole reason the second table is not a shortcut. A
`QShortcut` is offered the key before the focused widget is, so it cannot
decline in favour of one; an unhandled key event walks up the parent chain
instead, which is that ordering the right way round. `MainWindow.keyPressEvent`
is where the walk ends, and `answer_key` is what it asks.

↑ and ↓ are in neither table. They mean the next row of whatever holds focus,
every view that has rows already answers them itself, and there is no frame-wide
motion on that axis for them to fall through to.

Shortcuts are the window's, not the application's, so they act only while it
holds focus, and none of them repeat: the swipe re-aims a running slide at each
keystroke, so an autorepeating arrow would walk the track at the keyboard's
repeat rate rather than at the user's. A yielded key declines a repeat the same
way, and by declining rather than swallowing — a repeat the frame will not act
on is a repeat that belongs to whatever else might.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut

if TYPE_CHECKING:  # importing it for real would close the loop back to `window`
    from sieve.gui.frame.window import MainWindow

#: Each key sequence the frame answers wherever focus is, and the method name on
#: the window that answers it.
#:
#: Ctrl+R is on no menu, and is the reason this table is not the bar's leftovers:
#: reloading is not part of the picture the bar draws of what the application is
#: — it acts on the run rather than on the window or on a project, which is the
#: line `menu.py` keeps — but it is still something the frame can do, and a key
#: is where a thing the user does between edits belongs.
_KEYS: tuple[tuple[str, str], ...] = (("Ctrl+R", "reload"),)

#: Each key sequence the frame answers only where nothing nearer the user has,
#: and the method name on the window that answers it.
#:
#: ← and → are the swipe's, and are spent on it: the track is the one thing in
#: the frame that runs on a line, so the two keys that mean *along a line* say
#: exactly one thing wherever the user is standing — unless what they are
#: standing on runs on a line of its own. A segmented bar and a tab row both
#: walk their own options on this axis, and both are a thing the user has
#: deliberately put the keyboard on. Yielding to them costs the track nothing
#: the user can feel, since the widget that took the key is the one they were
#: looking at, and it keeps one motion spelled one way rather than putting the
#: track behind a modifier for the sake of two widgets.
_YIELDED_KEYS: tuple[tuple[str, str], ...] = (
    ("Left", "swipe_back"),
    ("Right", "swipe_forward"),
)


@dataclass
class Hotkeys:
    """What the frame answers, and whether it is answering at all.

    Held rather than returned loose because the two tables are suspended
    together and a caller should not be able to hold half of that. The window is
    kept so `answer_key` needs only the event: what a key means and who carries
    it out were decided at the same moment, and separating them here would make
    a caller re-supply the second.
    """

    window: MainWindow
    shortcuts: list[QShortcut] = field(default_factory=list)
    suspended: bool = False


def bind_hotkeys(window: MainWindow) -> Hotkeys:
    """Bind the frame's own keys to the window that carries them.

    Only `_KEYS` is bound here. `_YIELDED_KEYS` is not bound to anything — a
    binding is the thing it must not have, since a bound key is offered before
    the focused widget rather than after it. It is read at the end of the walk
    instead, by `answer_key`.
    """
    hotkeys = Hotkeys(window)
    for key, verb in _KEYS:
        shortcut = QShortcut(QKeySequence(key), window)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(getattr(window, verb))
        hotkeys.shortcuts.append(shortcut)
    return hotkeys


def answer_key(hotkeys: Hotkeys, event: QKeyEvent) -> bool:
    """Answer a key nothing in front of the window wanted, or decline it.

    True when the frame acted, which is the caller's cue to accept the event.
    False leaves it exactly as it arrived, so a key the frame has no use for
    goes on being unhandled rather than being quietly eaten by the last widget
    that looked at it.

    A repeat is declined rather than answered, for the reason the shortcuts
    switch it off: the swipe re-aims a running slide at each keystroke, so a
    held arrow would walk the track at the keyboard's rate. Declined and not
    swallowed, because the frame refusing to act on a repeat is not the frame
    claiming it.
    """
    if hotkeys.suspended or event.isAutoRepeat():
        return False
    pressed = QKeySequence(event.keyCombination())
    for key, verb in _YIELDED_KEYS:
        if pressed == QKeySequence(key):
            getattr(hotkeys.window, verb)()
            return True
    return False


def suspend_hotkeys(hotkeys: Hotkeys, suspended: bool) -> None:
    """Take the frame's keys away while something stands over the panes.

    A shortcut on the window fires wherever focus is, which is what makes it the
    frame's rather than a view's — and is exactly wrong while a view is covering
    the panes: ← and → would walk a track the user cannot see, and they would
    come back to a swipe standing somewhere they never took it. So the keys are
    held for as long as the cover is up, rather than every verb learning to ask
    whether it should run.

    Both tables, and the yielded one is the half that now has to be said out
    loud. A cover takes focus, but a key it does not use walks up the same
    parent chain as any other — so the track is reachable from behind a scrim
    unless the flag below is what `answer_key` reads first.
    """
    hotkeys.suspended = suspended
    for shortcut in hotkeys.shortcuts:
        shortcut.setEnabled(not suspended)
