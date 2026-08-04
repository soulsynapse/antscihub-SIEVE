"""Desktop application.

BOUNDARY: Qt stays in this package. Nothing outside `sieve.gui` imports
PySide6, and `sieve.gui` reaches the rest of the system through public APIs
only — it never becomes a second execution path.
"""
