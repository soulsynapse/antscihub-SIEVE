"""Re-exports the package's public interface from ``flags.py``, so callers'
``from ...preferences.dev import flags`` doesn't change regardless of what
this package's internals look like."""

from proto_sieve.src.sieve.preferences.dev import flags

__all__ = ["flags"]
