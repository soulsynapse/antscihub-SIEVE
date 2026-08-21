"""Random access: frame-accurate seek against grab-forward, by jump distance.

The coalescer, the scrub policy, the request intents and the proxy cache all
defend a seek budget measured through OpenCV 4.13. This measures the budget:
what a jump of d frames costs by seeking against stepping, per backend. Jumps
are chained — each starts where the last landed — so no untimed repositioning
pollutes the interval. The deliverable is the crossover distance below which
stepping wins, which is the number a scrub policy actually needs.

Jumps are denominated in frame indices here and converted to pts with exact
Fraction arithmetic; whether SIEVE identifies frames by pts or index is an
open decision this experiment does not take. A landing that missed its target
is counted and said in the case note, because a fast seek that lands on the
wrong frame is not a seek.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import av
import cv2

from harness import FOOTAGE, Run, report, time_case

JUMPS = 15  # per case, before the harness discards its warm-up

FORWARD_BOTH = {"big": (1, 2, 5, 10, 25, 50, 100), "small": (1, 5, 10, 25, 50, 100, 250, 1000)}
SEEK_ONLY = {"big": (250, 1000, -25, -250), "small": (5000, -100, -1000)}
START_FWD = {"big": 1000, "small": 2000}
START_BACK = {"big": 9000, "small": 25000}


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)  # pts per frame, exact
    return (lambda i: base + int(step * i)), step


def pyav_seek(path: Path, d: int, start: int, n: int,
              thread_count: int = 0, hwaccel: str | None = None):
    def work():
        opts = {}
        if hwaccel:
            from av.codec.hwaccel import HWAccel

            opts["hwaccel"] = HWAccel(device_type=hwaccel,
                                      allow_software_fallback=False)
        with av.open(str(path), **opts) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            stream.codec_context.thread_count = thread_count
            pts_of, step = _pts_helpers(stream)
            half = step / 2
            pos = start
            misses = 0
            yield "open"
            for _ in range(n):
                pos += d
                target = pts_of(pos)
                container.seek(target, stream=stream)
                for frame in container.decode(stream):
                    if frame.pts is not None and frame.pts + half >= target:
                        if abs(frame.pts - target) > half:
                            misses += 1
                        break
                yield True
        work.misses = misses

    return work


def pyav_step(path: Path, d: int, start: int, n: int):
    def work():
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            pts_of, step = _pts_helpers(stream)
            target = pts_of(start)
            container.seek(target, stream=stream)
            decoded = container.decode(stream)
            for frame in decoded:  # roll to start, untimed
                if frame.pts is not None and frame.pts + step / 2 >= target:
                    break
            yield "open"
            try:
                for _ in range(n):
                    for _ in range(d):
                        next(decoded)
                    yield True
            except StopIteration:
                return
        work.misses = 0

    return work


def cv2_seek(path: Path, d: int, start: int, n: int):
    def work():
        cap = cv2.VideoCapture(str(path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        cap.grab()
        pos, misses = start, 0
        yield "open"
        for _ in range(n):
            pos += d
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            if not cap.grab():
                break
            if cap.get(cv2.CAP_PROP_POS_FRAMES) != pos + 1:
                misses += 1
            yield True
        cap.release()
        work.misses = misses

    return work


def cv2_step(path: Path, d: int, start: int, n: int):
    def work():
        cap = cv2.VideoCapture(str(path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        cap.grab()
        yield "open"
        for _ in range(n):
            ok = True
            for _ in range(d):
                ok = cap.grab()
                if not ok:
                    break
            if not ok:
                break
            yield True
        cap.release()
        work.misses = 0

    return work


def n_for(start: int, d: int, limit: int) -> int:
    room = (limit - 50 - start) // d if d > 0 else (start - 50) // -d
    return max(4, min(JUMPS, room))


def measure(run: Run, path: Path, tag: str) -> None:
    with av.open(str(path)) as c:
        limit = c.streams.video[0].frames
    backends = {"pyav": (pyav_seek, pyav_step), "cv2": (cv2_seek, cv2_step)}
    for backend, (seek_fn, step_fn) in backends.items():
        for d in FORWARD_BOTH[tag]:
            for method, fn in (("seek", seek_fn), ("step", step_fn)):
                start = START_FWD[tag]
                n = n_for(start, d, limit)
                work = fn(path, d, start, n)
                case = time_case(
                    run, f"{tag}/{backend}/{method}/d={d}", work,
                    params={"backend": backend, "method": method,
                            "distance": d, "file": path.name},
                    unit="ms per jump",
                )
                misses = getattr(work, "misses", None)
                if misses:
                    case.note = f"{misses} jumps landed off-target"
        for d in SEEK_ONLY[tag]:
            start = START_FWD[tag] if d > 0 else START_BACK[tag]
            n = n_for(start, d, limit)
            work = seek_fn(path, d, start, n)
            case = time_case(
                run, f"{tag}/{backend}/seek/d={d}", work,
                params={"backend": backend, "method": "seek",
                        "distance": d, "file": path.name},
                unit="ms per jump",
            )
            misses = getattr(work, "misses", None)
            if misses:
                case.note = f"{misses} jumps landed off-target"


def seek_threads(run: Run, path: Path) -> None:
    """Seek cost against decoder threads, plus hardware: after every seek the
    frame-threaded decoder refills a pipeline thread_count frames deep before
    the first frame comes out, so the throughput winner and the latency winner
    need not be the same configuration."""
    for tc in (1, 2, 4, 16):
        work = pyav_seek(path, 25, 1000, JUMPS, thread_count=tc)
        time_case(
            run, f"big/pyav/seek/d=25/threads={tc}", work,
            params={"backend": "pyav", "method": "seek", "distance": 25,
                    "thread_count": tc, "file": path.name},
            unit="ms per jump",
        )
    for device in ("cuda", "d3d11va"):
        work = pyav_seek(path, 25, 1000, JUMPS, hwaccel=device)
        try:
            time_case(
                run, f"big/pyav/seek/d=25/hw={device}", work,
                params={"backend": "pyav", "method": "seek", "distance": 25,
                        "hwaccel": device, "file": path.name},
                unit="ms per jump",
            )
        except Exception as exc:  # noqa: BLE001 - absence is the datum
            run.note(f"seek hw={device} did not run: {exc!r}")


def main() -> None:
    run = Run(
        experiment="02-random-access",
        question=(
            "What does a jump of d frames cost, seeking against stepping, per "
            "backend — and where is the crossover the scrub policy would need?"
        ),
    )
    big = FOOTAGE / "GX010047c2_02_17_26.MP4"
    small = FOOTAGE / "rep3_intermittent_crop.MP4"
    run.add_footage(big, small)
    run.note(
        "Jumps are chained (each starts at the previous landing), so seek "
        "targets walk the file rather than resampling one region."
    )
    run.note(
        "pyav seek is frame-accurate: seek to keyframe, decode forward to the "
        "target pts. cv2's CAP_PROP_POS_FRAMES does its own equivalent "
        "internally; off-target landings are counted per case."
    )
    measure(run, big, "big")
    measure(run, small, "small")
    seek_threads(run, big)
    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()
