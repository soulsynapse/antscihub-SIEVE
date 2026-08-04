"""The condensed ledger is a promise that a number cannot go back up.

`CONDENSED` relaxes the prose cap to whatever a condensing run actually reached,
which is the whole point of having the state -- a file taken from 1,871 words to
404 against a 400 cap has done the work, and calling that a failure is what made
an earlier sweep revert 19 files to the bloat it found. But a relaxed cap that
nothing checks is an amnesty: the file leaves the queue, its ceiling is a comment
nobody runs, and the next edit that adds three paragraphs is invisible.

So the ratchet is the load-bearing claim, and these tests are what make it
binding. The gate has to fail when a condensed file grows past its own number,
and it has to keep failing on the structural half -- one module docstring, no
per-symbol docstrings -- because condensing relaxes how many words the secret
takes, never whether there is one secret.
"""

from __future__ import annotations

import pytest

import docstring_audit as audit


def measurement(path: str = "sieve/fake.py", **kw: int | bool) -> audit.Measurement:
    fields: dict[str, object] = {
        "path": path,
        "lines": 100,
        "module_docstring_words": 120,
        "has_module_docstring": True,
        "symbol_docstrings": 0,
        "symbol_docstring_words": 0,
        "comment_words": 200,
    }
    fields.update(kw)
    return audit.Measurement(**fields)  # pyright: ignore[reportArgumentType]


@pytest.fixture
def condensed(monkeypatch: pytest.MonkeyPatch) -> str:
    path = "sieve/fake.py"
    monkeypatch.setitem(audit.CONDENSED, path, (404, "what the file hides, in one line"))
    return path


def test_a_condensed_file_holds_at_its_own_ceiling(condensed: str) -> None:
    at_ceiling = measurement(condensed, module_docstring_words=104, comment_words=300)
    assert at_ceiling.prose_words == 404
    assert audit.condensed_violations(at_ceiling) == []


def test_growing_past_the_ceiling_is_a_violation(condensed: str) -> None:
    """One word over. The cap it beats -- 400 -- is not the number that binds it."""
    grown = measurement(condensed, module_docstring_words=105, comment_words=300)
    assert grown.prose_words == 405
    problems = audit.condensed_violations(grown)
    assert len(problems) == 1
    assert "405" in problems[0] and "404" in problems[0]


def test_the_ceiling_does_not_relax_the_one_secret_test(condensed: str) -> None:
    """Under its ceiling and still broken: the structural half is not on the same
    dial as the word count, so a file cannot condense its way out of it."""
    regressed = measurement(
        condensed,
        module_docstring_words=0,
        has_module_docstring=False,
        symbol_docstrings=3,
        symbol_docstring_words=90,
        comment_words=100,
    )
    assert regressed.prose_words < audit.CONDENSED[condensed][0]
    problems = audit.condensed_violations(regressed)
    assert len(problems) == 2
    assert any("secret is unstated" in p for p in problems)
    assert any("reappeared" in p for p in problems)


def test_a_condensed_file_has_left_the_queue(condensed: str) -> None:
    """The three ledgers differ in what they claim, never in whether the file is
    handed out again. A queue that re-serves a file until somebody bulldozes it
    is what the flag state was invented to avoid."""
    over_cap = measurement(condensed, comment_words=900)
    rows = [(over_cap, audit.violations(over_cap))]
    assert audit.queue(rows) == []
