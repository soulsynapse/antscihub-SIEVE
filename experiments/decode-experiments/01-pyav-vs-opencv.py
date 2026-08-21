"""Does the inherited OpenCV sequential-decode corpus survive a binding change?

Every decode number this tree inherited was taken through OpenCV 4.13: the
colour conversion costing more than the decode, the grab/retrieve split being
worth taking, threading that was not worth tuning because the binding owned it.
This experiment decodes the same files sequentially through OpenCV and PyAV and
splits each backend at the same joints — decode alone, decode plus luma, decode
plus BGR — so a difference is attributable to the joint and not the backend's
defaults.

Two deliberate fairness moves, both of which a naive comparison gets wrong:

- OpenCV's FFmpeg backend threads the decode on its own; PyAV's default
  `thread_type` is NONE. Comparing those defaults measures a configuration, not
  a binding, so PyAV runs both unthreaded and AUTO.
- PyAV's luma case is a numpy *view* over `planes[0]` with the stride handled,
  not `to_ndarray(format='gray')` — the latter is an swscale convert-and-copy,
  which is the very cost the luma path exists to avoid. A consumer that needs
  contiguous memory pays one memcpy on top; that is its cost to measure.

Both files run: the 5.3K HEVC source and the small H.264 clip bracket the
product's two regimes (pre-cut and post-cut), and per-frame fixed overheads
plausibly flip the ranking between them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import av
import cv2
import numpy as np

# The raw case makes cv2's FFmpeg wrapper warn once per frame; the shape it
# returned is recorded in the case note, which is the part that matters.
cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)

from harness import FOOTAGE, Run, report, time_case

#: Frames measured per case, chosen by how much a frame costs, so the big file
#: does not take an hour and the small one still yields a stable p50.
BIG, SMALL = 300, 1500


def cv2_case(path: Path, frames: int, mode: str):
    """mode: 'grab' (decode only), 'read' (grab+retrieve BGR), 'raw'
    (CONVERT_RGB=0 — whatever the backend actually returns is recorded)."""

    def work():
        cap = cv2.VideoCapture(str(path))
        if mode == "raw":
            cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        yield "open"
        shape = None
        for _ in range(frames):
            if not cap.grab():
                break
            if mode != "grab":
                ok, img = cap.retrieve()
                if not ok:
                    break
                shape = getattr(img, "shape", None)
            yield True
        cap.release()
        work.shape = shape  # read by the caller for the case note

    return work


def pyav_case(path: Path, frames: int, threads: str, convert: str):
    """threads: 'NONE' or 'AUTO'.
    convert: 'none', 'luma_view', 'bgr24', 'bgr24_cached'.

    'bgr24' is `to_ndarray`, which builds a fresh swscale context per call;
    'bgr24_cached' reuses one `VideoReformatter`, so the pair separates the
    conversion from the API's per-call setup — a cost that dominates exactly
    when frames are small."""

    def work():
        from av.video.reformatter import VideoReformatter

        reformatter = VideoReformatter()
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = threads
            decoded = container.decode(stream)
            yield "open"
            for index, frame in enumerate(decoded):
                if index >= frames:
                    break
                if convert == "luma_view":
                    plane = frame.planes[0]
                    arr = np.frombuffer(plane, dtype=np.uint8)
                    arr = arr[: frame.height * plane.line_size]
                    arr = arr.reshape(frame.height, plane.line_size)
                    arr = arr[:, : frame.width]
                    arr[0, 0]  # touch, so a lazy path cannot hide
                elif convert == "bgr24":
                    frame.to_ndarray(format="bgr24")
                elif convert == "bgr24_cached":
                    reformatter.reformat(frame, format="bgr24").to_ndarray()
                yield True

    return work


def measure(run: Run, path: Path, frames: int) -> None:
    tag = path.stem.split("_")[0]

    for mode in ("grab", "read", "raw"):
        work = cv2_case(path, frames, mode)
        case = time_case(
            run, f"{tag}/cv2/{mode}", work,
            params={"backend": "cv2", "mode": mode, "file": path.name},
        )
        shape = getattr(work, "shape", None)
        if mode != "grab":
            case.note = f"retrieve returned shape {shape}"

    for threads in ("NONE", "AUTO"):
        for convert in ("none", "luma_view", "bgr24", "bgr24_cached"):
            time_case(
                run,
                f"{tag}/pyav/threads={threads}/{convert}",
                pyav_case(path, frames, threads, convert),
                params={
                    "backend": "pyav", "thread_type": threads,
                    "convert": convert, "file": path.name,
                },
            )


def main() -> None:
    run = Run(
        experiment="01-pyav-vs-opencv",
        question=(
            "Do the inherited OpenCV sequential-decode numbers — conversion "
            "dwarfing decode, the grab/retrieve split, the threading ceiling — "
            "survive a change of binding?"
        ),
    )
    big = FOOTAGE / "GX010047c2_02_17_26.MP4"
    small = FOOTAGE / "rep3_intermittent_crop.MP4"
    for path in (big, small):
        if not path.exists():
            run.note(f"{path.name} absent; its cases did not run.")
    run.add_footage(*(p for p in (big, small) if p.exists()))
    run.note(
        "cv2 threads its FFmpeg decode by default and exposes no equivalent "
        "of thread_type=NONE here, so cv2 cases are compared against "
        "pyav/AUTO; pyav/NONE exists to price the threading itself."
    )
    run.note(
        "pyav luma_view is a stride-aware numpy view over planes[0], not "
        "to_ndarray('gray'); a consumer needing contiguous memory adds one "
        "memcpy not measured here."
    )

    if big.exists():
        measure(run, big, BIG)
    if small.exists():
        measure(run, small, SMALL)

    for case in run.cases:
        report(case)
    out = run.write()
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
