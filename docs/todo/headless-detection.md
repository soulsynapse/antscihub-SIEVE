---
title: The detector has no headless home
status: open
opened: 2026-07-28

gated_on: >
  nothing structurally — the primitives are in core/ already and only the glue
  is misplaced

reads:
  - src/sieve/gui/chain_model.py
  - src/sieve/core/detection.py
  - src/sieve/core/pipeline_model.py
  - src/sieve/cli/run_cmd.py
---

# The detector has no headless home

`DetectorSettings` is a first-class field on `Project` — serialized, versioned
(schema v3), resolved per replicate by `resolved_detector`, and hashed. The
primitives it names are in `core/`: `core/wavelet.py` for the transform,
`core/detection.py` for `gate_intervals`. But the one function that composes
them into an answer, `recompute` in `gui/chain_model.py`, is under `gui/`.

`sieve.gui` and `sieve.cli` are siblings in `.importlinter`'s layers contract,
so the CLI cannot import it. The consequence, checkable in one command: `sieve
run` decodes, executes, and prints a frame count. There is no path from a saved
project to detected intervals that does not start a Qt application.

**Why this is a defect and not a gap.** The document declares an answer that
only one front end can compute. Rule 2 says the pipeline is a data structure
and the complete input to rule 1's one path — that holds for frames and fails
for the thing frames are computed *for*. It also quietly falsifies a premise the
deferred HPC item rests on (docs/todo/hpc-handoff-and-review-mode.md): "HPC is
not a special path, it consumes the same serialized DAG the CLI does." True of
the executor, not true of detection, and the item does not know that yet.

**The boundary, decided.** A new `src/sieve/detect/` sitting below both front
ends — under `sieve.pipeline` in the layers contract, above `sieve.core` — is
the home. What crosses into it:

- **In:** a resolved `DetectorSettings`, the collected `(T, B)` series, `fps`,
  the series' `start_index`, and `workers`. All of those are already
  `recompute`'s arguments in everything but name.
- **Out:** band power, the gated intervals in absolute frames, and the settled
  frontier.
- **Not crossing:** `DetectorState`. It is the GUI's mutable tuning state — it
  carries `solo_block`, which `recompute` provably never reads (see
  `docs/completed-todo/2026.07.28-hover-to-solo.md`), and the cheap/expensive
  tier distinction is a GUI scheduling concern. `DetectorState.to_settings()`
  already exists; the GUI calls it at the boundary and `sieve.detect` never
  learns the type.
- **Not crossing either:** `Project`. If a `Project` appears in the new
  module's signature the extraction has failed — resolution to a
  `DetectorSettings` is `core/pipeline_model.py`'s job and already done.

**Two things fall out once the module exists**, and both are the point rather
than extras: a `sieve detect` command that takes a project and prints or writes
intervals, and detector tests that do not need `pytest.mark.gui`.

**The `workers` argument is the tell that this was already known.**
`recompute`'s docstring explains at length that `workers` is required with no
default because a default let the GUI run a full Morlet transform on the GUI
thread. A parameter that must be passed explicitly because its policy home is
unreachable is the same misplacement seen from the other side — see
docs/todo/machine-share-policy-is-above-its-consumers.md.
