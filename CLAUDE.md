# CLAUDE.md

SIEVE isolates ethological events from video. The product constraint: the
interactive tuning loop — drag a slider, graphs refill faster than the video
plays.

## Conventions

- Commits are with conventional commits.
- `docs/SCAFFOLD.md` is generated, never hand-edited: a pre-commit hook rebuilds
  it from the staged tree and stages it, so every commit carries a map matching
  what it moved. The glosses are each module's first docstring line, which is
  where a wrong one gets fixed. Hooks are tracked in `.githooks/`, so a fresh
  clone turns them on with `git config core.hooksPath .githooks`;
  `SIEVE_SKIP_SCAFFOLD=1` commits without one.

## Environment

- Windows, PowerShell 5.1 by default; a Bash tool is also available. This
  directory is a git worktree (`.git` is a file).
- A queued run executes in this same tree — the orchestrator launches it where
  its row was queued from — sharing one index and one HEAD with whoever is at
  the keyboard. Don't edit while one is running: the check that decides whether
  a run committed reads HEAD either side of it, and cannot tell your commit
  from the run's.
- Run Python through `uv run`, never bare `python`. No type checker is
  installed; don't spawn one.
- Write commit messages to a file and `git commit -F <file>` — a here-string
  in either shell corrupts the message and exits 0.
- `core.autocrlf` is on, so git checks files out converted and normalizes them
  back on the way in, while anything a tool has written since is still whatever
  that tool wrote — a file's own bytes are the only authority on its endings,
  never a rule stated here. Match and restore content through bytes, not
  `write_text`, and don't normalize a file you only meant to edit.
  `.gitattributes` is where a file that must not be converted says so, and its
  comment says why for the only ones that do.
- Don't redirect stderr (`2>&1`) on native commands in PowerShell 5.1; it
  wraps output in ErrorRecords and fails commands that succeeded.
