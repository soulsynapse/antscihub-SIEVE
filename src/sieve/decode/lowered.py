"""Pure value objects for source prefixes that have been lowered into decode.

The subprocess that performs the lowering lives in `decode/ffmpeg.py`; this
module is deliberately inert so cache-key and planning code can name the source
contract without importing process machinery. A lowered source is a different
source: it has already applied a source-space crop and one area scale before
Python sees the frame, so the route and the exact prefix have to enter the root
key.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.core.types import ROI

LOWERED_SOURCE_POLICY_VERSION = 1
FFMPEG_GRAY8_ROUTE = "ffmpeg-lowered-gray8"


def roi_parts(roi: ROI) -> tuple[int, int, int, int]:
    """`roi` in the only order FFmpeg and the cache key both use."""
    return (roi.x, roi.y, roi.width, roi.height)


@dataclass(frozen=True, slots=True)
class LoweredStep:
    """One declared operation that was removed from the executor's DAG."""

    name: str
    version: str
    params_json: str

    def cache_parts(self) -> tuple[str, str, str]:
        return (self.name, self.version, self.params_json)


@dataclass(frozen=True, slots=True)
class LoweredScale:
    """The one spatial scale operation FFmpeg will apply."""

    filter_id: str
    version: str
    params_json: str
    output_width: int
    output_height: int

    def cache_parts(self) -> tuple[str, str, str, int, int]:
        return (
            self.filter_id,
            self.version,
            self.params_json,
            self.output_width,
            self.output_height,
        )


@dataclass(frozen=True, slots=True)
class LoweredPrefix:
    """The source-side crop and scale now owned by the decoder route."""

    decoder_identity: str
    source_roi: ROI
    ffmpeg_roi: ROI
    scale: LoweredScale
    steps: tuple[LoweredStep, ...]
    route: str = FFMPEG_GRAY8_ROUTE
    policy_version: int = LOWERED_SOURCE_POLICY_VERSION

    @property
    def output_width(self) -> int:
        return self.scale.output_width

    @property
    def output_height(self) -> int:
        return self.scale.output_height

    @property
    def frame_bytes(self) -> int:
        """Gray8 rawvideo has one byte per pixel."""
        return self.output_width * self.output_height

    @property
    def filtergraph(self) -> str:
        """The FFmpeg filter graph, including the odd-origin crop guard."""
        roi = self.ffmpeg_roi
        return (
            f"crop={roi.width}:{roi.height}:{roi.x}:{roi.y}:exact=1,"
            f"scale={self.output_width}:{self.output_height}:flags=area,"
            "format=gray"
        )

    def cache_parts(self) -> dict[str, object]:
        """JSON-representable identity of the route and replaced prefix."""
        return {
            "route": self.route,
            "policy": self.policy_version,
            "crop_exact": True,
            "scale_flags": "area",
            "pixel_format": "gray8",
            "source_roi": roi_parts(self.source_roi),
            "ffmpeg_roi": roi_parts(self.ffmpeg_roi),
            "scale": self.scale.cache_parts(),
            "steps": tuple(step.cache_parts() for step in self.steps),
        }

    def description(self) -> str:
        roi = self.source_roi
        return (
            f"{self.route} crop {roi.width}x{roi.height}+{roi.x}+{roi.y} "
            f"-> {self.output_width}x{self.output_height}"
        )
