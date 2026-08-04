"""Re-exports the package's public interface from ``project_select.py``, so
callers' ``from ...gui.control.project_select import ProjectSelect`` doesn't
change regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.control.project_select.project_select import ProjectSelect

__all__ = ["ProjectSelect"]
