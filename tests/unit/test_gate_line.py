"""The gate's line holds the formatter and the workflow linter, and it is written once.

Six claims that were prose until this file, and each of the first four was
wrong as prose at some point. `ruff` sat in the dev group with no bound, so a lock refresh
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
(`findings/2026.08.07-actionlint-is-seven-tenths-of-a-percent-of-the-gate.md`,
settled as `adr/a-check-joins-the-gate-line.md`).

The fifth is about the line's comment rather than the line: it holds the rule
for what may join, so it has to cite the ADR that rule binds in rather than
restate it. Membership was argued from scratch in three files before there was
one, which is what `docs/todo/what-earns-a-place-on-the-gate-line.md` is.

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

The sixth is the only one about a copy rather than the line. ADR 19 makes a
copy forbidden exactly when something requires it to stay identical to the
line, and the one copy that met that test was an item's `done_when`, repaired
twice by a reviewer noticing rather than by anything red. That copy is struck
(`docs/todo/the-gate-line-has-a-live-second-copy-adr-19-forbids.md`), so the
walk passes over an empty set and the case beside it is what the walk would
catch — a check written for the next copy, not this one.
"""

from __future__ import annotations

import os
import re
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
TODO = REPO / "docs" / "todo"

#: The step whose `run:` is the gate. There is no second copy of the line in a
#: noxfile or a README, so this name is the only handle on it.
GATE_STEP = "Run the gate"

#: A citation as the gate step's comment already spells one: a path relative to
#: `docs/`, unbracketed, inside prose.
CITATION = re.compile(r"\badr/[a-z0-9-]+\.md\b")

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


def _gate_comment() -> str:
    """The comment block directly above the gate step, which YAML parsing drops.

    Read off the raw text by walking back from the step's `name:`, so a comment
    moved to sit above some other step stops being this one.
    """
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.strip() == f"- name: {GATE_STEP}":
            break
    else:
        raise AssertionError(f"no step named {GATE_STEP!r} in {WORKFLOW.name}")
    start = index
    while start and lines[start - 1].lstrip().startswith("#"):
        start -= 1
    return "\n".join(lines[start:index])


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


def _front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def _restates_the_gate_line(criterion: str) -> bool:
    """Whether a `done_when` stands in for the gate line rather than naming a check.

    A stand-in is the line, the line with commands appended, or the line with
    commands missing off its end. The last is the shape one of the two recorded
    drifts took — `actionlint` joined the line's end and not the copy — so a
    rule keyed on equal length would be blind to it.

    The other drift is out of reach of any rule reading the string alone, and
    widening this one to "the copy's commands in order" does not help: `ruff
    format --check` joined the line *second*, so that copy has a hole in the
    middle, and it is byte-identical to
    `the-gate-has-no-opinion-about-the-workflow.md`'s `done_when`, which
    restates nothing. Two equal strings, opposite verdicts
    (`findings/2026.08.07-the-gate-line-walk-catches-one-of-the-two-drifts-the-item-cites.md`).

    Sharing commands with the gate is not restating it. Most items are checked
    by some arrangement of `pytest` and `lint-imports`, and nothing in their
    content requires those to track the line.
    """
    gate = [command.strip() for command in _gate_line().split("&&")]
    commands = [command.strip() for command in criterion.split("&&")]
    if len(commands) < 2:
        return False
    shorter, longer = sorted((commands, gate), key=len)
    return longer[: len(shorter)] == shorter


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


def test_the_gate_steps_comment_cites_the_rule_it_applies() -> None:
    comment = _gate_comment()
    cited = [REPO / "docs" / reference for reference in CITATION.findall(comment)]

    assert cited, (
        f"the {GATE_STEP!r} comment cites no ADR:\n{comment}\n"
        f"the rule for what may join this line binds in `docs/adr/`, and a comment that "
        f"argues it instead of citing it is where the fourth argument from scratch starts"
    )
    missing = [path.name for path in cited if not path.exists()]
    assert not missing, f"the {GATE_STEP!r} comment cites {missing}, which is not in docs/adr/"


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


def test_no_restatement_of_the_gate_line_drifts_from_it() -> None:
    drifted = {
        path.name: criterion
        for path in sorted(TODO.glob("*.md"))
        if _restates_the_gate_line(criterion := str(_front_matter(path).get("done_when", "")))
        and criterion != _gate_line()
    }

    assert not drifted, (
        "these items' `done_when` stands in for the gate line and no longer matches it:\n"
        + "\n".join(f"  {name}: {criterion}" for name, criterion in drifted.items())
        + f"\n  {WORKFLOW.name}: {_gate_line()}\n"
        f"a copy of the line falls behind it and the copy a person runs is the one that "
        f"falls (adr/the-gate-is-one-line.md); an item whose criterion is the gate names a "
        f"check that reads the line instead of holding a second copy of it"
    )


def test_a_copy_a_command_behind_the_gate_line_is_the_thing_that_walk_looks_for() -> None:
    """What the walk above would catch, since today it passes over an empty set.

    The shape is the `actionlint` drift's, the line minus its newest command.
    The second case is the one that has to stay out: an item checked by two of
    the gate's commands is not keeping a copy of the line.
    """
    assert _restates_the_gate_line(" && ".join(_gate_line().split("&&")[:-1]))
    assert not _restates_the_gate_line("uv run pytest -q && uv run lint-imports")
