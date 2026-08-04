"""Re-exports the package's public interface from ``appearance.py``, so
callers' ``from ...preferences.appearance import get_appearance`` doesn't
change regardless of what this package's internals look like."""

from proto_sieve.src.sieve.preferences.appearance.appearance import (
    Appearance,
    get_appearance,
    set_appearance,
    subscribe,
)

__all__ = ["Appearance", "get_appearance", "set_appearance", "subscribe"]
