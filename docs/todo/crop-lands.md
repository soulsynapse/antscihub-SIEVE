---
title: crop lands
step: "04.1"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_crop.py tests/unit/test_crop_artifact.py -q"
opened: 2026-08-06
---

# crop lands

`tools/crop.py` in the ADR-2 shape. `storage/crop_writer.py` is already here
— it landed with 03.2, whose decode test needed `write_ffv1` for its
NTSC-rate fixture — so what this item adds is the tool and the wiring, and
the writer is read, not written. Parity against v2 goldens per 03.7's
mechanism. The region param declares its `region` stereotype (01.4) and
nothing else about the GUI — the canvas handoff is Phase 7's business. No
per-tool `.md`: guidance is not a file in v3 — what the tool is for goes in
its module docstring and is promoted to a spec field in Phase 7, when the
expander that shows it exists.
