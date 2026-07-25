# NOTES

[INTENT] The connective tissue between sessions: what is in progress, what is
deferred and why, what needs Kendrick's decision, and what the code-health
checks have surfaced. ADRs carry decisions; PR descriptions carry the narrative
of a change; this file carries state. Entries stay short.

[STABLE] Orientation for a new session lives in
`docs/06-ops/00-agent-orientation.md`. This file is read first, that file
second.

---

## Resolved this session

**Decoder.** ADR-018 (Proposed) pins OpenCV VideoCapture as the single v1
decode path. Kendrick's steer: decide against the architecture goals, and treat
the determinism/dtype-honesty language as aspirational rather than load-bearing
at this stage. Seek accuracy is the property the scrub budget rests on and the
only property whose failure is invisible to the user; bit depth above 8 bits is
a bounded, reportable loss with no current consumer. The ADR records its own
reopening conditions — the untested seek-then-decode-forward mitigation is the
most likely path back.

**Documentation voice — applies everywhere, including ADRs, rewrite now.**
[INTENT] Sequenced so the voice guardrail script lands before the rewrite, so
the pass is verifiable rather than judged by eye. The rewrite covers every ADR,
the architecture doc, and the vision and requirements prose. New documents are
written to the standard from here regardless of the backlog — ADR-018 and the
`docs/06-ops/` digests are the worked examples.

**`bench/` stays Qt-free.** Architecture §3 and §14 amended: the metric bus
emits plain callbacks and the QObject adapter lives in `gui/`. Encoded as a
layer contract so the CLI and headless runs keep importing `bench/` without Qt.

## Flagged, proceeding anyway

**PySide6 migration is unstarted.** ADR-001 selects PySide6 for licensing
reasons; the environment carries PyQt6 and its Qt binding. ADR-001 also
requires the napari embedding to be revalidated against PySide6 before first
production use. [INTENT] Handle as part of the first GUI commit rather than as
a standalone migration, since no GUI code exists to migrate yet.

**Packaging does not yet match ADR-012.** `pyproject.toml` carries tool config
only — no `[project]`, no `[build-system]`, no lockfile. The installed
distribution metadata describes a package name and entry points that no longer
correspond to the source tree. [INTENT] First guardrail commit rebuilds this
against ADR-012 (Hatchling, PEP 621, uv, committed lock).

**Layer-enforcement tooling is a new top-level dependency** not covered by any
ADR. Named in `SIEVE-HANDOFF.md`, so treated as authorized; recording it here
because the handoff asks for new uncovered dependencies to be visible.

**`bench/` would import Qt if the metric bus lives there.** `ARCHITECTURE.md`
§14 places `metric_bus.py` (described as a QObject signal bus) in `bench/`,
which sits below `gui/` in the layer model. Legal under §3, which forbids Qt
only in `core/` and `pipeline/` — but it means the CLI cannot import `bench/`
without pulling in Qt. [INTENT] Keep `bench/` Qt-free and emit through plain
callbacks, with the QObject adapter living in `gui/`. Cheap now, expensive
after `bench/` has several consumers. Worth an architecture doc amendment if
accepted.

**`ARCHITECTURE.md` §12 illustrates deterministic GPU mode with Torch-only
API calls.** ADR-016 already states this language is not operative for v1 and
that CuPy-specific reproducibility contracts replace it. The architecture doc
has not been updated to match. [INTENT] Fold into the voice rewrite pass.

**Imperative phrasing to correct during the voice rewrite,** flagged per the
handoff's standing request. `ARCHITECTURE.md` §1 asserts "four commitments the
architecture never violates" and §1's budget table calls its numbers "hard
targets"; §6 and §7 state criteria as "must". The ADRs use "must", "never", and
bare imperatives throughout their `Decision` sections. These read as absolutes
where most are intents with conditions attached — the rewrite is the place to
say which are which, and that is a content question, not a wording one.

## Deferred, with reasons

- **Determinism CI.** Wanted early and cheaply, but a byte-comparable canonical
  clip needs a decode path and at least one filter. Revisit at first filter.
- **Filter-contract property tests.** The Hypothesis strategy generator derives
  from a filter's Pydantic model; building it before any such model exists
  would be speculative. The `tests/contract/` harness location is fixed by
  ADR-008; it gets populated with the first filter, not before.
- **Latency benchmarks in CI.** The harness and the budget table land early;
  the interactive-loop budgets cannot be measured before the interactions
  exist. ADR-008 warns against a universal wall-time threshold across
  heterogeneous machines, so the gate needs recorded environment metadata
  before it can fail a build honestly.
- **Missing load-bearing specs.** `ARCHITECTURE.md` indexes several contract
  documents that are not yet written. None block the pre-pipeline loop.
  `PREVIEW_SEMANTICS`, `WORKER_PROTOCOL`, and `DETERMINISM_POLICY` become
  blocking at first filter execution; the rest at their respective features.
- **Empty requirement files.** `docs/01-vision/ui-vision.md` and
  `docs/02-requirements/BATCH_CONTRACT.md` exist with no content.

## In progress

Session 1 — orientation and planning. Docs read; `docs/06-ops/` digests
written so later sessions need not reload the tree; ADR-018 drafted;
architecture amended for the decode boundary and the `bench/` Qt rule. No
feature code — per `SIEVE-HANDOFF.md` that waits on confirmation, and the
guardrails come first regardless.

Session 2 scope — guardrails through the layer contract, then the voice
checker. The doc rewrite follows the checker so it can be verified.

## Phase 1 plan — guardrails

[INTENT] The order below is dependency order, not priority order. Each item is
verifiable on its own.

- [ ] Packaging per ADR-012: `[project]` + `[build-system]` in
      `pyproject.toml`, Hatchling backend, `dev` extra, committed `uv.lock`,
      console entry points matching the actual source tree.
- [ ] `noxfile.py` per ADR-009 with the required session names. Sessions that
      have nothing to run yet exist and pass trivially rather than being
      omitted — the automation interface is the contract, and CI calls session
      names, not their internals.
- [ ] Ruff and Pyright gates wired per ADR-003, strict on `core/` and
      `pipeline/`, clean baseline established before enforcement.
- [ ] Layer-enforcement contract encoding `ARCHITECTURE.md` §3, including the
      Qt-free constraint on `core/` and `pipeline/` and the
      `gui/`-never-imports-`workers/` rule. Contracts are written for layers
      that do not exist yet, so the rule is in place before the first import
      that could violate it.
- [ ] Benchmark harness skeleton with the §1 budget table as data rather than
      as assertions scattered through tests, plus environment metadata capture.
      One real measurement to prove the harness works end to end — decode-seek
      latency is measurable today against the existing corpus.
- [ ] Code-health report: a Nox session emitting signals worth a second look
      (file size outliers, cross-layer function reach, fan-in/fan-out,
      brittle-test heuristics). A report to read, not a gate to pass. Designed
      to be cheap to extend as the useful signals become known.
- [ ] Documentation voice checker — flags imperative constructions and
      absolutes ("always", "never", "must") in `docs/` and reports untagged
      claims about runtime behaviour. A report first; a gate once the corpus
      passes it.
- [ ] Voice rewrite of the existing corpus against that checker: every ADR, the
      architecture doc, the vision and requirements prose. Sequenced after the
      checker so the pass is verifiable.
- [ ] One end-to-end smoke test that grows with the vertical slice rather than
      one test per phase.

## Observations worth remembering

[STABLE] The decoder benchmark harness is importable at
`src/sieve/bench/decoder_benchmark.py` and the viewer comparison is at
`tests/benchmark_image_viewers.py`. Both are executable architectural
experiments rather than unit tests, and both are re-runnable — evidence for
ADR-001 and the pending decoder ADR can be regenerated rather than trusted from
a table.
