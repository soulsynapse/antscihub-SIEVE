"""Secret: what fills the canvas slot on the left of the main window —
the information side, showing whatever ``control/`` (the right slot) has
selected, eventually with light interactive elements of its own (drawing
a crop box, say). ``video_player/`` is one canvas — the raw source video,
played directly. Nothing about the slot itself (where it sits, how big it
starts) belongs here; that's ``layout.py``.

Canvas and control are genuinely coupled, not two independent modules
behind a boundary — a canvas is, in effect, an extension of whichever
control is active: a dragged crop box is control's current step, drawn
somewhere else. So there's no enforced import direction between the two
packages (nothing stops a canvas file importing a control type it needs);
the one thing that stays control's alone is deciding which step or
project is *current* — a canvas reacts to that, it doesn't set it.
Nothing about what a canvas *is* is decided yet — this package holds
implementations, not an interface, until a second one (a project preview)
exists to prove what they share.
"""
