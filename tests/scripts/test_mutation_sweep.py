"""The sweep cannot lie the recorded ways: bad anchors and red baselines refuse, restores are byte-exact.

Each case pins one of the loop findings the module encodes. The test commands are
`python -c` probes reading the subject file, so a kill and a survival are decided by
bytes on disk rather than by an import graph the tmp tree does not have.
"""

import sys
import time
from pathlib import Path

import mutation_sweep
import pytest
from mutation_sweep import Mutant, SweepError, apply_mutant, main, parse_mutant, run_sweep


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    return tmp_path


def subject_with(repo: Path, data: bytes) -> Path:
    path = repo / "src" / "subject.py"
    path.write_bytes(data)
    return path


def probe(path: Path, needle: str) -> list[str]:
    """A command that fails — kills the mutant — when `needle` has left the file."""
    code = (
        f"import sys, pathlib; "
        f"sys.exit(0 if {needle!r} in pathlib.Path({str(path)!r}).read_text() else 1)"
    )
    return [sys.executable, "-c", code]


def test_a_mutant_is_anchor_separator_replacement() -> None:
    mutant = parse_mutant("left + width ==> left - width")
    assert (mutant.anchor, mutant.replacement) == ("left + width", "left - width")


def test_a_mutant_written_without_padding_splits_the_same_way() -> None:
    """The unspaced form is the fallback, so an anchor ending in a space is still reachable."""
    assert parse_mutant("a==>b") == Mutant(anchor="a", replacement="b")


def test_an_empty_anchor_is_refused() -> None:
    with pytest.raises(SweepError, match="empty anchor"):
        parse_mutant(" ==> replacement")


def test_a_long_anchor_is_labelled_within_the_column() -> None:
    label = Mutant(anchor="x" * 80, replacement="y").label
    assert len(label) == 60 and label.endswith("...")


def test_a_mutant_without_the_separator_is_refused() -> None:
    with pytest.raises(SweepError, match="==>"):
        parse_mutant("left + width -> left - width")


def test_a_self_replacement_is_refused_as_a_guaranteed_survivor() -> None:
    with pytest.raises(SweepError, match="survive"):
        parse_mutant("width ==> width")


def test_an_anchor_that_also_appears_in_prose_is_refused(repo: Path) -> None:
    """The docstring hit: two occurrences means the replace may land in prose."""
    data = b'"""Uses INTER_AREA for shrinking."""\nkind = INTER_AREA\n'
    with pytest.raises(SweepError, match="occurs 2 times"):
        apply_mutant(data, Mutant(anchor="INTER_AREA", replacement="INTER_LINEAR"))


def test_a_missing_anchor_is_refused_not_skipped() -> None:
    with pytest.raises(SweepError, match="not found"):
        apply_mutant(b"kind = 1\n", Mutant(anchor="kind = 2", replacement="kind = 3"))


def test_an_lf_anchor_finds_the_crlf_file() -> None:
    """The CRLF miss: anchors are written in `\\n` and the tree is CRLF on disk."""
    data = b"a = 1\r\nb = 2\r\n"
    mutated = apply_mutant(data, Mutant(anchor="a = 1\nb = 2", replacement="a = 9\nb = 2"))
    assert mutated == b"a = 9\r\nb = 2\r\n"


def test_a_killed_and_a_surviving_mutant_are_told_apart(repo: Path) -> None:
    subject = subject_with(repo, b"# note\nlimit = 100\n")
    results = run_sweep(
        subject,
        [
            Mutant(anchor="limit = 100", replacement="limit = 101"),
            Mutant(anchor="# note", replacement="# not"),
        ],
        probe(subject, "limit = 100"),
        repo,
    )
    assert [killed for _, killed in results] == [True, False]


def test_the_subject_restores_byte_exact_including_crlf(repo: Path) -> None:
    """The `write_text` hit: a CRLF subject comes back with its exact bytes."""
    data = b"# note\r\nlimit = 100\r\n"
    subject = subject_with(repo, data)
    run_sweep(subject, [Mutant("limit = 100", "limit = 1")], [sys.executable, "-c", ""], repo)
    assert subject.read_bytes() == data


def test_the_subject_restores_when_the_command_cannot_even_run(repo: Path) -> None:
    data = b"limit = 100\n"
    subject = subject_with(repo, data)
    with pytest.raises(FileNotFoundError):
        run_sweep(subject, [Mutant("100", "1")], ["no-such-command-anywhere"], repo)
    assert subject.read_bytes() == data


def test_a_restore_that_did_not_take_refuses_the_tree(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guarantee has to fire on a restore that silently did nothing, not only on a good one.

    Nothing reachable through the public API can defeat the `finally`, so the write is
    dropped from underneath it — which is the shape of the `write_text` bug the guard
    exists for: a restore that returns without leaving the original bytes on disk.
    """
    data = b"limit = 100\n"
    subject = subject_with(repo, data)
    write_bytes = Path.write_bytes
    monkeypatch.setattr(
        Path, "write_bytes", lambda self, raw: len(raw) if raw == data else write_bytes(self, raw)
    )
    with pytest.raises(SweepError, match="byte-exact"):
        run_sweep(subject, [Mutant("100", "1")], [sys.executable, "-c", ""], repo)


def test_the_child_runs_with_bytecode_writing_off(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stale-bytecode hit at its source: the child is the process that would write a `.pyc`.

    The variable is cleared first because a sweep of this very module sets it for the
    pytest it spawns, so the grandchild would inherit it and the case would pass with
    the line that sets it deleted
    (`docs/findings/loop/2026.08.07-a-test-that-clears-an-environment-variable-is-vacuous-where-the-platform-default-already-agrees.md`).
    """
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    marker = repo / "dont-write.txt"
    subject = subject_with(repo, b"limit = 100\n")
    report = (
        f"import sys, pathlib; "
        f"pathlib.Path({str(marker)!r}).write_text(str(sys.dont_write_bytecode))"
    )
    run_sweep(subject, [Mutant("100", "1")], [sys.executable, "-c", report], repo)
    assert marker.read_text() == "True"


def test_stale_bytecode_is_purged_for_every_run(repo: Path) -> None:
    """The same-size-edit hit: any cached bytecode under the roots is removed."""
    cache = repo / "src" / "__pycache__"
    cache.mkdir()
    (cache / "subject.cpython-313.pyc").write_bytes(b"stale")
    subject = subject_with(repo, b"limit = 100\n")
    run_sweep(subject, [Mutant("100", "1")], [sys.executable, "-c", ""], repo)
    assert not cache.exists()


def test_exit_is_red_on_a_survivor_and_green_on_a_clean_kill(repo: Path) -> None:
    subject = subject_with(repo, b"limit = 100\n")
    kill = ["--file", "src/subject.py", "--mutant", "limit = 100 ==> limit = 1", "--"]
    assert main([*kill, *probe(subject, "limit = 100")], repo) == 0
    assert main([*kill, sys.executable, "-c", ""], repo) == 1


def test_a_command_line_without_a_test_command_is_refused(repo: Path) -> None:
    """The subject is written first: without it both lines are refused for the missing file."""
    subject_with(repo, b"limit = 100\n")
    assert main(["--file", "src/subject.py", "--mutant", "a ==> b"], repo) == 2
    assert main(["--file", "src/subject.py", "--mutant", "a ==> b", "--"], repo) == 2


def test_a_subject_that_is_not_a_file_is_refused(repo: Path) -> None:
    argv = ["--file", "src/absent.py", "--mutant", "a ==> b", "--", sys.executable, "-c", ""]
    assert main(argv, repo) == 2


def test_a_refused_anchor_is_reported_rather_than_raised(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A mistyped anchor reaches the reviewer as exit 1 and a message, not a traceback.

    The message is asserted because a survivor exits 1 too, and two paths sharing a
    return value is exactly the shape that leaves both untested
    (`docs/findings/loop/2026.08.07-two-refusals-that-return-the-same-code-shield-each-other-from-the-only-case.md`).
    """
    subject_with(repo, b"limit = 100\n")
    argv = ["--file", "src/subject.py", "--mutant", "absent ==> x", "--", sys.executable, "-c", ""]
    assert main(argv, repo) == 1
    assert "not found" in capsys.readouterr().err


def test_a_red_baseline_is_refused_rather_than_swept(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The fifth lie: a command red on the original bytes prints KILLED for every mutant.

    The command here is red no matter what the file holds, which is the crash shape —
    the sweep must refuse and show the command's own words, not report a clean kill.
    """
    subject_with(repo, b"limit = 100\n")
    red = [
        sys.executable,
        "-c",
        "import sys; print('E   ImportError: no such fixture'); sys.exit(4)",
    ]
    argv = ["--file", "src/subject.py", "--mutant", "limit = 100 ==> limit = 1", "--", *red]
    assert main(argv, repo) == 1
    captured = capsys.readouterr()
    assert "KILLED" not in captured.out
    assert "before any mutation" in captured.err
    assert "no such fixture" in captured.err


def test_an_oracle_over_budget_is_refused_as_too_broad(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The budget is a refusal with a remedy, not a report — no mutant verdict prints."""
    subject_with(repo, b"limit = 100\n")
    argv = [
        "--file",
        "src/subject.py",
        "--mutant",
        "limit = 100 ==> limit = 1",
        "--oracle-budget",
        "0.0001",
        "--",
        sys.executable,
        "-c",
        "",
    ]
    assert main(argv, repo) == 1
    captured = capsys.readouterr()
    assert "KILLED" not in captured.out
    assert "--oracle-budget" in captured.err


def test_a_hung_mutant_is_killed_and_the_subject_restores(repo: Path) -> None:
    """A mutant that stops the command terminating broke the program, which is a kill.

    Without the per-mutant timeout this case never returns — the hang is the shape
    that stranded the loop's own sweeps, backgrounded and then killed at turn end
    with the mutant still patched into the tree.
    """
    data = b"limit = 100\n"
    subject = subject_with(repo, data)
    code = (
        f"import sys, time, pathlib; "
        f"text = pathlib.Path({str(subject)!r}).read_text(); "
        f"time.sleep(60) if 'limit = 100' not in text else sys.exit(0)"
    )
    results = run_sweep(
        subject,
        [Mutant(anchor="limit = 100", replacement="limit = 1")],
        [sys.executable, "-c", code],
        repo,
        mutant_timeout=1.0,
    )
    assert [killed for _, killed in results] == [True]
    assert subject.read_bytes() == data


def test_a_hung_grandchild_does_not_outlive_the_mutant_timeout(repo: Path) -> None:
    """The live oracle shape: `uv run pytest` is a grandchild, and the case above is not.

    `subprocess.run(capture_output=True, timeout=T)` kills the process it started and
    then blocks in `communicate()` until every inherited copy of the pipe closes, so a
    command whose grandchild outlives it runs to the grandchild's own completion — 40.1s
    measured under a 3s timeout
    (`docs/findings/loop/2026.08.08-a-subprocess-timeout-does-not-bound-a-command-whose-grandchild-holds-the-pipe.md`).
    The mutant here spawns a grandchild that outlives its parent's kill and marks the
    disk partway through, so both halves are asserted: the call returns inside the
    timeout, and the work it was bounding is over rather than merely disowned.
    """
    data = b"limit = 100\n"
    subject = subject_with(repo, data)
    marker = repo / "grandchild-ran.txt"
    grandchild = (
        f"import time, pathlib; time.sleep(2); "
        f"pathlib.Path({str(marker)!r}).write_text('ran'); time.sleep(18)"
    )
    code = (
        f"import pathlib, subprocess, sys, time; "
        f"sys.exit(0) if 'limit = 100' in pathlib.Path({str(subject)!r}).read_text() else None; "
        f"subprocess.Popen([{sys.executable!r}, '-c', {grandchild!r}]); "
        f"time.sleep(18)"
    )
    started = time.monotonic()
    results = run_sweep(
        subject,
        [Mutant(anchor="limit = 100", replacement="limit = 1")],
        [sys.executable, "-c", code],
        repo,
        mutant_timeout=1.0,
    )
    elapsed = time.monotonic() - started
    assert [killed for _, killed in results] == [True]
    assert elapsed < 10.0
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not marker.exists():
        time.sleep(0.1)
    assert not marker.exists()
    assert subject.read_bytes() == data


def test_an_oracle_whose_output_outgrows_the_pipe_buffer_is_scored_by_its_exit(repo: Path) -> None:
    """Redirecting to files is what keeps a talkative oracle running, not what returns on time.

    Nothing in `_run_bounded` drains the streams — it waits on the process handle, so
    promptness is `Popen.wait`'s and holds whatever the streams are
    (`docs/findings/loop/2026.08.10-a-two-part-fix-is-reported-as-two-kills-and-the-half-that-carries-it-is-the-other-one.md`).
    Under `PIPE` the child blocks in its own `write` once the buffer fills, never exits,
    and is timed out — and a timeout is a kill, so the verdict is KILLED for a mutant
    the tests do not kill. Both streams are filled because either redirection alone
    would otherwise be the uncased half, and the mutant here survives, which is the
    verdict a full buffer would silently flip.
    """
    subject = subject_with(repo, b"limit = 100\n")
    fat = 1 << 20
    noisy = f"import sys; sys.stdout.write('o' * {fat}); sys.stderr.write('e' * {fat}); sys.exit(0)"
    results = run_sweep(
        subject,
        [Mutant(anchor="limit = 100", replacement="limit = 1")],
        [sys.executable, "-c", noisy],
        repo,
        oracle_budget=20.0,
        mutant_timeout=20.0,
    )
    assert [killed for _, killed in results] == [False]


def test_the_mutant_timeout_is_derived_from_the_baseline(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both halves of the derivation are run, because every other case passes the timeout in.

    The floor and the factor were written and checked by nothing — `max(FLOOR, 2.0 *
    elapsed + 1.0) ==> 300.0` SURVIVED a sweep of this module. A fast baseline takes the
    floor; the floor is then lowered so a slower one takes the doubling.
    """
    subject = subject_with(repo, b"limit = 100\n")
    seen: list[float] = []
    bounded = mutation_sweep._run_bounded

    def record(command: list[str], cwd: Path, env: dict[str, str], timeout: float):
        seen.append(timeout)
        return bounded(command, cwd, env, timeout)

    monkeypatch.setattr(mutation_sweep, "_run_bounded", record)
    run_sweep(subject, [Mutant("100", "1")], [sys.executable, "-c", ""], repo)
    assert seen == [
        mutation_sweep.ORACLE_BUDGET_SECONDS,
        mutation_sweep.MUTANT_TIMEOUT_FLOOR_SECONDS,
    ]

    seen.clear()
    monkeypatch.setattr(mutation_sweep, "MUTANT_TIMEOUT_FLOOR_SECONDS", 0.0)
    slow = [sys.executable, "-c", "import time; time.sleep(0.5)"]
    run_sweep(subject, [Mutant("100", "1")], slow, repo)
    assert 2.0 * 0.5 + 1.0 <= seen[1] <= 2.0 * 3.0 + 1.0
