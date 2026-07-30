"""The stderr filter drops one line and loses nothing else.

Run in subprocesses, and they are the only honest way to test this: the thing
under test takes file descriptor 2 for the life of a process, and pytest's own
capture owns fd 2 in this one. A test that installed the filter in-process would
be asserting against the fixture it had just displaced.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

#: Composed as a list of flush-left lines rather than a dedented block, because
#: these scripts are assembled from pieces and any indentation that survives
#: interpolation is an `IndentationError` in the child — which fails the test
#: for a reason that has nothing to do with the filter.
INSTALL = (
    "import sys",
    "from sieve.decode.quiet import silence_raw_format_warning",
    "assert silence_raw_format_warning()",
)

#: One line of exactly what this build's FFmpeg backend emits per frame.
NOISE = (
    "import sys",
    'sys.stderr.write("[ WARN:0@87.958] global cap_ffmpeg_impl.hpp:1889 retrieveFrame '
    'Unknown/unsupported picture format: yuv420p, will be treated as 8UC1.\\n")',
)


def run(*lines: str) -> subprocess.CompletedProcess[str]:
    """Execute `lines` in a fresh interpreter and hand back what it said."""
    return subprocess.run(
        [sys.executable, "-c", "\n".join(lines)],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120,
        check=False,
    )


class TestFilter:
    def test_the_known_line_is_dropped(self) -> None:
        assert "8UC1" not in run(*INSTALL, *NOISE).stderr

    def test_everything_else_survives_in_order(self) -> None:
        """The line filter's whole claim: it is a filter, not a mute.

        Order matters as much as presence — the pump is a second thread, and one
        that reordered or coalesced lines would still pass a presence check while
        making the console lie about what happened when.
        """
        result = run(
            *INSTALL,
            'print("first", file=sys.stderr)',
            *NOISE,
            'print("second", file=sys.stderr)',
        )
        assert "8UC1" not in result.stderr
        assert [line for line in result.stderr.splitlines() if line.strip()] == [
            "first",
            "second",
        ]

    def test_a_traceback_survives(self) -> None:
        """The case the filter must not cost anything: the process is dying.

        A daemon pump killed at interpreter shutdown would swallow exactly this,
        which is why `_restore` flushes, closes the write end, and joins.
        """
        result = run(*INSTALL, 'raise RuntimeError("must reach the console")')
        assert result.returncode != 0
        assert "must reach the console" in result.stderr
        assert "Traceback" in result.stderr

    def test_installing_twice_is_a_no_op(self) -> None:
        """Idempotent, because two pumps on one fd would each see half the lines."""
        result = run(*INSTALL, *INSTALL, 'print("survivor", file=sys.stderr)', *NOISE)
        assert "8UC1" not in result.stderr
        assert "survivor" in result.stderr

    def test_an_unrelated_opencv_warning_is_kept(self) -> None:
        """Narrow on purpose: a different fallback is something to see.

        The pattern is anchored on `retrieveFrame` and the 8UC1 fallback
        together, so a warning about a format this reader has never been
        measured against still reaches the console.
        """
        result = run(
            *INSTALL,
            "import sys",
            'sys.stderr.write("[ WARN:0@1.0] global cap.cpp:217 cv::VideoCapture::open '
            'VIDEOIO(DSHOW): backend is generally available\\n")',
        )
        assert "DSHOW" in result.stderr


@pytest.mark.slow
class TestAgainstTheDecoder:
    def test_a_luma_read_of_real_footage_is_quiet(self) -> None:
        """The whole point, against the source that produces the line.

        Skipped rather than failed without the reference footage: this asserts
        about a message only this build's FFmpeg backend emits, and a checkout
        without `videos-testing/` cannot produce it either way.
        """
        footage = REPO / "videos-testing" / "stab_GX010050c2_02_18_26.MP4"
        if not footage.is_file():
            pytest.skip("reference footage is not in this checkout")

        result = run(
            *INSTALL,
            "from sieve.decode.reader import VideoReader",
            f'reader = VideoReader(r"{footage}", luma=True)',
            "[reader.read(index) for index in range(20)]",
            "reader.close()",
        )
        assert result.returncode == 0, result.stderr
        assert "8UC1" not in result.stderr
