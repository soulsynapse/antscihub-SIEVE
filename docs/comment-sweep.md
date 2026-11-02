# Comment sweep: the brief for one file

A one-off pass over the tree, one file per run, bringing every comment and docstring to the
standard in CLAUDE.md. Delete this file when the sweep is done; the standard stays in CLAUDE.md.

## The run

You are given one file. Read all of it. Change nothing but comments and docstrings: a diff that
touches any other line is wrong and you start over. Then run `.venv\Scripts\python -m pytest -q`
and stop if it does not pass. Reply with the diff and the list below. Do not commit.

Classify every comment and docstring in the file as one of:

- **contract**: what goes in, what comes out, a constraint a caller cannot see from the signature.
  Keep, untouched.
- **why**: a reason the code cannot state. Keep, untouched.
- **trap**: a platform, library or concurrency fact that would bite someone who did not know it.
  Keep, untouched.
- **restatement**: recoverable by reading the code under it. Cut.
- **narration**: the story of how the module got its features, one sentence per commit. Cut; a
  module docstring left over about ten lines is narration until shown otherwise.
- **stale**: says something the code does not do. Keep it as it is and report it, with the line
  and what the code does instead.

Keep a line unread by the model whenever it names a thread, a lock, the GIL, Windows, cp1252, Qt,
cv2, FFmpeg, a `docs/findings` path, a unit or a numeric range, or contains "must", "never" or
"only". Erring toward keeping a restatement is the right error; a cut trap is not recoverable.

Never reword what you keep. Never merge two kept comments. Never add a comment.

## The list

For each cut: the line it was on and its class. For each stale: the line, the text, and what the
code does. Nothing else.

## Order and batches

1. `sieve_player/document.py`, `pane.py`, `worker.py`, `graph.py`: the module headers that read as changelogs.
2. The rest of `sieve_player/` and `sieve_player/dev/`.
3. `tools/*.py`.
4. `tests/*.py`, `smoke.py`, `bench.py`.

One commit per batch after review, so blame on a module lands on one sweep commit. Tests and
`smoke.py` pass before each.
