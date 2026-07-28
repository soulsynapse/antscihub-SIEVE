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
#:
#: 2: the luma path (2026-07-27). A graph that reads no chroma is now decoded
#: from the Y plane rather than from a BGR conversion of it, which moves pixel
#: values — the two differ by more than the limited-to-full range expansion,
#: because this footage is BT.709 and `cvtColor(BGR2GRAY)` weights BT.601. Every
#: existing entry was computed from the colour path and must not be served to a
#: run that now decodes luma, so the whole cache turns over once. *Which* format
#: a given run used is a separate question and a per-run one; that is
#: `DecodeFormat` in `cache_key.source_key`, not this constant.
DECODE_POLICY_VERSION = 2


@cache
def decoder_identity() -> str:
    """Stable string identifying the decoder that produced a frame."""
    return f"opencv-{cv2.__version__}/policy-{DECODE_POLICY_VERSION}"
