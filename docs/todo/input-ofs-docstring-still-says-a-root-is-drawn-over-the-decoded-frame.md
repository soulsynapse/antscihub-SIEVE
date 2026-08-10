---
title: input_of's docstring still says a root's input is the decoded frame
priority: normal
phase: 10
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k input_of_agrees_with_render_at"
opened: 2026-08-10
---

# input_of's docstring still says a root's input is the decoded frame

`ee5420c` ruled a source root drawn alone
([a-second-source-root-is-drawn-over-the-first-roots-footage.md](a-second-source-root-is-drawn-over-the-first-roots-footage.md))
and rewrote the two docstrings that carried the old reading —
`tuning.render_at`'s and `app._paint_viewport`'s. The third was left behind.
`app.input_of` still says of its `None` return: "a root, whose input is the
frame the run decoded rather than another node's output — which is what
`tuning.render_at` reads it as." `render_at` now reads that `None` as no input
layer at all, and says so in its own paragraph six lines away.

It is the hinge of the ruling rather than a stray sentence: `input_of` is the
one call that decides which nodes get the root treatment, so a reader sizing up
a per-root input — the alternative the item's fork left standing, and the one a
`footage` root over another file would need if the blend ever comes back — is
told by the function they start at that the decoded frame is already the
answer.

The criterion is the awkward part and is named rather than hidden: what has to
be true is that a paragraph agrees with code six lines from it, and any test of
that asserts words. The least dishonest shape, and what `done_when` reserves a
name for, is a case that reads both docstrings and pins the one word they must
not disagree about — that `input_of`'s `None` return is described as no input
layer and not as `result.source`, which is what `render_at`'s own paragraph
already says. A worker that judges the assertion worse than the prose it guards
should say so on the item and strike the case rather than write a green one; the
edit itself is three lines either way.
