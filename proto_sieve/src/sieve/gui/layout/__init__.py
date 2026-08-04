"""Re-exports the package's public interface from ``layout.py``, so callers'
``from ...gui.layout import compose, size_window`` doesn't change regardless
of what this package's internals look like."""

from proto_sieve.src.sieve.gui.layout.layout import compose, size_window

__all__ = ["compose", "size_window"]
