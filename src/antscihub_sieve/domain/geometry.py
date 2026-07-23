from __future__ import annotations

from collections.abc import Iterable

from antscihub_sieve.errors import SieveError

Box = tuple[int, int, int, int]


def parse_box(value: str | Iterable[int]) -> Box:
    try:
        parts = [int(part.strip()) for part in value.split(",")] if isinstance(value, str) else [int(v) for v in value]
    except (TypeError, ValueError) as exc:
        raise SieveError("LAYOUT_COORDINATES_INVALID", "A box must contain four integer edges", box=value) from exc
    if len(parts) != 4:
        raise SieveError("LAYOUT_COORDINATES_INVALID", "A box must contain x0,y0,x1,y1", box=value)
    return tuple(parts)  # type: ignore[return-value]


def validate_box(box: str | Iterable[int], width: int, height: int) -> Box:
    x0, y0, x1, y1 = parse_box(box)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise SieveError(
            "LAYOUT_COORDINATES_INVALID",
            f"Box {(x0, y0, x1, y1)} is outside the {width}x{height} half-open frame",
            box=[x0, y0, x1, y1], width=width, height=height,
        )
    return x0, y0, x1, y1


def clamp_move(box: Box, x0: int, y0: int, width: int, height: int) -> Box:
    box_width, box_height = box[2] - box[0], box[3] - box[1]
    x0 = min(max(0, int(x0)), width - box_width)
    y0 = min(max(0, int(y0)), height - box_height)
    return x0, y0, x0 + box_width, y0 + box_height


def compose_translation(boxes: Iterable[Iterable[int]]) -> tuple[int, int]:
    x, y = 0, 0
    for box in boxes:
        x0, y0, _, _ = parse_box(box)
        x += x0
        y += y0
    return x, y
