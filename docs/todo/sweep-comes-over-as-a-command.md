---
title: sweep comes over as a command
step: "06.4"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_sweep.py -q"
opened: 2026-08-07
---

# sweep comes over as a command

`bench/sweep.py` verbatim and `cli/sweep_cmd.py` port-with-rename: the
instrument that sweeps a cost over core sets and worker counts and reports
the curvature of the surface, so a worker constant can be judged rather than
believed.

It lands in this phase because of what 03.1 did. `mutual/shares.py` came over
verbatim with its caps and shares intact, every one of them chosen on v2's
machine, and nothing since has asked whether they hold here. Sweep is the
only thing in either repo that can answer it: a flat optimum means the
constants are harmless wherever they came from, a sharp one means they are
wrong everywhere they were not measured. Having imported them, this repo owns
the question.

Affinity is the machine axis and `mutual/machine.py` is what reports it, so
the module has its dependency already. `tests/unit/test_sweep.py` is the
criterion.

The reading it produces is a `docs/findings/` file in the same session, with
the machine named — a curvature reported in a passing test tells the next
reader nothing about which way the constants should move.
