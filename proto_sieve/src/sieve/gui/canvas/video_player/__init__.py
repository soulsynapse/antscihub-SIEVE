"""Re-exports the package's public interface from ``video_player.py``, so
callers' ``from ...gui.representation.video_player import VideoPlayer``
doesn't change regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.representation.video_player.video_player import VideoPlayer

__all__ = ["VideoPlayer"]
