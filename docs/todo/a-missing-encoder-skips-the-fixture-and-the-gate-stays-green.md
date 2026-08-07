---
title: A missing encoder skips the fixture and the gate stays green
status: awaiting-review
priority: low
phase: 0
gated_on: nothing
done_when: "uv run pytest \"tests/test_fixture_gate.py::test_skipping_synthetic_video_fails_the_run\" \"tests/test_fixture_gate.py::test_skipping_stirred_clip_fails_the_run\" \"tests/test_fixture_gate.py::test_a_run_with_no_fixture_skip_stays_green\" -q"
opened: 2026-08-07
---

# A missing encoder skips the fixture and the gate stays green

`synthetic_video` calls `pytest.skip("No usable mp4v encoder in this OpenCV
build")` when `VideoWriter.isOpened()` is false. That line came over verbatim
with the v2 port, and it reintroduces at runtime the exact shape the fixture's
own module docstring argues against — "a decoder test that skips is
indistinguishable from one that passes." `stirred_clip` carries the same two
lines. Ten test files across `unit`, `integration`, and `bench` now take one
fixture or the other, so the Phase-3 exposure this item was opened against has
already arrived: a runner whose OpenCV wheel loses mp4v turns the whole of that
coverage into a green gate with nothing behind it.

The fix is not in the fixture — the port is verbatim by decision. It belongs
wherever the gate is defined: a run that skips the synthetic-video fixture
should fail rather than pass, since every environment SIEVE supports is one
where writing an mp4 is a precondition, not an optional capability. `-p
no:randomly`-style flags are not the mechanism; something that reads the skip
count for that fixture, or `--strict-markers`-adjacent enforcement, is.

The criterion names three node ids because a gate that turns a skip into a
failure is trivially satisfiable by a gate that fails always: the two positive
cases pin that each fixture's skip is caught, and
`test_a_run_with_no_fixture_skip_stays_green` pins that an ordinary skip
elsewhere — or no skip at all — still leaves the run green. It is
`tests/test_fixture_gate.py` rather than a file under `unit/` because what it
asserts about is the fixture module beside it, not anything under `src/sieve`.

Low priority because the encoder is present on every build in play today
(opencv-python-headless 4.14 on Windows and on the CI runner). It becomes
urgent the first time an OpenCV bump is proposed.
