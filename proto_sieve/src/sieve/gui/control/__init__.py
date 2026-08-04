"""Secret: what fills the control slot on the right of the main window —
the generic "user selects/edits stuff" space. ``pipeline/`` is one control
(the step list). Nothing about the slot itself (where it sits, how big it
starts) belongs here; that's ``layout.py``. A control mutates shared
session/app state; ``canvas/`` (the left slot) only ever reads it back — a
control widget must never import from ``canvas/``, and canvas must never
need to know a specific control exists. Nothing about what a control *is*
is decided yet — this package holds implementations, not an interface,
until a second one (project selection) exists to prove what they share.
"""
