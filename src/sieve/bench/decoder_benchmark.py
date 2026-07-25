"""Benchmark video decoder throughput, seeking, dtype, memory, and footprint.

The controller launches one worker process per decoder/clip pair so RSS is not
contaminated by decoders benchmarked earlier in the run. Pixel hashes are
decoder-local: a random request for frame N is compared with that decoder's
own sequentially decoded frame N.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import platform
import random
import subprocess
import sys
import threading
import time
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import psutil

from sieve.bench.corpus import CORPUS_FILENAME, DEFAULT_CORPUS_DIR, Clip, read_manifest

BACKENDS = ("pyav", "decord", "imageio-ffmpeg", "opencv-videocapture")
MIB = 1024 * 1024


class PeakRssSampler:
    """Sample the worker plus child processes (notably imageio's FFmpeg)."""

    def __init__(self, interval_s: float = 0.005) -> None:
        self._process = psutil.Process()
        self._interval_s = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.baseline_bytes = self._rss_bytes()
        self.peak_bytes = self.baseline_bytes

    def _rss_bytes(self) -> int:
        processes = [self._process]
        with contextlib.suppress(psutil.Error):
            processes.extend(self._process.children(recursive=True))
        total = 0
        for process in processes:
            with contextlib.suppress(psutil.Error):
                total += process.memory_info().rss
        return total

    def _run(self) -> None:
        while not self._stop.wait(self._interval_s):
            self.peak_bytes = max(self.peak_bytes, self._rss_bytes())

    def __enter__(self) -> PeakRssSampler:
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        self._thread.join()
        self.peak_bytes = max(self.peak_bytes, self._rss_bytes())


def _hash_pixels(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(contiguous.dtype.str.encode("ascii"))
    digest.update(np.asarray(contiguous.shape, dtype=np.int64).tobytes())
    digest.update(contiguous.tobytes())
    return digest.hexdigest()


def _generate_corpus(corpus_dir: Path, ffmpeg: str, frames: int) -> Path:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    specifications = [
        (
            "h264-8bit",
            "H.264 8-bit",
            "h264_8bit.mp4",
            8,
            ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p"],
        ),
        (
            "h264-10bit",
            "H.264 10-bit",
            "h264_10bit.mp4",
            10,
            [
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p10le",
            ],
        ),
        (
            "h265",
            "H.265",
            "h265.mp4",
            8,
            [
                "-c:v",
                "libx265",
                "-preset",
                "fast",
                "-crf",
                "22",
                "-pix_fmt",
                "yuv420p",
                "-x265-params",
                "log-level=error",
            ],
        ),
        (
            "vp9",
            "VP9",
            "vp9.webm",
            8,
            [
                "-c:v",
                "libvpx-vp9",
                "-cpu-used",
                "4",
                "-crf",
                "28",
                "-b:v",
                "0",
                "-pix_fmt",
                "yuv420p",
            ],
        ),
        (
            "prores",
            "ProRes 422 HQ",
            "prores.mov",
            10,
            ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"],
        ),
    ]
    manifest: dict[str, Any] = {
        "generated_by": "sieve.bench.decoder_benchmark",
        "source": "FFmpeg testsrc2, 640x360, 30 fps",
        "frames": frames,
        "clips": [],
    }
    for label, codec, filename, bit_depth, codec_args in specifications:
        output = corpus_dir / filename
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30",
            "-frames:v",
            str(frames),
            "-g",
            "60",
            *codec_args,
            str(output),
        ]
        print(f"Generating {codec}: {output}")
        subprocess.run(command, check=True)
        manifest["clips"].append(
            {
                "label": label,
                "codec": codec,
                "file": filename,
                "expected_bit_depth": bit_depth,
            }
        )
    manifest_path = corpus_dir / CORPUS_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _pyav_frames(path: Path, limit: int) -> Iterator[tuple[np.ndarray, int | None]]:
    import av

    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        for index, frame in enumerate(container.decode(stream)):
            if index >= limit:
                break
            yield frame.to_ndarray(format="rgb24"), frame.pts


def _pyav_seek(path: Path, frame_pts: list[int | None], index: int) -> np.ndarray:
    import av

    target_pts = frame_pts[index]
    if target_pts is None:
        raise RuntimeError("PyAV frame has no PTS; exact seeking is undefined")
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        container.seek(target_pts, stream=stream, backward=True, any_frame=False)
        for frame in container.decode(stream):
            if frame.pts is not None and frame.pts >= target_pts:
                if frame.pts != target_pts:
                    raise RuntimeError(
                        f"Seek passed requested PTS {target_pts}; decoded {frame.pts}"
                    )
                return frame.to_ndarray(format="rgb24")
    raise IndexError(index)


def _pyav_dtype(path: Path) -> dict[str, Any]:
    import av

    with av.open(str(path)) as container:
        frame = next(container.decode(video=0))
        component_bits = max(component.bits for component in frame.format.components)
        if component_bits > 8:
            # PyAV does not implement to_ndarray() for every high-bit-depth
            # planar format (including yuv420p10le), but its decoded AVFrame
            # planes retain the native little-endian samples and expose the
            # buffer protocol.
            native = np.frombuffer(frame.planes[0], dtype="<u2")
        else:
            native = np.frombuffer(frame.planes[0], dtype=np.uint8)
        return {
            "dtype": str(native.dtype),
            "pixel_format": frame.format.name,
            "component_bits": component_bits,
        }


def _decord_frames(path: Path, limit: int) -> Iterator[tuple[np.ndarray, None]]:
    import decord

    reader = decord.VideoReader(str(path), ctx=decord.cpu(0))
    for index in range(min(limit, len(reader))):
        yield reader[index].asnumpy(), None


def _decord_seek(path: Path, _metadata: list[None], index: int) -> np.ndarray:
    import decord

    reader = decord.VideoReader(str(path), ctx=decord.cpu(0))
    return reader[index].asnumpy()


def _decord_dtype(path: Path) -> dict[str, Any]:
    import decord

    array = decord.VideoReader(str(path), ctx=decord.cpu(0))[0].asnumpy()
    return {"dtype": str(array.dtype), "pixel_format": "RGB"}


def _imageio_generator(
    path: Path, *, input_params: list[str] | None = None
) -> tuple[Iterator[bytes], dict[str, Any]]:
    import imageio_ffmpeg

    generator = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24", input_params=input_params)
    metadata = next(generator)
    return generator, metadata


def _imageio_frames(path: Path, limit: int) -> Iterator[tuple[np.ndarray, None]]:
    generator, metadata = _imageio_generator(path)
    width, height = metadata["size"]
    try:
        for index, frame_bytes in enumerate(generator):
            if index >= limit:
                break
            yield np.frombuffer(frame_bytes, dtype=np.uint8).reshape(height, width, 3), None
    finally:
        generator.close()


def _imageio_seek(path: Path, metadata: list[None], index: int) -> np.ndarray:
    del metadata
    probe, info = _imageio_generator(path)
    probe.close()
    fps = float(info["fps"])
    generator, seek_info = _imageio_generator(path, input_params=["-ss", f"{index / fps:.12f}"])
    width, height = seek_info["size"]
    try:
        frame_bytes = next(generator)
        return np.frombuffer(frame_bytes, dtype=np.uint8).reshape(height, width, 3)
    finally:
        generator.close()


def _imageio_dtype(path: Path) -> dict[str, Any]:
    generator, _metadata = _imageio_generator(path)
    try:
        array = np.frombuffer(next(generator), dtype=np.uint8)
        return {"dtype": str(array.dtype), "pixel_format": "rgb24"}
    finally:
        generator.close()


def _opencv_frames(path: Path, limit: int) -> Iterator[tuple[np.ndarray, None]]:
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open {path}")
    try:
        for _index in range(limit):
            ok, frame = capture.read()
            if not ok:
                break
            yield frame, None
    finally:
        capture.release()


def _opencv_seek(path: Path, _metadata: list[None], index: int) -> np.ndarray:
    import cv2

    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise RuntimeError(f"OpenCV could not open {path}")
        if not capture.set(cv2.CAP_PROP_POS_FRAMES, index):
            raise RuntimeError(f"OpenCV rejected frame seek {index}")
        ok, frame = capture.read()
        if not ok:
            raise IndexError(index)
        return frame
    finally:
        capture.release()


def _opencv_dtype(path: Path) -> dict[str, Any]:
    array, _ = next(_opencv_frames(path, 1))
    return {"dtype": str(array.dtype), "pixel_format": "BGR"}


def _adapter(backend: str) -> tuple[Any, Any, Any]:
    return {
        "pyav": (_pyav_frames, _pyav_seek, _pyav_dtype),
        "decord": (_decord_frames, _decord_seek, _decord_dtype),
        "imageio-ffmpeg": (_imageio_frames, _imageio_seek, _imageio_dtype),
        "opencv-videocapture": (_opencv_frames, _opencv_seek, _opencv_dtype),
    }[backend]


def _worker(backend: str, clip: Clip, decode_frames: int, seek_count: int) -> dict[str, Any]:
    sequential, seek, dtype_probe = _adapter(backend)
    result: dict[str, Any] = {
        "backend": backend,
        "clip": clip.label,
        "codec": clip.codec,
        "path": str(clip.path),
        "expected_bit_depth": clip.expected_bit_depth,
        "status": "ok",
    }

    # The timed/RSS pass performs decode and array conversion, but intentionally
    # excludes hashing and random seeks.
    decoded = 0
    started = time.perf_counter()
    with PeakRssSampler() as rss:
        for array, _position in sequential(clip.path, decode_frames):
            decoded += 1
            if array.size == 0:
                raise RuntimeError("Decoder returned an empty frame")
    elapsed = time.perf_counter() - started
    result.update(
        {
            "decoded_frames": decoded,
            "sequential_seconds": elapsed,
            "sequential_fps": decoded / elapsed if elapsed else None,
            "rss_baseline_mb": rss.baseline_bytes / MIB,
            "peak_rss_mb": rss.peak_bytes / MIB,
            "peak_rss_delta_mb": (rss.peak_bytes - rss.baseline_bytes) / MIB,
        }
    )

    hashes: list[str] = []
    positions: list[Any] = []
    for array, position in sequential(clip.path, decoded):
        hashes.append(_hash_pixels(array))
        positions.append(position)
    if len(hashes) != decoded:
        raise RuntimeError(f"Reference pass decoded {len(hashes)} of {decoded} frames")

    rng = random.Random(f"sieve-decoder-benchmark:{clip.label}")
    requested = sorted(rng.sample(range(decoded), min(seek_count, decoded)))
    mismatches: list[int] = []
    seek_errors: dict[str, str] = {}
    for index in requested:
        try:
            if _hash_pixels(seek(clip.path, positions, index)) != hashes[index]:
                mismatches.append(index)
        except Exception as exc:  # A failed request is a seek mismatch.
            mismatches.append(index)
            seek_errors[str(index)] = f"{type(exc).__name__}: {exc}"
    result.update(
        {
            "seek_requests": len(requested),
            "seek_mismatches": len(mismatches),
            "seek_mismatch_rate": len(mismatches) / len(requested) if requested else None,
            "mismatched_frames": mismatches,
            "seek_errors": seek_errors,
        }
    )

    dtype = dtype_probe(clip.path)
    preserves = (
        clip.expected_bit_depth <= 8
        or np.dtype(dtype["dtype"]).itemsize * 8 >= clip.expected_bit_depth
    )
    result.update(dtype)
    result["preserves_expected_bit_depth"] = preserves
    return result


def _distribution_closure(root_name: str) -> list[importlib.metadata.Distribution]:
    from packaging.requirements import Requirement

    pending = [root_name]
    found: dict[str, importlib.metadata.Distribution] = {}
    while pending:
        requested = pending.pop()
        distribution = importlib.metadata.distribution(requested)
        key = distribution.metadata["Name"].lower().replace("_", "-")
        if key in found:
            continue
        found[key] = distribution
        for raw_requirement in distribution.requires or []:
            requirement = Requirement(raw_requirement)
            if requirement.marker is None or requirement.marker.evaluate():
                pending.append(requirement.name)
    return list(found.values())


def _distribution_size(distribution: importlib.metadata.Distribution) -> int:
    total = 0
    for relative in distribution.files or []:
        path = distribution.locate_file(relative)
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            pass
    return total


def _footprints() -> dict[str, dict[str, Any]]:
    roots = {
        "pyav": "av",
        "decord": "decord",
        "imageio-ffmpeg": "imageio-ffmpeg",
        "opencv-videocapture": "opencv-python-headless",
    }
    results: dict[str, dict[str, Any]] = {}
    for backend, root in roots.items():
        distributions = _distribution_closure(root)
        root_distribution = importlib.metadata.distribution(root)
        results[backend] = {
            "package": root_distribution.metadata["Name"],
            "version": root_distribution.version,
            "package_size_mb": _distribution_size(root_distribution) / MIB,
            "installed_closure_size_mb": sum(
                _distribution_size(distribution) for distribution in distributions
            )
            / MIB,
            "transitive_dependency_count": len(distributions) - 1,
            "dependency_closure": sorted(
                distribution.metadata["Name"] for distribution in distributions
            ),
        }
    return results


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _write_report(
    path: Path,
    results: list[dict[str, Any]],
    footprints: dict[str, dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    failed_seek = {
        result["backend"]
        for result in results
        if result.get("status") != "ok" or result.get("seek_mismatches", 0) > 0
    }
    lines = [
        "# Decoder benchmark",
        "",
        (
            f"Native-resolution sequential decode of up to {args.decode_frames} frames per "
            f"clip; {args.seek_count} deterministic random frame requests per decoder/clip."
        ),
        "",
        (
            "A decoder is disqualified for preview extraction if any codec has a failed or "
            "pixel-mismatched random seek."
        ),
        "",
        "| Decoder | Codec | Seq fps | Seek mismatches | Mismatch % | Native dtype / format | Preserves depth | Peak RSS MB | Install MB (closure) | Transitive deps | Preview eligible |",
        "|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        backend = result["backend"]
        footprint = footprints[backend]
        if result.get("status") == "ok":
            dtype = f"{result['dtype']} / {result['pixel_format']}"
            mismatch = f"{result['seek_mismatches']}/{result['seek_requests']}"
        else:
            dtype = f"ERROR: {result.get('error', 'unknown error')}"
            mismatch = "failed"
        lines.append(
            "| {backend} | {codec} | {fps} | {mismatch} | {rate} | {dtype} | "
            "{depth} | {rss} | {size} | {deps} | {eligible} |".format(
                backend=backend,
                codec=result["codec"],
                fps=_fmt(result.get("sequential_fps")),
                mismatch=mismatch,
                rate=_fmt(
                    100 * result["seek_mismatch_rate"]
                    if result.get("seek_mismatch_rate") is not None
                    else None
                ),
                dtype=dtype,
                depth=_fmt(result.get("preserves_expected_bit_depth")),
                rss=_fmt(result.get("peak_rss_mb")),
                size=_fmt(footprint["installed_closure_size_mb"]),
                deps=footprint["transitive_dependency_count"],
                eligible="NO — DISQUALIFIED" if backend in failed_seek else "yes",
            )
        )
    lines.extend(["", "## Seek-accuracy decision", ""])
    for backend in BACKENDS:
        backend_results = [result for result in results if result["backend"] == backend]
        failures = [
            result["codec"]
            for result in backend_results
            if result.get("status") != "ok" or result.get("seek_mismatches", 0) > 0
        ]
        if failures:
            lines.append(
                f"- **{backend}: DISQUALIFIED** — failed seek accuracy on {', '.join(failures)}."
            )
        else:
            lines.append(f"- **{backend}: eligible** — no mismatches in this corpus/run.")
    lines.extend(
        [
            "",
            "## Measurement boundaries",
            "",
            "- Sequential throughput includes decode plus conversion to each adapter's normal array output; hashing and random seeks run in a separate pass.",
            "- Peak RSS is the maximum sampled worker-plus-child-process resident set during the sequential pass. The raw JSON also records baseline and peak delta.",
            "- Seek hashes compare each decoder with its own sequential output, avoiding false mismatches caused by different color-conversion implementations.",
            "- Dtype preservation probes the decoder's native/default array representation. Throughput and seek comparison use normal RGB/BGR preview arrays.",
            "- Install closure size is the on-disk size of the installed root distribution and its active runtime dependency closure in this virtual environment.",
            "",
            f"Raw data: `{path.with_name('results.json').name}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _worker_entry(args: argparse.Namespace) -> int:
    clip = Clip(
        label=args.worker_label,
        codec=args.worker_codec,
        path=args.worker_path.resolve(),
        expected_bit_depth=args.worker_bit_depth,
    )
    try:
        result = _worker(args.worker, clip, args.decode_frames, args.seek_count)
    except BaseException as exc:
        result = {
            "backend": args.worker,
            "clip": clip.label,
            "codec": clip.codec,
            "path": str(clip.path),
            "expected_bit_depth": clip.expected_bit_depth,
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    args.worker_result.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0 if result["status"] == "ok" else 1


def _controller(args: argparse.Namespace) -> int:
    if args.generate_corpus:
        _generate_corpus(args.corpus_dir, args.ffmpeg, args.corpus_frames)
    clips = read_manifest(args.corpus_dir)
    output = args.output or Path(
        f"tests/results/decoder-benchmark-{time.strftime('%Y%m%d-%H%M%S')}"
    )
    output.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for backend in args.backends:
        for clip in clips:
            result_path = output / f"{backend}-{clip.label}.json"
            command = [
                sys.executable,
                "-m",
                "sieve.bench.decoder_benchmark",
                "--worker",
                backend,
                "--worker-result",
                str(result_path),
                "--worker-label",
                clip.label,
                "--worker-codec",
                clip.codec,
                "--worker-path",
                str(clip.path),
                "--worker-bit-depth",
                str(clip.expected_bit_depth),
                "--decode-frames",
                str(args.decode_frames),
                "--seek-count",
                str(args.seek_count),
            ]
            print(f"Benchmarking {backend} / {clip.codec} ...", flush=True)
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                check=False,
            )
            (output / f"{backend}-{clip.label}.log").write_text(
                f"COMMAND: {subprocess.list2cmdline(command)}\n"
                f"EXIT CODE: {completed.returncode}\n\n"
                f"STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}",
                encoding="utf-8",
            )
            if result_path.exists():
                result = json.loads(result_path.read_text(encoding="utf-8"))
            else:
                result = {
                    "backend": backend,
                    "clip": clip.label,
                    "codec": clip.codec,
                    "status": "error",
                    "error": "Worker produced no result",
                }
            results.append(result)
            print(
                f"  {result['status']}: {result.get('sequential_fps', 'n/a')} fps; "
                f"seek mismatches={result.get('seek_mismatches', 'n/a')}"
            )

    footprints = _footprints()
    combined = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "config": {
            "corpus_dir": str(args.corpus_dir.resolve()),
            "decode_frames": args.decode_frames,
            "seek_count": args.seek_count,
        },
        "footprints": footprints,
        "results": results,
    }
    (output / "results.json").write_text(json.dumps(combined, indent=2), encoding="utf-8")
    _write_report(output / "README.md", results, footprints, args)
    print(f"Report: {(output / 'README.md').resolve()}")
    return 0 if all(result.get("status") == "ok" for result in results) else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--generate-corpus", action="store_true")
    parser.add_argument("--corpus-frames", type=int, default=1000)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--decode-frames", type=int, default=1000)
    parser.add_argument("--seek-count", type=int, default=40)
    parser.add_argument("--backends", nargs="+", choices=BACKENDS, default=list(BACKENDS))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--worker", choices=BACKENDS, help=argparse.SUPPRESS)
    parser.add_argument("--worker-result", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-label", help=argparse.SUPPRESS)
    parser.add_argument("--worker-codec", help=argparse.SUPPRESS)
    parser.add_argument("--worker-path", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-bit-depth", type=int, help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.decode_frames <= 0 or args.corpus_frames <= 0 or args.seek_count <= 0:
        raise SystemExit("frame and seek counts must be positive")
    if args.worker:
        required = (
            args.worker_result,
            args.worker_label,
            args.worker_codec,
            args.worker_path,
            args.worker_bit_depth,
        )
        if any(value is None for value in required):
            raise SystemExit("Incomplete worker arguments")
        return _worker_entry(args)
    return _controller(args)


if __name__ == "__main__":
    raise SystemExit(main())
