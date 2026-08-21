"""Does the analysis compute dominate decode? Price the v1/v2-shaped ops per regime.

SIEVE exists to redo what v1/v2 did: per-frame image ops (differencing,
background subtraction, optical flow) reduced to time series, and spectral
ops (continuous Morlet wavelet) over those series. Decode costs are already
on the shelf (results/01-, 05-); this measures the other half on the same
footage, in the three regimes the pipeline actually has — the small post-cut
clip, the 1024^2 cut of the 5.3K source, and the uncut 5.3K frame — so the
comparison "does compute dominate decode" is per regime, not global.

The CWT is measured over a series, not per pixel, because that is what the
reduction step feeds it: its unit is ms per whole transform (64 scales, FFT
convolution), with per-sample cost derivable. A per-pixel spatiotemporal
wavelet would be a different animal by four orders of magnitude, and if that
is ever wanted it must be priced separately, not extrapolated from this.
"""

from __future__ import annotations

from pathlib import Path

import av
import cv2
import numpy as np

from harness import FOOTAGE, Run, report, time_case

SOURCES = [
    ("small", FOOTAGE / "rep3_intermittent_crop.MP4", 300),
    ("cut1024", FOOTAGE / "derived" / "cut-crf18-intra.mp4", 300),
    ("big", FOOTAGE / "GX010047c2_02_17_26.MP4", 32),
]
SERIES_LENGTHS = (11328, 30579)  # the two files' frame counts
N_SCALES = 64


def load_luma(path: Path, count: int) -> list[np.ndarray]:
    frames = []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for index, frame in enumerate(container.decode(stream)):
            if index >= count:
                break
            plane = frame.planes[0]
            arr = np.frombuffer(plane, dtype=np.uint8)
            arr = arr[: frame.height * plane.line_size]
            arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
            frames.append(np.ascontiguousarray(arr))
    return frames


def pairs_op(frames: list[np.ndarray], op):
    """One unit of work per consecutive frame pair, decode already paid."""

    def work():
        yield "ready"
        for prev, cur in zip(frames, frames[1:]):
            op(prev, cur)
            yield True

    return work


def image_ops(run: Run, tag: str, frames: list[np.ndarray]) -> None:
    h, w = frames[0].shape
    mean_frame = np.mean(np.stack(frames[: min(16, len(frames))]), axis=0)
    mean_u8 = mean_frame.astype(np.uint8)

    dis_fast = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
    dis_med = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ops = {
        "absdiff": lambda p, c: cv2.absdiff(p, c),
        "gaussian5": lambda p, c: cv2.GaussianBlur(c, (5, 5), 0),
        "bgsub+count": lambda p, c: cv2.countNonZero(
            cv2.threshold(cv2.absdiff(c, mean_u8), 25, 255,
                          cv2.THRESH_BINARY)[1]),
        "farneback-flow": lambda p, c: cv2.calcOpticalFlowFarneback(
            p, c, None, 0.5, 3, 15, 3, 5, 1.2, 0),
        "farneback-halfres": lambda p, c: cv2.calcOpticalFlowFarneback(
            cv2.pyrDown(p), cv2.pyrDown(c), None, 0.5, 3, 15, 3, 5, 1.2, 0),
        "dis-ultrafast": lambda p, c: dis_fast.calc(p, c, None),
        "dis-medium": lambda p, c: dis_med.calc(p, c, None),
        "reduce-mean": lambda p, c: float(np.mean(c)),
    }
    for name, op in ops.items():
        time_case(
            run, f"{tag}/{name}", pairs_op(frames, op),
            params={"file": tag, "width": w, "height": h, "op": name},
            warmup=2,
        )


def morlet_cwt(series: np.ndarray, scales: np.ndarray, w0: float = 6.0,
               pad: bool = True):
    """FFT-convolution Morlet CWT; pad=True rounds up to a power of two.

    The padding is not an optimisation flourish: an awkward series length
    (30579 = 3 x 10193, prime) sends numpy down its Bluestein path and the
    same transform costs an order of magnitude more. Both variants are
    measured so that fact sits in the results rather than in a comment."""
    n = len(series)
    nfft = 1 << (n - 1).bit_length() if pad else n
    spectrum = np.fft.rfft(series, nfft)
    omega = 2.0 * np.pi * np.fft.rfftfreq(nfft)
    power = np.empty((len(scales), n))
    for row, scale in enumerate(scales):
        psi = (np.pi ** -0.25) * np.sqrt(scale) * np.exp(
            -0.5 * (scale * omega - w0) ** 2)
        power[row] = np.abs(np.fft.irfft(spectrum * psi, nfft))[:n]
    return power


def cwt_cases(run: Run) -> None:
    rng = np.random.default_rng(7)
    for length in SERIES_LENGTHS:
        series = rng.standard_normal(length)
        # periods from ~0.1 s to ~60 s of behaviour at these frame rates
        scales = np.geomspace(2, length / 8, N_SCALES)
        for pad in (True, False):
            def work(series=series, scales=scales, pad=pad):
                yield "ready"
                for _ in range(12):
                    morlet_cwt(series, scales, pad=pad)
                    yield True

            case = time_case(
                run, f"cwt/morlet-{length}" + ("-padded" if pad else "-raw"),
                work,
                params={"samples": length, "scales": N_SCALES, "padded": pad},
                warmup=2, unit="ms per whole transform",
            )
            if case.samples_ms:
                per_sample_us = 1000 * (
                    sorted(case.samples_ms)[len(case.samples_ms) // 2] / length)
                case.note = (
                    f"~{per_sample_us:.2f} us per sample per 64-scale transform")


def main() -> None:
    run = Run(
        experiment="06-analysis-costs",
        question=(
            "Do the v1/v2-shaped analysis ops (frame ops per regime, Morlet "
            "CWT over series) dominate the decode costs already measured?"
        ),
    )
    run.note(
        "Frames are decoded up front and ops timed over consecutive pairs, "
        "so these are pure compute costs; add the shelf's decode numbers "
        "per regime to get the pipeline's frame budget."
    )
    for tag, path, count in SOURCES:
        if not path.exists():
            run.note(f"{tag}: {path.name} absent; cases did not run")
            continue
        run.add_footage(path)
        image_ops(run, tag, load_luma(path, count))
    cwt_cases(run)
    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()
