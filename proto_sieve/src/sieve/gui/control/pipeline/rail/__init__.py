"""Re-exports the package's public interface from ``rail.py``, so callers'
``from ...gui.control.pipeline.rail import StepRail`` doesn't change
regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.control.pipeline.rail.rail import StepRail

__all__ = ["StepRail"]
