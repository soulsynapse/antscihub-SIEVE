---
title: sieve detect collapses into sieve run
status: open
opened: 2026-07-29
priority: normal
gated_on: nothing
after: [detection-is-a-filter, sink-writers]
reads: [src/sieve/cli/detect_cmd.py, src/sieve/cli/run_cmd.py, src/sieve/detect/tables.py]
---

# sieve detect collapses into sieve run

With detection a filter and a table sink writable, `sieve detect` is `sieve
run` with a sink — one command, one path, and the CLI stops holding a second
composition of the detection chain (the `ALL_CORES` on one side,
`resolve_worker_split().detector` on the other split dies with it).

What must survive the collapse, because it is settled and correct: the
two-table export (series = measured, intervals = claimed; one wide table
would make a threshold change read as a new measurement), `repr` numbers, and
absence-as-missing-file-plus-NA. Those rows move from `detect/tables.py`'s
hand-authored world into the sink's, reading declared channel names
(`a-filter-names-what-it-emits`); the semantics do not change.
