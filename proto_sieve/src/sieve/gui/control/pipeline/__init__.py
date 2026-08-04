"""Re-exports the package's public interface from ``pipeline.py``, so
callers' ``from ...gui.control.pipeline import build_step_list`` doesn't
change regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.control.pipeline.pipeline import build_step_list

__all__ = ["build_step_list"]
