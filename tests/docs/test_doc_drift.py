"""The one line `nox -s docs` prints says the same thing as the report.

The full report moved to its own session because forty lines printed after
every completed item are read once and skipped thereafter. What `docs` keeps
is a count — and a count is only worth keeping if it is the count of the list
`nox -s drift` would show. If the two can disagree, the quiet line becomes the
thing that gets ignored instead.
"""

from __future__ import annotations

import pytest

import doc_drift


def test_the_summary_is_one_line(capsys: pytest.CaptureFixture[str]) -> None:
    assert doc_drift.main(["--summary"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 1


def test_the_summary_counts_what_the_report_lists() -> None:
    summary, full = doc_drift.report()
    docs_listed = sum(
        1 for line in full if "commits touched its subjects" in line or "cannot assess" in line
    )
    findings_listed = sum(1 for line in full if "commits touched its files" in line)
    assert f"{docs_listed} docs and {findings_listed} findings" in summary


def test_the_bare_run_still_prints_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert doc_drift.main([]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("doc_drift: prose docs")
    assert any("findings whose measured files moved" in line for line in out)
