---
title: The synthetic video fixture ports verbatim
step: "00.4"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/test_fixture.py -q"
opened: 2026-08-06
---

# The synthetic video fixture ports verbatim

`synthetic_video` from v2's `tests/conftest.py`, unchanged, plus one test that
consumes it — a fixture nothing reaches is the vacuity shape the v2 audit
named. The stirred-clip fixture does not come yet; it arrives in Phase 5 with
the parity work that needs a clip that can disagree with itself.

## Done

`uv run pytest tests/test_fixture.py -q` → `1 passed in 0.11s`. Full gate:
`uv run ruff check . && uv run lint-imports && uv run pytest -q` → all checks
passed, 5 contracts kept, 39 tests passed.

The fixture body and its docstring are byte-identical to
`main:tests/conftest.py`. Around it, three things the port had to decide:

- **`FIXTURE_RATE` is not carried.** `Fraction(20)`, whose docstring points at
  `VideoMetadata.fps` — a v2 declaration nothing in v3 consumes, so PLAN's
  porting discipline refuses it. It returns with `core/types.py`'s rational
  media time if that type wants a fixture-side spelling to agree with.
- **The `QT_QPA_PLATFORM` line is not carried.** It is module setup for v2's
  Qt suite, not part of the fixture; v3 has neither PySide6 nor a GUI test.
- **OpenCV and numpy enter the dev group, not `dependencies`.** The fixture
  cannot exist without an encoder, and no shipped component decodes anything
  until Phase 2 promotes them. This also falsified a claim in `ci.yml`'s
  comment that OpenCV is never installed in CI; the comment is corrected to
  say what actually keeps the contracts honest, which is that grimp reads
  source and not the environment.

The consuming test asserts the fixture's real property rather than its stated
one — see
[findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md](../findings/2026.08.06-the-synthetic-fixture-identifies-frames-by-order.md).
The obvious assertion, decoded blue within half a step of `n * 5`, fails at 4.0
of 5 levels. Frames are strictly ordered and exactly uniform, which is what
frame identity actually rests on.
