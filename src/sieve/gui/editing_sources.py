"""Who is being edited right now — a set of sources, not a flag.

Window shortcuts that collide with typing (space plays, Delete removes a
replicate) have to stand down while the user is entering something, because Qt
dispatches a window shortcut before the focused widget ever sees the key. More
than one control answers "should they stand down?": a cell editor in the
replicate table, a number field in the crop tools, and every typing control
added after them.

A `bool` cannot carry more than one answer. Two sources interleaving — a
`False` from one arriving while the other is still live — either strands the
keys off for the rest of the session or hands them back while somebody is still
typing, depending on the order Qt happened to deliver the signals in. That was
the defect in
`docs/completed-todo/2026.07.27-spacebar-dies-on-focus.md`.

A counter fixes the interleaving and loses the rest: an unbalanced end
decrements to zero while another source is still live, a widget that announces
twice has to be balanced exactly, and a field hidden mid-edit or a cell editor
destroyed without a focus-out leaves a begin nobody can attribute. Keying by
source settles all three by identity instead of arithmetic — a departing source
names itself on the way out, so no rescue hook has to guess how many
outstanding begins it owned.

Qt-free on purpose: this is the arithmetic, and the widget that owns it emits
the signal. `gui/replicate_tab.py` holds the one instance that exists today.
"""

from __future__ import annotations


class EditingSources:
    def __init__(self) -> None:
        self._open: set[str] = set()

    @property
    def active(self) -> bool:
        return bool(self._open)

    @property
    def sources(self) -> frozenset[str]:
        return frozenset(self._open)

    def mark(self, source: str, editing: bool) -> None:
        if editing:
            self._open.add(source)
        else:
            self._open.discard(source)

    def clear(self) -> None:
        self._open.clear()
