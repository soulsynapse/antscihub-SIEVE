from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EncodingProfile:
    name: str
    codec: str
    pixel_format: str
    arguments: tuple[str, ...]
    color_metadata: dict[str, str]


PROFILES = {
    "lossless": EncodingProfile("lossless", "ffv1", "bgr0", ("-c:v", "ffv1", "-level", "3", "-g", "1", "-pix_fmt", "bgr0", "-color_range", "pc"), {"range": "full", "space": "rgb"}),
    "high-quality": EncodingProfile("high-quality", "libx264rgb", "bgr0", ("-c:v", "libx264rgb", "-crf", "12", "-preset", "medium", "-pix_fmt", "bgr0", "-color_range", "pc"), {"range": "full", "space": "rgb"}),
    "compact": EncodingProfile("compact", "libx264", "yuv444p", ("-c:v", "libx264", "-crf", "23", "-preset", "medium", "-pix_fmt", "yuv444p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"), {"range": "limited", "space": "bt709", "primaries": "bt709", "transfer": "bt709"}),
}
