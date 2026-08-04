"""Re-exports the package's public interface from ``breadcrumb_stack.py``,
so callers' ``from ...gui.breadcrumb_stack import BreadcrumbStack`` doesn't
change regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.breadcrumb_stack.breadcrumb_stack import BreadcrumbStack

__all__ = ["BreadcrumbStack"]
