---
name: comment-check
description: Check the comments in the working diff against the derivability test — does this say anything the code does not. Runs a naive reader over only what changed.
argument-hint: "[paths, or nothing for the working diff]"
---

Run `comment-critic` over the comments in $ARGUMENTS, or over the working diff
if no paths were given.

1. Get the changed hunks: `git diff -U15 HEAD -- $ARGUMENTS`. **Pass line
   ranges, not whole files** — a comment is judged against the code it sits on,
   so a hunk with context is the unit. A whole file is 20x the input for the
   same answer.
2. Spawn `comment-critic` per file, in one message so they run concurrently.
   Give each the file path, the line ranges, and an output path under the
   scratchpad directory.
3. Each returns one line. Read a findings file only if its count is non-zero.
4. Apply the cuts yourself. **Delete a docstring only when it is entirely
   restatement** — a docstring cannot consist of rationale with no subject, so
   "cut the first sentence" is bad advice and the critic gives it freely.
5. Ignore anything the critic says about comments that are *missing*. It is
   biased toward more explanation and will ask for docstrings on functions that
   do not need them.

The rule being enforced is `CLAUDE.md`'s: a comment earns its place by
recording a decision — the reason, the rejected alternative, the non-obvious
consequence. If a competent reader can derive it from the code, delete it; if
they cannot, that is the whole value and shortening it is the wrong cut.

## Retooling this — read before editing the agent

Nothing here reaches the critic. `.claude/agents/comment-critic.md` is what it
*is*; this file is how it is used and tuned, so tuning notes belong here.
(HTML comments are not stripped from an agent body — they would land in the
system prompt as text for the model to interpret.)

**The target.** A prompt short and precise enough that the critic is right
every time, at which point it is given `Edit` and applies the cuts itself
instead of reporting them. Reporting is the training-wheels stage, not the
design.

**The promotion criterion**, so it is a decision and not a feeling: three
consecutive runs where every finding is accepted and nothing has to be
ignored. Today it fails on two known classes — asking for docstrings that are
missing, and advising that a docstring's first sentence be cut. Both are
listed above because they recur; when they stop, it is close.

**The falsifier, and the tension worth naming.** "Refine the prompt" and "keep
it short" pull against each other, and which one wins is the whole answer.
Every clarification added to keep the critic correct is *evidence it is not
getting it* — so prompt length is the signal, not the fix. If the prompt has
to keep growing, the task is above this model tier and the right move is to
raise the tier, not to accrete instructions. Note the line count when you
edit; a prompt that has doubled has answered the question.

**The size half is already instrumented.** The `SubagentStop` hook logs every
return to `.claude/subagent-returns.jsonl` and speaks above 2000 chars, so a
loosening return contract announces itself. Correctness has no instrument —
that is the count of findings you rejected, and it is on you to notice.
