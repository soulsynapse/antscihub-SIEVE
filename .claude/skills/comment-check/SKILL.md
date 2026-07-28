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
