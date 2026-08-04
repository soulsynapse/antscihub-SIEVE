"""Re-exports the package's public interface from ``hotkeys.py``, so
callers' ``from ...gui.hotkeys import bind_hotkeys`` doesn't change
regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.hotkeys.hotkeys import bind_hotkeys, bind_navigation_hotkeys

__all__ = ["bind_hotkeys", "bind_navigation_hotkeys"]
