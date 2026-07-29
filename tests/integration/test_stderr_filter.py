







from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]





INSTALL = (
    "import sys",
    "from sieve.decode.quiet import silence_raw_format_warning",
    "assert silence_raw_format_warning()",
)


NOISE = (
    "import sys",
    'sys.stderr.write("[ WARN:0@87.958] global cap_ffmpeg_impl.hpp:1889 retrieveFrame '
    'Unknown/unsupported picture format: yuv420p, will be treated as 8UC1.\\n")',
)


def run(*lines: str) -> subprocess.CompletedProcess[str]:

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





        result = run(*INSTALL, 'raise RuntimeError("must reach the console")')
        assert result.returncode != 0
        assert "must reach the console" in result.stderr
        assert "Traceback" in result.stderr

    def test_installing_twice_is_a_no_op(self) -> None:

        result = run(*INSTALL, *INSTALL, 'print("survivor", file=sys.stderr)', *NOISE)
        assert "8UC1" not in result.stderr
        assert "survivor" in result.stderr

    def test_an_unrelated_opencv_warning_is_kept(self) -> None:






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
