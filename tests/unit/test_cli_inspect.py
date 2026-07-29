








from __future__ import annotations

import subprocess
import sys

from typer.testing import CliRunner

from sieve.cli.app import app

runner = CliRunner()


def test_the_listing_finds_a_filter_in_a_process_that_imported_nothing() -> None:









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





    result = runner.invoke(app, ["inspect", "downsample", "--version", "9.9.9"])

    assert result.exit_code == 1
    assert "9.9.9" in result.stderr
    assert "1.0.0" in result.stderr


def test_the_description_carries_the_bounds_and_the_guidance() -> None:







    result = runner.invoke(app, ["inspect", "downsample"])

    assert result.exit_code == 0
    assert "minimum=2" in result.output
    assert "maximum=64" in result.output

    assert "Put it early" in result.output
