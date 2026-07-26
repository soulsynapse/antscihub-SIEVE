"""Decoder identity string for cache key derivation.

Two runs that decode the same file with different decoders can disagree on
pixel values — different colour matrices, different handling of B-frames on
seek. Any cache key over decoded content therefore has to include who did the
decoding. Changing the decoder invalidates every downstream entry, which is
the intended behaviour and the reason OpenCV is pinned below 5.x.
"""

from __future__ import annotations

from functools import cache

import cv2

#: Bumped by hand when this package changes how it decodes, independently of
#: the OpenCV version — e.g. a change to the seek strategy that could land on
#: a different frame.
DECODE_POLICY_VERSION = 1


@cache
def decoder_identity() -> str:
    """Stable string identifying the decoder that produced a frame."""
    return f"opencv-{cv2.__version__}/policy-{DECODE_POLICY_VERSION}"
