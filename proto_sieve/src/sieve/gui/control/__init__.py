"""Secret: what fills the control slot on the right of the main window —
the generic "user selects stuff" space. ``pipeline/`` is one control (the
step list); ``project_select/`` is a second (which project is open).
Nothing about the slot itself (where it sits, how big it starts) belongs
here; that's ``layout.py``.

Control and canvas are genuinely coupled — see ``gui/canvas/__init__.py``
— so there's no enforced boundary between the two packages. The one thing
that stays here alone: deciding which step or project is *current*.
Nothing about what a control *is* is decided as an interface yet — two
implementations exist, but neither shares a base class or a protocol; that
stays undecided until a third makes the shared shape (if any) worth
naming.
"""
