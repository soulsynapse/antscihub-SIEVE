"""Who is being edited right now — a set of sources, not a flag.

Window shortcuts that collide with typing (space plays, Delete removes the
selected replicate, I and O mark the clip) have to stand down while the user is
entering something, because Qt dispatches a window shortcut before the focused
widget ever sees the key. The question "should they stand down?" has more than
one answer arriving at it: a cell editor in the replicate table, a number field
in the crop tools, and every typing control added after them.

A `bool` cannot carry more than one answer. Two sources interleaving — a
`False` from one arriving while the other is still live — either strands the
keys off for the rest of the session or hands them back while somebody is still
typing, and which one you get depends on the order Qt happened to deliver the
signals in.

So the state is a **set keyed by source**, and the aggregate is "is it
non-empty". Three properties follow, and each of them is why this is a set
rather than a counter:

- A stale end cannot clear a live begin: ending source A discards A and leaves
  B, where a decrement would have reached zero.
- A duplicate begin from one source is idempotent, so a widget that announces
  twice — Qt re-delivering a focus event, a field that both types and commits —
  does not have to be balanced exactly.
- A source that disappears is dropped by identity. A field hidden mid-edit, or
  a cell editor destroyed without a focus-out, names itself on the way out; no
  rescue hook has to guess how many outstanding begins it owned.

Qt-free on purpose: this is the arithmetic, and the widget that owns it emits
the signal. `gui/replicate_tab.py` holds the one instance that exists today.
"""

from __future__ import annotations


class EditingSources:
    """The set of sources that currently claim the keyboard."""

    def __init__(self) -> None:
        self._open: set[str] = set()

    @property
    def active(self) -> bool:
        """True while at least one source is being edited."""
        return bool(self._open)

    @property
    def sources(self) -> frozenset[str]:
        """The claimants, for a test or a diagnostic to name them."""
        return frozenset(self._open)

    def mark(self, source: str, editing: bool) -> None:
        """Record that `source` started or stopped being edited.

        Both directions are idempotent — `discard`, not `remove` — because a
        source ending an edit it never began is exactly the case a counter gets
        wrong, and silently doing nothing is the correct answer to it.
        """
        if editing:
            self._open.add(source)
        else:
            self._open.discard(source)

    def clear(self) -> None:
        """Forget every claim. A known-good point, for a caller that has one."""
        self._open.clear()
