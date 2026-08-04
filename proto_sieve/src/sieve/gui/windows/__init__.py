"""Re-exports each window from its own module, so callers'
``from ...gui.windows import PreferencesWindow`` doesn't change regardless
of what a given window's internals look like."""

from proto_sieve.src.sieve.gui.windows.history import ProjectHistoryWindow
from proto_sieve.src.sieve.gui.windows.preferences import PreferencesWindow

__all__ = ["PreferencesWindow", "ProjectHistoryWindow"]
