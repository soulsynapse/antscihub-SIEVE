"""Secret: what fills the control slot on the right of the main window —
the generic "user selects stuff" space. ``pipeline/`` is one control (the
step list). Nothing about the slot itself (where it sits, how big it
starts) belongs here; that's ``layout.py``.

Control and canvas are genuinely coupled — see ``gui/canvas/__init__.py``
— so there's no enforced boundary between the two packages. The one thing
that stays here alone: deciding which step or project is *current*.
Nothing about what a control *is* is decided yet — this package holds
implementations, not an interface, until a second one (project selection)
exists to prove what they share.
"""
