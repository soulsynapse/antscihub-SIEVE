---
title: decode/ ports verbatim
step: "02.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_decode.py tests/unit/test_decode_format.py tests/unit/test_decode_workers.py -q"
opened: 2026-08-06
---

# decode/ ports verbatim

All six modules of `decode/`, byte-identical modulo imports (PLAN.md, porting
discipline); the three test files above port with them and run on
`synthetic_video` (00.4). ffmpeg presence is the environment's problem, not
the port's — if it is missing, that is a blocker note at the bottom of this
item, never a softened test.
