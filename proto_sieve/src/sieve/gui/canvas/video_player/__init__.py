"""Re-exports the package's public interface from ``video_player.py``, so
callers' ``from ...gui.canvas.video_player import VideoPlayer``
doesn't change regardless of what this package's internals look like."""

from proto_sieve.src.sieve.gui.canvas.video_player.video_player import VideoPlayer

__all__ = ["VideoPlayer"]
