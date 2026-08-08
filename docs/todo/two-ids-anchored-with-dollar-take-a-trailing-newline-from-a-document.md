---
title: Two ids anchored with `$` take a trailing newline from a document
status: awaiting-review
priority: normal
phase: 2
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pipeline_model.py -q -k a_tool_id_or_version_ending_in_a_newline_is_refused"
opened: 2026-08-08
---

# Two ids anchored with `$` take a trailing newline from a document

`TOOL_ID_PATTERN` and `SEMVER_PATTERN` in `core/tool_base.py` both end `$`, and
Python's `$` is `(?=\n?\Z)`. A project whose `tool_id` is the double-quoted
scalar `"downsample\n"` and whose `version` is `"1.0.0\n"` loads clean and keeps
both newlines — measured in
`findings/loop/2026.08.08-consolidating-two-guards-onto-one-constant-narrows-the-stricter-one.md`,
whose own subject was the same anchor on `NODE_ID_PATTERN`. A *bare* newline
inside a quoted scalar folds to a space and is refused, so writing one takes the
escape, which is what a hand edit is.

Neither field becomes a path, so this is not the node-id hole a second time. The
consequences are smaller and they differ:

- `tool_id` misses the registry, and the refusal names an id whose two spellings
  are indistinguishable on a terminal — a message the user cannot act on, which
  is `adr/declared-means-verified.md`'s complaint about a promise the code does
  not keep.
- `version` reaches `SEMVER_PATTERN.match(self.version).group()` on the cache-key
  path, so one tool version keys two entries and a cache the reviewer-rerun
  promise stands on quietly holds a duplicate.

What the item has to settle is whether that is enough to move both to `\Z`, or
whether the honest fix is narrower — the anchors are two of a class the tree may
hold more of, and a rule tested per-constant is the shape that let the first one
through. `Sink.format` shares `TOOL_ID_PATTERN` and would move with it.
