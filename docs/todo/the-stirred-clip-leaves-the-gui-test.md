---
title: The stirred clip leaves the GUI test and becomes a fixture
step: "05.5"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/integration/test_stirred_clip.py -q"
opened: 2026-08-07
---

# The stirred clip leaves the GUI test and becomes a fixture

The oracle needs footage that can disagree with itself — `synthetic_video`'s
frames are told apart by their order
(`findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md`),
which makes it perfect for "did every frame arrive" and useless for "did the
two implementations compute the same thing". In v2 that clip is built inside
`tests/gui/test_gui_cli_parity.py`, which is the whole reason v2's parity
oracle could not run without Qt installed.

Here it is a shared fixture beside `synthetic_video` in `tests/conftest.py`,
and this item's test is what proves it earns the name: the clip must produce
a signal that varies frame to frame in a way a windowed tool can disagree
about, asserted directly, not assumed. Cheap enough to build per session, or
it will not be used.

No CLI work here. 05.6 and Phase 6 are the consumers.
