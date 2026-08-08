"""The gate's line holds the formatter and the workflow linter, and reaches the code only.

Four claims that were prose until this file, and each was wrong as prose at
some point. `ruff` sat in the dev group with no bound, so a lock refresh
restyled files nobody edited; the gate ran `ruff check` and never `ruff format
--check`, so the tree disagreed with its own formatter for two commits; and the
commit that fixed both stated that the formatter "has no opinion about `.md`",
which
`findings/2026.08.07-ruff-format-check-over-the-root-formats-the-python-in-docs.md`
measured as false — 219 of the 330 files that run scanned were documents.

The fourth is `actionlint`, and it is here because the formatter's two-commit
absence is the precedent: a command can leave this line and nothing notices.
Nothing else in the tree reads `.github/workflows/`, and the errors actionlint
catches are the ones that stop the job — so a CI green cannot stand in for it
(`findings/2026.08.07-actionlint-is-seven-tenths-of-a-percent-of-the-gate.md`).

The third test is the one with content. `docs/findings/` exists to quote code
that does not work, and a Markdown file is not a place a formatter gets a vote,
so `pyproject.toml` excludes Markdown from ruff's file discovery and the gate
comment says so. What is pinned here is the property rather than the mechanism:
whatever target the gate's own line passes to `ruff format --check`, a document
holding an unformatted Python fence survives it and a `.py` file does not. A
later decision to bound the target by directory instead of by file type answers
the same way.

`docs/todo/ruff-format-drifts-because-ruff-is-unpinned.md` is the item behind
all three.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

import sieve

REPO = Path(str(sieve.__file__)).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

#: The step whose `run:` is the gate. There is no second copy of the line in a
#: noxfile or a README, so this name is the only handle on it.
GATE_STEP = "Run the gate"

#: A file ruff wants to rewrite, in both spellings the tree holds.
UNFORMATTED = "x = (   1+2 )\n"
UNFORMATTED_FENCE = f"# A finding quoting code that does not work.\n\n```python\n{UNFORMATTED}```\n"


def _dev_group() -> list[str]:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["dependency-groups"]["dev"]


def _gate_line() -> str:
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["gate"]["steps"]
    for step in steps:
        if step.get("name") == GATE_STEP:
            return str(step["run"])
    raise AssertionError(f"no step named {GATE_STEP!r} in {WORKFLOW.name}")


def _gate_commands() -> list[list[str]]:
    """The gate line's `&&`-separated commands, tokenised."""
    return [shlex.split(command) for command in _gate_line().split("&&")]


def _format_targets() -> list[str]:
    """The paths the gate's own `ruff format --check` is pointed at."""
    for command in _gate_line().split("&&"):
        tokens = shlex.split(command)
        if "ruff" not in tokens or tokens[tokens.index("ruff") + 1 :][:2] != ["format", "--check"]:
            continue
        after = tokens[tokens.index("--check") + 1 :]
        return [token for token in after if not token.startswith("-")]
    raise AssertionError(f"no `ruff format --check` in the {GATE_STEP!r} line")


def _ruff() -> Path:
    """The pinned ruff, beside the interpreter running the tests.

    Not `uv run ruff` as the gate spells it: `uv` would resolve the environment
    against the *copy's* `pyproject.toml`, which names no dev group, and install
    whatever ruff is newest that day — the drift this file exists to pin.
    """
    binary = Path(sys.executable).parent / ("ruff.exe" if os.name == "nt" else "ruff")
    if not binary.exists():
        pytest.skip(f"no ruff beside {sys.executable}")
    return binary


@pytest.fixture(scope="module")
def unformatted_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The repo's ruff config, over one bad document and one bad module.

    The directories the gate might name all exist, so the target under test is
    the only thing that decides what is reached. The config is copied rather
    than pointed at with `--config` because ruff resolves `exclude` patterns
    against the directory the config sits in.
    """
    tree = tmp_path_factory.mktemp("gate")
    shutil.copyfile(PYPROJECT, tree / "pyproject.toml")
    for directory in ("docs", "src", "tests", "scripts"):
        (tree / directory).mkdir()
    (tree / "docs" / "finding.md").write_text(UNFORMATTED_FENCE, encoding="utf-8")
    (tree / "README.md").write_text(UNFORMATTED_FENCE, encoding="utf-8")
    (tree / "src" / "module.py").write_text(UNFORMATTED, encoding="utf-8")
    return tree


def test_ruff_is_pinned_to_an_exact_version() -> None:
    pins = [entry for entry in _dev_group() if entry.split("=")[0].split(">")[0].strip() == "ruff"]

    assert pins, f"no ruff in the dev group of {PYPROJECT.name}"
    assert "==" in pins[0], (
        f"{pins[0]!r} lets a lock refresh restyle files nobody edited; the formatter's "
        f"version decides what the committed tree is, so it is pinned with `==`"
    )


def test_the_gate_line_runs_the_formatter() -> None:
    line = _gate_line()

    assert "ruff format --check" in line, (
        f"the {GATE_STEP!r} line runs {line!r}; `ruff check` and `ruff format --check` "
        f"are unrelated commands and green on one says nothing about the other"
    )


def test_the_gate_line_lints_the_workflow() -> None:
    commands = _gate_commands()

    assert ["uv", "run", "actionlint"] in commands, (
        f"the {GATE_STEP!r} line runs {commands}; nothing else in the tree reads "
        f"`.github/workflows/`, and a step added to `ci.yml` to check `ci.yml` is a step the "
        f"errors worth catching stop from running, so the pre-push line is the only reader"
    )


def test_the_formatters_reach_into_docs_is_the_one_the_gate_declares(
    unformatted_tree: Path,
) -> None:
    result = subprocess.run(
        [str(_ruff()), "format", "--check", *_format_targets()],
        cwd=unformatted_tree,
        # A file needing reformatting exits 1, which is the result under test.
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    report = result.stdout + result.stderr

    assert "module.py" in report, f"the gate's target does not reach the code:\n{report}"
    assert ".md" not in report, (
        f"the gate's target formats the Python inside documents:\n{report}\n"
        f"a finding quoting broken code would turn a docs-only commit red in CI"
    )
