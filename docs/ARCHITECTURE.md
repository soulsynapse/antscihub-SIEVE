# SIEVE — Minimal Architecture Reference

SIEVE is a video signal-processing tool built around one question: how much economy can the user buy back without losing signal? The architecture serves the ability to answer that question interactively for a representative clip, then execute the answer over the full dataset locally or on HPC.

This tool's value is first measured in speed. Speed has two distinct regimes, and both are load-bearing:

Pre-pipeline speed — from opening a video to having replicates cut and a clip selected. The intended feel is a video editor rather than a distributed system.

In-pipeline speed — from dragging a slider to seeing the graph update. The intended feel is direct manipulation rather than job submission.

## Layer Diagram

```
┌───────────────────────────────────────┐
│  gui/          cli/                   │  UI (Qt / terminal)
├───────────────────────────────────────┤
│  bench/                               │  Observation (latency checks)
├───────────────────────────────────────┤
│  pipeline/     (DAG, executor, cache) │  Orchestration
├───────────────────────────────────────┤
│  io/                                  │  Video decode / file I/O
├───────────────────────────────────────┤
│  core/         (filters, dtypes)      │  Pure logic — no imports from above
└───────────────────────────────────────┘
```

The enforced consequences: `core/` imports nothing above it and no
Qt, Zarr, or subprocess. `pipeline/` does not import Qt. `bench/` does not
import Qt, so headless and CLI runs can observe without a GUI toolkit — the
QObject adapter over the metric bus lives in `gui/`. `gui/` reaches `workers/`
only through `pipeline/`. This is the mechanism that makes CLI and HPC parity
real rather than aspirational; a violation is a product regression rather than
a style problem.

The rule is encoded as a machine-checked contract rather than
enforced by review.

---

## Non-Negotiables

|#|Rule|Meaning|
|---|---|---|
|1|Filesystem is truth _at rest_|Materialized artifacts are readable without SIEVE running. During interactive tuning, truth lives in memory.|
|2|Pipeline is a data structure|Serializable DAG. No GUI-only state in the pipeline artifact.|
|3|Filter = one class + one markdown|Discovery is automatic. No registration elsewhere.|
|4|No latency budget misses|A miss is a defect, not a tradeoff.|
|5|No regime tradeoffs|Don't improve pre-pipeline at cost to in-pipeline or vice versa.|

---

## Two Speed Regimes

```
PRE-PIPELINE (feels like a video editor)
  Open file → first frame:        < 500 ms
  Scrub/seek → frame repaint:     < 50 ms
  Cut confirmed → ready:          < 200 ms

IN-PIPELINE (feels like direct manipulation)
  First filter → first graph tick: < 2 s
  Slider drag → preview repaint:   < 100 ms
  Slider drag → graph update:      < 200 ms
  Full preview render (5–10s clip): < 3 s
```

---

## Import Boundaries

- `core/` — no Qt, no Zarr, no subprocess, no imports from upper layers
- `pipeline/` — no Qt (CLI and HPC must run headless)
- `bench/` — no Qt (headless benchmarks)
- `gui/` — reaches pipeline through `pipeline/` public API only

---

## Pipeline Model

- DAG (directed acyclic graph), not a linear list
- A linear chain is valid — it's just a degenerate DAG
- Cache keys include upstream content hashes
- Materialization is user-initiated or pressure-triggered, not automatic per step

---

## Extension Pattern

```
src/sieve/core/filters/
  my_filter.py      ← one class implementing FilterContract
  my_filter.md      ← guidance doc (discovered automatically)
```

That's it. GUI, CLI, cache, and HPC discover it without changes elsewhere.