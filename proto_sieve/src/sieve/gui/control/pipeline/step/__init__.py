"""Re-exports the package's public interface from ``step.py``, so callers'
``from ...gui.control.pipeline.step import StepBox`` doesn't change regardless
of what this package's internals look like."""

from proto_sieve.src.sieve.gui.control.pipeline.step.step import StepBox

__all__ = ["StepBox"]
