# CLAUDE.md

SIEVE isolates ethological events from video. The product constraint: the
interactive tuning loop — drag a slider, graphs refill faster than the video
plays. Architecture serves that or it does not belong.

## Layout

- `docs/VISION.md` — the binding target: components, what each must never
  own, the claims that define built-correctly.
- `docs/ARCHITECTURE.md` — index of ADRs under `docs/adr/`; settled
  decisions bind.
- `docs/PLAN.md` — build sequence.
- `docs/todo/`, `docs/findings/` — open work and measured truths. Regenerate
  indexes after editing: `uv run python scripts/doc_index.py`.
- `docs/V2-MAP.md` — where to look in `../antscihub-SIEVE-v2`, the previous
  generation and the evidence base. "Bring X over from v2" means bring the
  decision, not the file; `docs/VISION.md` already rules on several.
- `../antscihub-SIEVE` (v2.5) is a failed rewrite. Don't build on it.

## Conventions

- Minting a `docs/todo/` item is the exception, not the reflex. Before writing
  one, search the open items for the module, the symbol, and the claim: if a
  not-yet-done item would carry the observation, fold it in there. Two items
  one commit would satisfy are one item. The backlog's cost is its count, and
  a review that mints per observation pays that cost on your behalf.
  A fold adds the paragraph to the existing item and never edits its
  `done_when` — say in your final message that the criterion may no longer
  cover the whole of it, so the review can widen it.
- Comments record what the code cannot show. If a competent reader could
  derive the sentence from the code, delete it. Match the density of the
  file you're in.
- Docs say why, not what happened. One fact, one home — link, don't restate.
  Prefer a claim a test can check over prose a reader must trust.
- Commits: `type(scope): the sentence, not the changelog line`. Types:
  feat, fix, refactor, perf, docs, test, build, ci, chore.
- End the session with the branch committed and pushed. Never force-push.
- Stage by explicit path. Never `git add -A` or `git add .`.
- Orchestrator loop agents: an edit you did not make is the author's, and
  belongs to a separate commit. Don't stage it, revert it, stash it, or
  account for it as yours — leave it where it is and name it in your final
  message.

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
- The working tree is CRLF. Match and restore file content through bytes,
  not `write_text`. Mutation testing is
  `uv run python scripts/mutation_sweep.py`, never a scratch harness.
- Don't redirect stderr (`2>&1`) on native commands in PowerShell 5.1; it
  wraps output in ErrorRecords and fails commands that succeeded.
