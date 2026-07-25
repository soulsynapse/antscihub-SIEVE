# Agent orientation

[INTENT] This file plus `NOTES.md` is the intended read-set for starting a
session. The `docs/` tree costs a large fraction of a context window to load
whole, and most sessions need one slice of it. The digests exist so that
loading the whole tree is a deliberate choice rather than the default.

[STALE WHEN] The layer model in `ARCHITECTURE.md` §3 changes, a latency budget
in §1 changes, or a digest stops matching its source. Digests are derived;
sources win on disagreement.

## Read order

1. `NOTES.md` (repo root) — running state, in-progress work, open questions.
   Single file, no subdirectory: coordination lives in exactly one place.
2. This file.
3. `docs/06-ops/architecture-digest.md` — layer model, budgets, contracts.
4. `docs/06-ops/adr-digest.md` — one entry per ADR, keyed to its number.

Reading past that is task-driven. The routing table says when.

## Document tree invariants

- `docs/01-vision/` — what the product is for, in the maintainer's framing.
  Prose, not specification. Read when a decision needs its "why".
- `docs/02-requirements/` — contracts a subsystem must satisfy, one file per
  contract. `ARCHITECTURE.md` states criteria; these state the specification.
- `docs/04-architecture/` — `ARCHITECTURE.md` commits to structure and
  boundaries and defers each load-bearing contract to its own file.
  `ARCHITECTURE-TREE.md` maps every architectural choice to the ADR that made
  it, so it is the fastest path from "what decided this?" to a filename.
- `docs/05-adr/` — one decision family per file, `ADR-NNN-kebab-title.md`.
  Numbers are never reused and never renumbered. A reversal is a new ADR that
  supersedes an old one; ADRs are not edited into a new decision. Template at
  `.adr-template.md`. A file whose `Status` is not `Accepted` is not binding.
- `docs/06-ops/` — operational material for whoever is working the repo:
  digests, runbooks (`.template-runbook.md`), and `handoff-*.md` briefs.
  Derived, disposable, rewritable. A handoff brief is self-contained by
  construction: it is written for an agent that will not read the rest of this
  tree, so it restates what it needs rather than pointing at it.
- `docs/07-resources/` — external references. Nothing depends on it.

## Routing table — when the full document earns its tokens

| Task | Read in full |
| --- | --- |
| Implementing or changing a filter | `docs/02-requirements/FILTER_CONTRACT.md` |
| Worker lifecycle, IPC, cancellation | ADR-015, ADR-002, ADR-017 |
| Pre-pipeline loop (open, scrub, replicate) | `ARCHITECTURE.md` §5.5, `docs/01-vision/replicate-vision.md` |
| Persisting arrays | ADR-014 |
| Benchmark results or the metric bus | `docs/01-vision/benchmarking-vision.md`, ADR-013, ADR-010 |
| GUI panels and layout | `ARCHITECTURE.md` §15, §15.5, `docs/01-vision/workflow-vision.md` |
| Adding a GPU path | ADR-016, ADR-011 |
| Tracing "what decided this?" | `ARCHITECTURE-TREE.md`, then the ADR it names |

[ASSUMPTION] A digest entry suffices to judge whether a change is *consistent*
with a decision, and does not suffice to judge *how* to implement against one.
The routing table covers the second case.

## Documentation voice

[STABLE] Descriptive voice, not imperative. Epistemic tags appear wherever the
confidence level is load-bearing: `[STABLE]` `[ASSUMPTION]` `[INTENT]`
`[STALE WHEN]` `[OPEN QUESTION]`. A claim about runtime behavior that carries
no tag is an unmarked assumption and should acquire one or a source pointer.

[OPEN QUESTION] Whether the voice rule reaches ADR `Decision` sections, which
are imperative by genre. Unresolved — see `NOTES.md`.

## Environment invariants

[STABLE] The repository virtual environment is `.venv` at the repo root; on
Windows the interpreter is `.\.venv\Scripts\python.exe`. Validation commands
run through that interpreter rather than a globally-resolved `python`.

[STABLE] Ordinary Qt tests run under `QT_QPA_PLATFORM=offscreen`. Renderer
measurements do not: napari's VisPy canvas needs a real OpenGL context, and
offscreen timings are not renderer timings.

[STALE WHEN] The packaging work in `NOTES.md` lands. ADR-012 moves environment
creation to uv from `pyproject.toml`, which supersedes the `.venv`
pass-through policy this section describes.
