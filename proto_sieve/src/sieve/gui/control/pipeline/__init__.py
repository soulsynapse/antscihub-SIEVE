"""Re-exports the package's public interface from ``pipeline.py``, so
callers' ``from ...gui.control.pipeline import PipelinePanel`` doesn't
change regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.control.pipeline.pipeline import PipelinePanel

__all__ = ["PipelinePanel"]
