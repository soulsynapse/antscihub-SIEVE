---
title: A missing encoder skips the fixture and the gate stays green
status: open
priority: low
phase: 0
gated_on: nothing
opened: 2026-08-07
---

# A missing encoder skips the fixture and the gate stays green

`synthetic_video` calls `pytest.skip("No usable mp4v encoder in this OpenCV
build")` when `VideoWriter.isOpened()` is false. That line came over verbatim
with the v2 port, and it reintroduces at runtime the exact shape the fixture's
own module docstring argues against — "a decoder test that skips is
indistinguishable from one that passes." Today one test consumes the fixture;
by Phase 2 every decode test will, and a runner whose OpenCV wheel loses mp4v
turns the whole of that coverage into a green gate with nothing behind it.

The fix is not in the fixture — the port is verbatim by decision. It belongs
wherever the gate is defined: a run that skips the synthetic-video fixture
should fail rather than pass, since every environment SIEVE supports is one
where writing an mp4 is a precondition, not an optional capability. `-p
no:randomly`-style flags are not the mechanism; something that reads the skip
count for that fixture, or `--strict-markers`-adjacent enforcement, is.

Low priority because the encoder is present on every build in play today
(opencv-python-headless 4.14 on Windows and on the CI runner). It becomes
urgent the first time an OpenCV bump is proposed.
