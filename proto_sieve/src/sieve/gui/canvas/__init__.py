"""Secret: what fills the canvas slot on the left of the main window —
the information side, showing whatever ``control/`` (the right slot) has
selected, eventually with light interactive elements of its own (drawing
a crop box, say). ``video_player/`` is one canvas — the raw source video,
played directly. Nothing about the slot itself (where it sits, how big it
starts) belongs here; that's ``layout.py``. A canvas only ever reads
shared session/app state that a control wrote — it must never import from
``control/``, and it never mutates selection itself, even once it grows
elements the user clicks or drags. Nothing about what a canvas *is* is
decided yet — this package holds implementations, not an interface, until
a second one (a project preview) exists to prove what they share.
"""
