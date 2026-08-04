"""Re-exports the package's public interface from ``menu.py``, so callers'
``from ...gui.menu import build_menu_bar`` doesn't change regardless of
what this package's internals look like."""

from proto_sieve.src.sieve.gui.menu.menu import build_menu_bar

__all__ = ["build_menu_bar"]
