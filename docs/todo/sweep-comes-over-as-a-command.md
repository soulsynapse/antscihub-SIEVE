---
title: sweep comes over as a command
step: "05.3"
status: deferred
gated_on: "PLAN's open question about bench/sweep.py, which has no disposition in either direction and is the whole of what this command runs"
done_when: "uv run pytest tests/unit/test_sweep.py -q"
opened: 2026-08-07
---

# sweep comes over as a command

`cli/sweep_cmd.py` port-with-rename: the command that measures decode
throughput across worker counts and prints the table you pick a setting
from. Its only real dependencies are `bench/sweep.py` and `decode/reader`.

Deferred before it starts, and deliberately so. `bench/sweep.py` appears
nowhere in PLAN.md's port disposition — not verbatim, not renamed, not
re-derived, not dropped — and this command is a thin front end over it, so
doing the work means deciding the module's fate in passing. That is the
disposition gap the plan's open questions now name. The criterion above is
v2's own test file and stands whichever way the ruling goes, so what the
ruling unblocks is the work, not the measurement of it.
