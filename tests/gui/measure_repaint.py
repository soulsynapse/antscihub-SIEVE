"""Measure repaint cost through `VideoViewer._paint`, not a pytest test.

The scrub-seek budget in `sieve.bench.budgets` covers seek, decode, color
conversion, and widget repaint; `tests/bench/test_decode_seek.py` measures
only the first two, through the pinned decode boundary. This measures the
rest: the BGR-to-QImage wrap, the aspect-preserving scale, and
`QLabel.setPixmap`, against real decoded frames. It needs PySide6, so it
cannot live in `tests/bench/` -- `nox -s benchmark` installs the headless
`dev` extra by design (NOTES.md), and folding a Qt-requiring measurement into
that session's collection would break it there.

`DECODE_SHARE` in `test_decode_seek.py` is set from a run of this script; the
comment at that constant records when and against what. Re-run and update
both if `VideoViewer._paint`'s shape changes.

Example
-------
    python tests/gui/measure_repaint.py tests/fixtures/decoder-corpus/h264_8bit.mp4
"""

from __future__ import annotations

import random
import statistics
import sys
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sieve.gui.panels.video_viewer import VideoViewer
from sieve.io.video_read import VideoReader

SAMPLE = 64
_EXPECTED_ARGC = 2


def main(clip_path: Path) -> None:
    app = QApplication(sys.argv[:1])
    viewer = VideoViewer()
    viewer.resize(960, 540)  # A representative window size, not maximized.
    viewer.show()

    reader = VideoReader(clip_path)
    total = reader.info.frame_count
    if total is None:
        raise SystemExit(f"{clip_path} reports no frame count; nothing to sample.")
    rng = random.Random("sieve-repaint-measurement")
    targets = rng.sample(range(total), min(SAMPLE, total))
    frames = [reader.read(index) for index in targets]
    reader.close()

    samples_ms = []
    for frame in frames:
        start = time.perf_counter()
        viewer._paint(frame)  # measuring the private repaint path directly
        app.processEvents()
        samples_ms.append((time.perf_counter() - start) * 1000.0)

    print(
        f"n={len(samples_ms)} "
        f"median={statistics.median(samples_ms):.3f}ms "
        f"mean={statistics.mean(samples_ms):.3f}ms "
        f"min={min(samples_ms):.3f}ms "
        f"max={max(samples_ms):.3f}ms"
    )


if __name__ == "__main__":
    if len(sys.argv) != _EXPECTED_ARGC:
        raise SystemExit(f"usage: python {sys.argv[0]} <clip-path>")
    main(Path(sys.argv[1]))
