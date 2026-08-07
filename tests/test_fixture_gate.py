"""A run that could not build a video fixture is not a run that passed.

`conftest.py`'s two fixtures skip when OpenCV has no mp4v encoder, and that
line ports verbatim by decision — so the correction lives in the gate around
them rather than in the fixture. The subject here is the conftest module beside
this file, not anything under `src/sieve`, which is why this is not under
`unit/`.

Each case runs a whole nested pytest session, because what is under test is a
session's exit code and no assertion inside one session can observe another's.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The nested session gets the real fixtures and the real gate by importing the
# module under test, rather than a copy that could drift from it.
_CONFTEST = """
import sys

sys.path.insert(0, {root!r})

from tests.conftest import *  # noqa: F401,F403
"""

# An OpenCV build with no usable mp4v encoder, which is the condition the
# fixtures' `isOpened()` branch exists for and which no runner in play can be
# put into for real.
_NO_ENCODER = """
import cv2


class _DeadWriter:
    fourcc = staticmethod(cv2.VideoWriter.fourcc)

    def __init__(self, *args, **kwargs):
        pass

    def isOpened(self):
        return False


cv2.VideoWriter = _DeadWriter
"""


def _nested_run(pytester: pytest.Pytester, conftest_tail: str, body: str) -> pytest.RunResult:
    pytester.makeconftest(_CONFTEST.format(root=str(REPO_ROOT)) + conftest_tail)
    pytester.makepyfile(body)
    return pytester.runpytest_subprocess()


def test_skipping_synthetic_video_fails_the_run(pytester: pytest.Pytester) -> None:
    result = _nested_run(
        pytester,
        _NO_ENCODER,
        """
        def test_wants_the_fixture(synthetic_video):
            assert synthetic_video.exists()
        """,
    )

    assert result.ret != 0
    result.assert_outcomes(errors=1, skipped=0, passed=0)


def test_skipping_stirred_clip_fails_the_run(pytester: pytest.Pytester) -> None:
    result = _nested_run(
        pytester,
        _NO_ENCODER,
        """
        def test_wants_the_fixture(stirred_clip):
            assert stirred_clip.exists()
        """,
    )

    assert result.ret != 0
    result.assert_outcomes(errors=1, skipped=0, passed=0)


def test_a_run_with_no_fixture_skip_stays_green(pytester: pytest.Pytester) -> None:
    """The control: a gate that failed every run would satisfy the two above."""
    result = _nested_run(
        pytester,
        "",
        """
        import pytest


        def test_wants_the_fixture(synthetic_video):
            assert synthetic_video.exists()


        @pytest.mark.skip(reason="an ordinary skip, unrelated to any fixture")
        def test_skips_for_its_own_reasons():
            raise AssertionError
        """,
    )

    assert result.ret == 0
    result.assert_outcomes(passed=1, skipped=1, errors=0)
