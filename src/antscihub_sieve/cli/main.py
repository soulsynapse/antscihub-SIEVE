from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.application.derivation import DerivationService
from antscihub_sieve.application.layouts import LayoutService
from antscihub_sieve.application.lineage import LineageService
from antscihub_sieve.errors import SieveError
from antscihub_sieve.media.benchmark import (
    benchmark_media,
    format_media_benchmark,
)
from antscihub_sieve.media.session import MediaSession


def _box(value: str) -> str:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be x0,y0,x1,y1")
    try:
        [int(p) for p in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("box edges must be integers") from exc
    return value


def _json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="write the result as JSON to stdout")


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _at_least_two(value: str) -> int:
    parsed = _positive_int(value)
    if parsed < 2:
        raise argparse.ArgumentTypeError("value must be at least 2")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sieve", description="SIEVE replicate asset tools")
    parser.add_argument("--log-format", choices=("human", "json"), default="human")
    commands = parser.add_subparsers(dest="command", required=True)

    asset = commands.add_parser("asset", help="inspect, initialize, and verify assets"); asset_sub = asset.add_subparsers(dest="action", required=True)
    p = asset_sub.add_parser("inspect"); p.add_argument("reference"); _json_flag(p)
    p = asset_sub.add_parser("init"); p.add_argument("video"); p.add_argument("--label", help="display label; defaults to the filename stem"); _json_flag(p)
    p = asset_sub.add_parser("verify"); p.add_argument("reference"); p.add_argument("--level", choices=("metadata", "quick", "full"), default="metadata"); _json_flag(p)

    lineage = commands.add_parser("lineage", help="inspect and resolve asset lineage"); lineage_sub = lineage.add_subparsers(dest="action", required=True)
    p = lineage_sub.add_parser("show"); p.add_argument("reference"); _json_flag(p)
    p = lineage_sub.add_parser("parent"); p.add_argument("reference"); p.add_argument("--locate"); _json_flag(p)

    layout = commands.add_parser("layout", help="manage editable replicate layouts"); layout_sub = layout.add_subparsers(dest="action", required=True)
    p = layout_sub.add_parser("inspect"); p.add_argument("reference"); _json_flag(p)
    p = layout_sub.add_parser("add"); p.add_argument("parent"); p.add_argument("--box", type=_box, required=True); p.add_argument("--label"); _json_flag(p)
    p = layout_sub.add_parser("update"); p.add_argument("parent"); p.add_argument("--region-id", required=True); p.add_argument("--box", type=_box, required=True); _json_flag(p)
    p = layout_sub.add_parser("rename"); p.add_argument("parent"); p.add_argument("--region-id", required=True); p.add_argument("--label", required=True); _json_flag(p)
    p = layout_sub.add_parser("remove"); p.add_argument("parent"); p.add_argument("--region-id", required=True); _json_flag(p)
    p = layout_sub.add_parser("clear"); p.add_argument("parent"); _json_flag(p)
    p = layout_sub.add_parser("import"); p.add_argument("parent"); p.add_argument("template"); _json_flag(p)
    p = layout_sub.add_parser("export"); p.add_argument("parent"); p.add_argument("--out", required=True); p.add_argument("--drafts-only", action="store_true", required=True); _json_flag(p)
    p = layout_sub.add_parser("validate"); p.add_argument("reference"); _json_flag(p)

    media = commands.add_parser("media", help="probe media and decode preview frames"); media_sub = media.add_subparsers(dest="action", required=True)
    p = media_sub.add_parser("probe"); p.add_argument("asset"); _json_flag(p)
    p = media_sub.add_parser("frame"); p.add_argument("asset"); group = p.add_mutually_exclusive_group(required=True); group.add_argument("--frame", type=int); group.add_argument("--time"); p.add_argument("--out", required=True); _json_flag(p)
    p = media_sub.add_parser("benchmark", help="estimate media responsiveness on this computer"); p.add_argument("asset")
    representation = p.add_mutually_exclusive_group()
    representation.add_argument("--native", action="store_true", help="measure full-resolution RGB instead of the 1280-pixel display representation")
    representation.add_argument("--max-width", type=_positive_int, default=1280, help="display representation width cap (default: 1280)")
    p.add_argument("--iterations", type=_positive_int, default=3)
    p.add_argument("--sequential-frames", type=_at_least_two, default=12)
    _json_flag(p)

    derive = commands.add_parser("derive", help="materialize child replicate assets")
    derive.add_argument("parent", nargs="?", help="parent asset, or the literal 'verify'"); derive.add_argument("target", nargs="?", help="child asset when using 'derive verify'"); derive.add_argument("--crop", type=_box); derive.add_argument("--label")
    derive.add_argument("--layout"); derive.add_argument("--region-id", action="append", dest="region_ids"); derive.add_argument("--out")
    derive.add_argument("--profile", choices=("lossless", "high-quality", "compact"), default="lossless"); derive.add_argument("--plan", action="store_true")
    derive.add_argument("--verify", metavar="CHILD", dest="verify_child"); _json_flag(derive)
    return parser


def _seconds(value: str) -> float:
    raw = value.strip().lower(); raw = raw[:-1] if raw.endswith("s") else raw
    try:
        return float(raw)
    except ValueError as exc:
        raise SieveError("FRAME_DECODE_FAILED", "Time must be seconds, such as 12.5s", time=value) from exc


def dispatch(args: argparse.Namespace) -> Any:
    assets = AssetService(); layouts = LayoutService(assets); lineage = LineageService(assets)
    if args.command == "asset":
        if args.action == "inspect": return assets.inspect(args.reference)
        if args.action == "init": return assets.initialize(args.video, label=args.label)
        return assets.verify(args.reference, level=args.level)
    if args.command == "lineage":
        if args.action == "show": return lineage.describe(args.reference)
        return lineage.resolve_parent(args.reference, args.locate)
    if args.command == "layout":
        if args.action == "inspect": return layouts.load(args.reference)
        if args.action == "add": return layouts.add(args.parent, args.box, args.label)
        if args.action == "update": return layouts.update(args.parent, args.region_id, args.box)
        if args.action == "rename": return layouts.rename(args.parent, args.region_id, args.label)
        if args.action == "remove": return layouts.remove(args.parent, args.region_id)
        if args.action == "clear": return layouts.clear(args.parent)
        if args.action == "import": return layouts.import_template(args.parent, args.template)
        if args.action == "export": return layouts.export_template(args.parent, args.out)
        return layouts.validate(args.reference)
    if args.command == "media":
        inspected = assets.verify(args.asset, level="metadata")
        if args.action == "benchmark":
            return benchmark_media(
                Path(inspected["media_path"]),
                asset=inspected["asset"],
                iterations=args.iterations,
                sequential_frames=args.sequential_frames,
                max_width=None if args.native else args.max_width,
            )
        session = MediaSession(Path(inspected["media_path"]))
        try:
            if args.action == "probe":
                return {"asset_id": inspected["asset"]["asset_id"], "media_path": inspected["media_path"], **session.metadata, "frame_count": session.frame_count}
            frame = args.frame if args.frame is not None else session.resolve_time(_seconds(args.time))
            output = Path(args.out).expanduser().resolve(); session.read_frame(frame, output)
            return {"asset_id": inspected["asset"]["asset_id"], "frame": frame, "time_seconds": float(session.timestamp_for_frame(frame)), "output_path": str(output)}
        finally:
            session.close()
    if args.command == "derive":
        service = DerivationService(assets, layouts)
        if args.verify_child or args.parent == "verify":
            child = args.verify_child or args.target
            if not child: raise SieveError("DERIVATION_VERIFY_FAILED", "derive verify requires a child asset or package")
            return service.verify(child)
        if args.target:
            raise SieveError("ENCODER_START_FAILED", "Unexpected positional argument", argument=args.target)
        if not args.parent or not args.out:
            raise SieveError("ENCODER_START_FAILED", "derive requires PARENT and --out")
        progress = lambda record: print(json.dumps(record) if args.log_format == "json" else f"[{record['phase']}] {record['label']}: {record['message']}", file=sys.stderr, flush=True)
        options = dict(out=args.out, profile=args.profile, crop=args.crop, label=args.label, layout=args.layout, region_ids=args.region_ids)
        return service.plan(args.parent, **options) if args.plan else service.run(args.parent, progress=progress, **options)
    raise AssertionError("unhandled command")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv); result = dispatch(args)
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False))
        elif (
            getattr(args, "command", None) == "media"
            and getattr(args, "action", None) == "benchmark"
        ):
            print(format_media_benchmark(result))
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except SieveError as exc:
        print(json.dumps({"error": exc.as_dict()}, ensure_ascii=False), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(json.dumps({"error": {"code": "DERIVATION_CANCELLED", "message": "Interrupted", "context": {}}}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
