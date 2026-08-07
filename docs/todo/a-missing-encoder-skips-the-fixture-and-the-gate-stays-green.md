---
title: A missing encoder skips the fixture and the gate stays green
status: awaiting-review
priority: low
phase: 0
gated_on: nothing
done_when: "uv run pytest \"tests/test_fixture_gate.py::test_skipping_synthetic_video_fails_the_run\" \"tests/test_fixture_gate.py::test_skipping_stirred_clip_fails_the_run\" \"tests/test_fixture_gate.py::test_a_run_with_no_fixture_skip_stays_green\" \"tests/test_fixture_gate.py::test_an_unguarded_fixture_skip_stays_a_skip\" \"tests/test_fixture_gate.py::test_the_nested_runner_pins_the_child_encoding\" -q"
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

## Reopened after review of 3a4db10

The gate that landed is right and the two positive cases are honest; two
defects sent it back, and the criterion above gained a node id for each.

`test_skipping_stirred_clip_fails_the_run` is green only where
`PYTHONIOENCODING` says utf-8. `pytester.runpytest_subprocess` reads the child
session's output as utf-8 while the child writes the locale encoding, and
`stirred_clip`'s docstring — echoed into the fixture-error traceback — carries
an em dash, so on a bare Windows shell the assertion never runs and the test
dies on `UnicodeDecodeError`
(`docs/findings/loop/2026.08.07-a-nested-pytest-session-is-decoded-as-utf-8-and-only-the-harness-env-makes-that-true.md`).
`test_the_nested_runner_pins_the_child_encoding` is the criterion for the fix:
the nested runner must set the child's encoding rather than inherit it, and a
test has to assert that it does, because no shell incantation in a `done_when`
is portable enough to stand in for it.

`test_a_run_with_no_fixture_skip_stays_green` does not reach the branch it was
minted to protect. Its ordinary skip is a `@pytest.mark.skip`, raised in the
call phase, which `pytest_fixture_setup` is never handed — so replacing
`if fixturedef.argname not in FATAL_FIXTURE_SKIPS:` with `if False:` leaves all
three cases passing
(`docs/findings/loop/2026.08.07-a-control-that-skips-by-mark-cannot-see-a-hook-that-only-watches-fixtures.md`).
`test_an_unguarded_fixture_skip_stays_a_skip` needs a fixture outside the
frozenset that skips, and that skip must arrive as a skip.

Both corrections land in `tests/test_fixture_gate.py`; `tests/conftest.py` is
untouched, because neither defect was in the gate — the gate was narrow all
along and nothing exercised the narrowness, and the encoding was never the
gate's to choose. The nested runner now sets `PYTHONIOENCODING` for the child
instead of passing on whatever the parent had, and the new control declares a
fixture in the nested conftest that skips during setup, which is the only place
`pytest_fixture_setup` can see it. Each was watched fail before it passed: with
the `setenv` removed, `test_skipping_stirred_clip_fails_the_run` and
`test_the_nested_runner_pins_the_child_encoding` both fail in a shell that
exports nothing; with the membership test replaced by `if False:`,
`test_an_unguarded_fixture_skip_stays_a_skip` fails while the other four pass.
