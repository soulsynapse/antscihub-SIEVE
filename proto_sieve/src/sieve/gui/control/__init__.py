"""Secret: what fills the control slot on the right of the main window —
the generic "user selects stuff" space, and which of its three screens
(project selection, pipeline, step) is current. ``pipeline/`` and
``project_select/`` are its two content sources; ``control.py`` is what
assembles them into one sliding track plus the rail. Nothing about the
slot itself (where it sits, how big it starts) belongs here; that's
``layout.py``.

Control and canvas are genuinely coupled — see ``gui/canvas/__init__.py``
— so there's no enforced boundary between the two packages. Which step is
current is ``session.Session``'s fact, not this package's — ``control.py``
only ever renders whatever index it's given.
"""

from proto_sieve.src.sieve.gui.control.control import Control

__all__ = ["Control"]
