"""The sweep cannot lie the four recorded ways: bad anchors refuse, restores are byte-exact.

Each case pins one of the loop findings the module encodes. The test commands are
`python -c` probes reading the subject file, so a kill and a survival are decided by
bytes on disk rather than by an import graph the tmp tree does not have.
"""

import sys
from pathlib import Path

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
    assert main(["--file", "src/subject.py", "--mutant", "a ==> b"], repo) == 2
    assert main(["--file", "src/subject.py", "--mutant", "a ==> b", "--"], repo) == 2
