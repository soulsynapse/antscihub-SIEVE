# CLAUDE.md


## Comments and docstrings
- Write no comment by default. When one is needed, one line stating a why the
  code cannot; prefer a clearer name to a comment.
- A docstring states the contract: what goes in, what comes out, and the
  constraints a caller cannot see from the signature. Prose, no section
  headings. It never narrates what the body does.
- A module docstring says what the module is and where its seams are, within
  the length tests/test_seams.py allows. It is not a changelog.
- A change to behaviour, a name or a contract updates or deletes every comment,
  docstring and cross-reference it invalidates, wherever they sit, not only in
  the lines touched. A comment contradicting the code is a correctness bug.
  Write comments about the code as it now is; the change itself is the commit
  message's to tell.
- Prose contradicting code you did not change is reported, never silently
  fixed or cut: which side is wrong is the author's call, and the comment may
  be a bug's only witness.
- Moving or refactoring code keeps its comments unless the change makes one
  obsolete.

## Tests
- `tests/` holds seams and invariants: what a later change elsewhere could break without anyone
  looking. A feature is not pinned to a test for having been built.
- That a behaviour was seen working once is shown by a one-off script under
  `docs/findings/experiments/` or a simulation's exit, not by a new test.
- A spec's `Check:` is a one-off by the same rule and a test only for a seam or an invariant; a
  check already ticked as a test stands.
- Tests built of wall time carry the `simulation` marker and stay out of the default run;
  `pyproject.toml` holds the marker.
- A test asserts only what holds whichever thread runs first and however slow the machine is. A
  count or a position that a second thread or a timer can move is fixed by taking that thread out:
  the worker's turns are taken on the test's thread, a clock is handed in, a value a timer may have
  moved is read before the act and compared after. Waiting on another thread for an end state that
  must come is allowed; asserting what it passed through on the way is not.
- A test that fails some runs is a defect in the test or a race in the code, and is settled as one
  or the other: never rerun until green, never widened by a row, never measured for how often.

## Running
- Run Python and pytest through `.venv/Scripts/python.exe`; the anaconda `python` on PATH has no PySide6.
- Files are LF. A script that rewrites one must open it with `newline="\n"` (or write bytes); Python's
  default on Windows writes CRLF, and git then warns on every touch.
- A Python script fed to the Bash tool by heredoc has its `\n` escapes turned into real newlines;
  write or edit files with the Write and Edit tools instead.
