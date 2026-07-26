"""Video decode. The only place OpenCV is allowed to appear."""

from sieve.decode.identity import decoder_identity
from sieve.decode.reader import VideoDecodeError, VideoReader

__all__ = ["VideoDecodeError", "VideoReader", "decoder_identity"]
