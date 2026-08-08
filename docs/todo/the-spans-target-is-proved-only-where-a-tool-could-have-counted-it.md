---
title: The span's target is proved only where a tool could have counted it itself
priority: normal
phase: 3
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_executor.py -q -k bound_only_target"
opened: 2026-08-08
---

# The span's target is proved only where a tool could have counted it itself

`FrameSpan.lookahead` landed at ee6ffc5 so a windowed tool reads the frame it
was called about instead of counting back from the end of its window. The
argument for it — the one that chose the field over the `FrameSpan.centred_on`
constructor, and the one
[a-centred-window-counts-its-target-from-the-wrong-end.md](a-centred-window-counts-its-target-from-the-wrong-end.md)
calls the second cost — is that a tool declaring only `max_lookahead_frames`
has no per-configuration `k`: `ParamsBase.lookahead_frames` gives it
`NO_FRAMES`, it counts back zero, and it lands on the end of its window. The
span carries `node_lookahead_frames`' answer, which falls back to the bound, so
that tool now finds its target.

Nothing in the tree asserts that. Every fixture that reads `window.target` and
is *right* declares the refinement beside the bound — `_windowed`'s `centre2`
and `trail3` in `tests/unit/test_executor.py`, and `detect`, which declares
both. The one bound-only centred fixture, `WrongEndParams`/`_last_frame_run`,
exists to be refused. So the case that would go red if the span were fed
`params.lookahead_frames()` instead of `node_lookahead_frames` does not exist,
and the branch the change was made for is the one branch unexercised.

The consequence is visible as a green revert. Reverting `src/sieve/tools/
detect.py`'s hunk alone — putting back
`row = len(window) - 1 - params.lookahead_frames().frames` in place of
`row = window.target_row` — leaves all of `tests/unit/test_detect_tool.py`
green, because the two expressions are equal for every configuration in the
tree. `test_the_emitted_frame_is_the_target_and_not_the_end_of_the_window`
cannot separate them and never could; what it caught during the change was its
own `span_for` helper, not `run`
([findings/loop/2026.08.08-a-per-subject-revert-is-green-when-the-two-expressions-agree-on-every-fixture.md](../findings/loop/2026.08.08-a-per-subject-revert-is-green-when-the-two-expressions-agree-on-every-fixture.md)).

So the missing case belongs at the executor and answers for `detect` on the way
past: a windowed tool declaring only `max_lookahead_frames`, run through the
loop, reading `window.target` and emitting for it — and not refused by
`_run_node`'s index check, which is the assertion. Spell it `bound_only_target`.
A detect-level case cannot stand in for it: the divergence needs a span whose
`lookahead` differs from what the tool's own params would say, and that is a
window the loop never builds, so building one by hand asserts against a shape
that does not occur.

While the file is open: the middle assertion of
`test_a_centred_windows_span_target_is_the_frame_it_answers_for` compares
`TARGETS` to `[result.index for result in results]`, and `_mean_run` sets the
emitted index from the same `window.target` it appends to `TARGETS` — so given
the call returned at all, the two cannot differ. The case is not vacuous (it is
`_run_node`'s refusal that makes it red on the unchanged tree, and the two
assertions either side carry real content), but that line stands for a check it
is not making.
