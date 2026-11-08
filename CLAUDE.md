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

## Running
- Run Python and pytest through `.venv/Scripts/python.exe`; the anaconda `python` on PATH has no PySide6.
- Files are LF. A script that rewrites one must open it with `newline="\n"` (or write bytes); Python's
  default on Windows writes CRLF, and git then warns on every touch.
