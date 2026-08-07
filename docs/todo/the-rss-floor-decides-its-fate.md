---
title: The RSS floor decides its fate
status: done
priority: normal
phase: 3
gated_on: nothing
opened: 2026-08-07
---

# The RSS floor decides its fate

`tests/unit/test_machine.py`'s
`test_the_session_rss_reading_is_real_and_monotone_in_allocation` opens with
`assert before > 64 * MIB`, and that number is a property of whatever pytest
was told to collect rather than of `process_memory_bytes`. v3's suite reads
47 MiB alone and clears the floor only once the rest of the suite's imports
are in the process; v2's bare session cleared it by 20 KB, a margin nobody
chose. Measurements in
`findings/2026.08.07-the-rss-floor-measures-the-test-session-not-the-resolver.md`.

This item is the authorization the porting discipline requires: the floor is
in the cut list, so editing it is in scope here and nowhere else. 03.1's
review would not take it, because striking an assertion from a ported test to
make a criterion pass is the one move a reviewer must not make on its own.

The argument for striking it outright is that its discriminating power is
inverted. A resolver returning a fabricated large constant passes the floor;
a correct resolver in a small process fails it. The claim the floor is
supposed to carry — this is a reading, not a constant — is carried whole by
the two lines below it: allocate 64 MB, touch every page, and the delta must
exceed 32 MB. That catches a constant, a wrong unit (KB would give a delta of
~65 000), and a reading of the wrong process.

The argument against is that a floor with a real margin still documents the
units for free. If it stays, it stays at a number v3's smallest plausible
session clears by several times, not at one tuned to the tree as it is today,
because the suite only ever grows and a floor that tracks it proves nothing.

Whichever wins, the comment goes with it: "a Python process with numpy
loaded holds more" is the claim the measurement refuted, and leaving it
beside a changed number would preserve the reasoning that was wrong.

## Ruled 2026-08-07: struck

The floor is gone and the monotonicity assertion stands alone, with the
docstring rewritten to say why the floor is absent — a reader who wonders
where it went is the reader most likely to add it back. The comment went with
it. `uv run pytest tests/unit/test_machine.py tests/unit/test_pool_meter.py
tests/unit/test_ledger_sensors.py -q` is 15 passed, which is 03.1's criterion
green over the three files it names rather than over the whole suite.
