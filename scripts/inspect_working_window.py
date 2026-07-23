from __future__ import annotations

import argparse
import json
from pathlib import Path

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.application.working_window import (
    WorkingWindowRequest,
    open_working_window,
)
from antscihub_sieve.errors import SieveError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect the development working-window source"
    )
    parser.add_argument("asset", type=Path)
    parser.add_argument("start", type=int)
    parser.add_argument("stop", type=int)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument(
        "--cancel-after-frames",
        type=int,
        help="cancel before decoding the frame at this zero-based request offset",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        assets = AssetService()
        sidecar_path, _ = assets.resolve(args.asset)
        if not sidecar_path.is_file():
            raise SieveError(
                "ASSET_SIDECAR_MISSING",
                "The diagnostic requires a registered asset",
                path=str(sidecar_path),
            )
        inspected = assets.inspect(sidecar_path)
        asset = inspected["asset"]
        request = WorkingWindowRequest(
            asset_ref=Path(inspected["sidecar_path"]),
            expected_asset_id=asset["asset_id"],
            expected_content_sha256=asset["media"]["content_sha256"],
            start_frame=args.start,
            stop_frame=args.stop,
        )
        cancellation_checks = 0

        def cancelled() -> bool:
            nonlocal cancellation_checks
            should_cancel = (
                args.cancel_after_frames is not None
                and cancellation_checks >= args.cancel_after_frames
            )
            cancellation_checks += 1
            return should_cancel

        stream = open_working_window(
            request,
            batch_size=args.batch_size,
            cancelled=cancelled,
            assets=assets,
        )
        batches: list[dict[str, object]] = []
        error: dict[str, object] | None = None
        try:
            with stream:
                for batch in stream:
                    batches.append(
                        {
                            "absolute_frame_indices": list(
                                batch.absolute_frame_indices
                            ),
                            "shape": list(batch.shape),
                        }
                    )
        except SieveError as exc:
            error = exc.as_dict()

        resolved = stream.resolved
        outcome = stream.outcome
        assert outcome is not None
        result = {
            "asset_id": resolved.asset_id,
            "content_sha256": resolved.content_sha256,
            "identity_status": resolved.identity_status,
            "media_path": str(resolved.media_path),
            "requested_span": [
                resolved.start_frame,
                resolved.stop_frame,
            ],
            "declared_stop": resolved.declared_stop,
            "extent_provenance": resolved.extent_provenance.value,
            "fps": [resolved.fps_num, resolved.fps_den],
            "plane": {
                "plane_id": resolved.plane.plane_id,
                "shape": list(resolved.plane.per_frame_shape),
                "dtype": resolved.plane.dtype,
                "value_domain": [
                    resolved.plane.value_min,
                    resolved.plane.value_max,
                ],
                "channel_order": list(resolved.plane.channel_order),
                "backend": resolved.plane.backend,
                "source_pixel_format": resolved.plane.source_pixel_format,
                "source_color_range": resolved.plane.source_color_range,
                "source_color_space": resolved.plane.source_color_space,
                "source_color_transfer": resolved.plane.source_color_transfer,
                "source_color_primaries": resolved.plane.source_color_primaries,
            },
            "batches": batches,
            "outcome": {
                "kind": outcome.kind.value,
                "delivered_span": [
                    outcome.delivered_start,
                    outcome.delivered_stop,
                ],
                "stopped_at_frame": outcome.stopped_at_frame,
                "error": (
                    outcome.error.as_dict()
                    if outcome.error is not None
                    else error
                ),
            },
        }
        print(json.dumps(result, indent=2))
        return 0 if outcome.kind.value != "failed" else 1
    except SieveError as exc:
        print(json.dumps({"error": exc.as_dict()}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
