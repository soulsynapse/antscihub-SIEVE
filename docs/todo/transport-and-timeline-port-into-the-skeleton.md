---
title: Transport and timeline port into the skeleton
step: "07.6"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_timeline.py tests/gui/test_player_scrub.py -q"
opened: 2026-08-08
---

# Transport and timeline port into the skeleton

Port-with-care of v2's `gui/transport/` and `gui/timeline/` — the two GUI
contracts that held in v2 — into 07.4's skeleton, under the porting
discipline: the ported v2 tests are the spec, and a test that must change to
pass is a decision written at the bottom of this item, not an adaptation. The
canvas plays and scrubs footage through the decode path, and the timeline is
v2's scrubber at the height VISION gives it. The criterion names whole ported
modules rather than `-k` claims because for a port the module *is* the claim:
it passes as v2 wrote it or the item stops.

This is the pre-pipeline regime's surface (open → first frame, scrub →
repaint, release → exact frame); the numbers are taken through the GUI at
07.11, not here. Canvas and widget-control stay one package — PLAN.md's one
boundary *not* to draw — so nothing in this item minted an import fence
between them.
