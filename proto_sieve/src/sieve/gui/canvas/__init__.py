"""Secret: what fills the representation slot on the left of the main
window. ``video_player/`` is one representation — the raw source video,
played directly. Nothing about the slot itself (where it sits, how big it
starts) belongs here; that's ``layout.py``. Nothing about what a
representation *is* is decided yet — this package holds implementations,
not an interface, until a second one exists to prove what they share.
"""
