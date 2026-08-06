"""`sieve inspect` against the real shelf.

Deliberately not a scratch registry. Every other registry test builds its own
so that it controls what is on it; the thing this command is for is proving
that the *process-wide* shelf is populated by the time a command runs, and a
test that registered a fixture filter itself would prove the opposite of what
it was written to check.
"""

from __future__ import annotations

import subprocess
import sys

from typer.testing import CliRunner

from sieve.cli.app import app

runner = CliRunner()


def test_the_listing_finds_a_filter_in_a_process_that_imported_nothing() -> None:
    """The command's own `discover()` is what puts the filter on the shelf.

    A subprocess rather than `CliRunner`, and that is the whole test: in-process
    the registry is already populated by whatever else the suite imported, so an
    `inspect` that had forgotten to call `discover()` would pass and then print
    nothing for the user, whose `sieve inspect` starts a process that has
    imported exactly this module. It also exercises `sieve.cli.app` as an entry
    point, which is what the installed console script resolves to.
    """
    result = subprocess.run(
        [sys.executable, "-m", "sieve.cli.app", "inspect"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert any(line.startswith("downsample") and "1.0.0" in line for line in lines)


def test_a_version_that_is_not_installed_is_refused_with_the_ones_that_are() -> None:
    """A wrong version is a typo, and the fix is printed rather than looked up.

    Fails if `--version` falls back to `latest` — which would answer a question
    about 9.9.9 with 1.0.0's declaration and give no sign it had done so.
    """
    result = runner.invoke(app, ["inspect", "downsample", "--version", "9.9.9"])

    assert result.exit_code == 1
    assert "9.9.9" in result.stderr
    assert "1.0.0" in result.stderr


def test_the_description_carries_the_bounds_and_the_guidance() -> None:
    """Parameters come from the model and guidance comes from beside the module.

    Two claims in one invocation because they fail for the same class of reason
    and the command prints them in one pass: `factor`'s bounds exist only in
    the pydantic field, and the guidance text exists only in `downsample.md`.
    Fails if either is a string this module wrote down instead.
    """
    result = runner.invoke(app, ["inspect", "downsample"])

    assert result.exit_code == 0
    assert "minimum=2" in result.output
    assert "maximum=64" in result.output
    assert "work units/MP (uncalibrated)" in result.output
    assert "work_anchor" in result.output
    assert " s/MP" not in result.output
    # A sentence from `src/sieve/filters/downsample.md`, not from the spec.
    assert "Put it early" in result.output
