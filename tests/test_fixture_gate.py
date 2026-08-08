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

# A fixture the gate does not guard, skipping where the gate can see it — in
# setup rather than in the call phase, which `pytest_fixture_setup` is never
# handed.
_UNGUARDED_SKIP = """
import pytest


@pytest.fixture
def a_fixture_the_gate_does_not_guard():
    pytest.skip("an excused fixture, outside FATAL_FIXTURE_SKIPS")
"""


def _nested_run(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    conftest_tail: str,
    body: str,
) -> pytest.RunResult:
    # `Pytester.run` reads the child's captured output as utf-8 while the child
    # picks its stdout encoding from the locale — cp1252 on a bare Windows
    # shell. The two agree only by coincidence, and the coincidence holds until
    # a traceback quotes a source line above 0x7f: `stirred_clip`'s docstring
    # has an em dash in it. Pinning the child is the only half of that pair we
    # control
    # (`docs/findings/loop/2026.08.07-a-nested-pytest-session-is-decoded-as-utf-8-and-only-the-harness-env-makes-that-true.md`).
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    pytester.makeconftest(_CONFTEST.format(root=str(REPO_ROOT)) + conftest_tail)
    pytester.makepyfile(body)
    return pytester.runpytest_subprocess()


def test_skipping_synthetic_video_fails_the_run(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _nested_run(
        pytester,
        monkeypatch,
        _NO_ENCODER,
        """
        def test_wants_the_fixture(synthetic_video):
            assert synthetic_video.exists()
        """,
    )

    assert result.ret != 0
    result.assert_outcomes(errors=1, skipped=0, passed=0)


def test_skipping_stirred_clip_fails_the_run(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _nested_run(
        pytester,
        monkeypatch,
        _NO_ENCODER,
        """
        def test_wants_the_fixture(stirred_clip):
            assert stirred_clip.exists()
        """,
    )

    assert result.ret != 0
    result.assert_outcomes(errors=1, skipped=0, passed=0)


def test_a_run_with_no_fixture_skip_stays_green(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control: a gate that failed every run would satisfy the two above."""
    result = _nested_run(
        pytester,
        monkeypatch,
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


def test_an_unguarded_fixture_skip_stays_a_skip(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other direction: the gate is narrow, not merely present.

    The control above skips by mark, in the call phase, which
    `pytest_fixture_setup` never sees — so it leaves the gate's membership test
    free to be deleted outright
    (`docs/findings/loop/2026.08.07-a-control-that-skips-by-mark-cannot-see-a-hook-that-only-watches-fixtures.md`).
    This one enters the hook and has to come back out of it still a skip.
    """
    result = _nested_run(
        pytester,
        monkeypatch,
        _UNGUARDED_SKIP,
        """
        def test_wants_the_fixture(a_fixture_the_gate_does_not_guard):
            raise AssertionError
        """,
    )

    assert result.ret == 0
    result.assert_outcomes(skipped=1, errors=0, failed=0, passed=0)


def test_the_nested_runner_overrides_the_parents_encoding(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_nested_run` overrides the child's text encoding rather than inheriting it.

    The parent is given a codec the assertion below fails under, rather than
    none: a child that merely clears the variable falls back to the
    interpreter's default, which is already utf-8 on the Linux runner that
    gates a merge, so the cleared version distinguishes nothing there
    (`docs/findings/loop/2026.08.07-a-test-that-clears-an-environment-variable-is-vacuous-where-the-platform-default-already-agrees.md`).
    An inherited latin-1 is wrong on every platform.

    `sys.__stdout__` rather than `sys.stdout`: pytest's capture replaces the
    latter with a utf-8 file whatever the interpreter chose, so only the
    startup object still reports what the child was told.
    """
    monkeypatch.setenv("PYTHONIOENCODING", "latin-1")
    result = _nested_run(
        pytester,
        monkeypatch,
        "",
        """
        import codecs
        import sys


        def test_the_child_writes_utf_8():
            assert codecs.lookup(sys.__stdout__.encoding).name == "utf-8"
        """,
    )

    assert result.ret == 0
    result.assert_outcomes(passed=1)
