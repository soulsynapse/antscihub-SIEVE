---
title: crop lands
step: "04.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_crop.py tests/unit/test_crop_artifact.py -q"
opened: 2026-08-06
---

# crop lands

`tools/crop.py` in the ADR-2 shape. `storage/crop_writer.py` is already here
— it landed with 02.1, whose decode test needed `write_ffv1` for its
NTSC-rate fixture — so what this item adds is the tool and the wiring, and
the writer is read, not written. Parity against v2 goldens per 02.4's
mechanism. The region param declares its `region` stereotype (01.4) and
nothing else about the GUI — the canvas handoff is Phase 7's business. No
per-tool `.md`: PLAN's open question decides that later, and creating one
now would preempt it.
