








from __future__ import annotations

from functools import cache

import cv2













DECODE_POLICY_VERSION = 2


@cache
def decoder_identity() -> str:

    return f"opencv-{cv2.__version__}/policy-{DECODE_POLICY_VERSION}"
