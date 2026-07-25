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

**ADR-018 is Accepted.** Kendrick's call. OpenCV VideoCapture is the pinned v1
decode path; the reopening conditions in the ADR stand unchanged.

**The budget table is data, and a test keeps it honest.**
`sieve/bench/budgets.py` transcribes `ARCHITECTURE.md` §1;
`tests/bench/test_budget_table.py` parses the table out of the document and
fails naming the row that moved. It caught a real difference on its first run
(an en dash in "5–10 s" against a hyphen in the transcription), which is the
evidence that it checks something rather than agreeing with itself. It is not
marked `slow`, so it runs in `checks` — the drift it catches is a documentation
edit and does not wait for a benchmark machine.

**Scrub decode measured: median 8.6 ms.** `tests/bench/test_decode_seek.py`
seeks to 64 deterministic pseudorandom frames in the H.264 8-bit corpus clip
through OpenCV and decodes. Against `DECODE_SHARE = 0.6` of the 50 ms scrub
budget — 30 ms allotted — the verdict is `within`, with roughly 21 ms of
headroom for color conversion and repaint. [ASSUMPTION] The 0.6 share is
judgement, not measurement; it is the number to replace once the repaint path
exists, and it is why a pass here is not a pass on the budget itself.

**Benchmarks report, they do not gate.** ADR-008 forbids a universal wall-time
threshold across heterogeneous machines, so the verdict lands in
`extra_info` and a human reads it. `SIEVE_BENCH_ENFORCE` makes a past-margin
regression a failure — the enforcement point is wired so the deferred CI gate
is a configuration change rather than a rewrite.

**One owner for the corpus manifest.** `sieve/bench/corpus.py` holds `Clip` and
`read_manifest`; `decoder_benchmark.py` now imports them instead of carrying
its own copy. The corpus is gitignored and regenerates deterministically, so
both readers skip with the regeneration command rather than failing on a
missing path.

**Code-health report exists and found something.** `tools/code_health.py`,
stdlib-only, run by `nox -s code_health` (no venv). Emits module size outliers,
fan-in/fan-out over the internal import graph, deep cross-layer reach,
suppression census, and brittle-test heuristics. Today it flags
`sieve.bench.decoder_benchmark` at 641 lines and lists the two config-level
exemptions this file has been tracking by hand. Never a gate: it exits non-zero
only when it cannot parse a file, because a report that can fail becomes a gate
and a gate accumulates suppressions.

**Decoder.** ADR-018 pins OpenCV VideoCapture as the single v1
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

**Qt and CuPy are optional extras; `dependencies` is what a headless run
needs.** Derived from §3's parity guarantee rather than from an ADR that says
so. `gui` carries PySide6, napari, and pyqtgraph; `gpu` carries CuPy per
ADR-016; `dev-gui` adds pytest-qt on top of both. The forcing case: pytest-qt
aborts collection when no Qt binding is importable, so leaving it in `dev`
makes a headless developer unable to run any test at all. [OPEN QUESTION]
Whether this split deserves its own ADR. It is a packaging consequence of an
accepted architectural rule, not a new decision, but it is the kind of thing a
later reader will look for an ADR to explain.

**The layer contract is verified, not just written.** `.importlinter` encodes
four contracts and each was confirmed to fail against a deliberate violation
before being trusted. The Qt contract catches PySide6 even though PySide6 is
not installed, because the analysis is static.

## Flagged, proceeding anyway

**PySide6 migration is unstarted.** ADR-001 selects PySide6 for licensing
reasons; the environment carries PyQt6 and its Qt binding. ADR-001 also
requires the napari embedding to be revalidated against PySide6 before first
production use. [INTENT] Handle as part of the first GUI commit rather than as
a standalone migration, since no GUI code exists to migrate yet.

**No license is declared.** There is no LICENSE file and `pyproject.toml`
carries no `license` field. ADR-001 chose PySide6 precisely to avoid being
bound by PyQt6's GPLv3, so a license position exists in the reasoning without
existing in the repository. Needs Kendrick's decision; nothing is blocked by it
until distribution.

**No console entry points are declared,** deliberately. `cli/` and `gui/` have
no module to point at, and a script naming a module that does not exist is the
exact stale-metadata failure this work replaced. They land with the commit that
creates the entry module.

**`checks` has no GUI coverage.** `test_gui` is a separate session because
pytest-qt cannot be installed into the headless environment. Costless while
`gui/` is empty. [OPEN QUESTION] Whether `test_gui` joins `checks` or stays a
separately-invoked CI job — decide at the first GUI commit, when the cost of
installing Qt into every gate run becomes real.

**Two files are exempted from both gates.** `bench/decoder_benchmark.py` and
`tests/benchmark_image_viewers.py` carry Ruff per-file ignores (PLC0415, E501,
PLR2004) and are listed in Pyright's `ignore`. Each exemption has its reasoning
written at the config site. These are suppressions rather than fixes: the
Pyright diagnostics are artifacts of PyAV, pyqtgraph, and napari stubs, and the
Ruff ones are rules that do not fit an executable experiment that emits
markdown tables. Imports are still analyzed, so a dependency that disappears
still fails the gate.

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

Session 2 — the gate exists and is green. `nox -s checks` runs Ruff, Pyright,
the layer contract, and the fast suite in about six seconds against a headless
environment with no Qt installed at all, which is what makes the parity claim
testable rather than asserted. Remaining phase-1 items are the benchmark
harness, the code-health report, the voice checker, and the corpus rewrite.

Session 3 — the benchmark harness and the code-health report both exist and
both found something on their first run. `nox -s checks` stays green; `nox -s
benchmark` and `nox -s code_health` are separately invoked by design.

The voice checker and the corpus rewrite are handed off rather than done, with
written prompts at `docs/06-ops/handoff-voice-checker.md` and
`docs/06-ops/handoff-voice-rewrite.md`. [INTENT] Both are transcription against
a decided standard rather than decisions, and the rewrite in particular is a
whole-corpus edit whose cost is context rather than judgement. The checker is
sequenced first because it is the rewrite's instrument: the rewriting agent
runs it, fixes what it names, and re-runs, so the pass is verifiable by a tool
rather than judged by eye.

Session 4 scope — open at Kendrick's call. The guardrail phase is complete
except for the two handed-off documentation items, so the next thing is either
the first vertical-slice code (the decode boundary at `io/video_read.py`, which
ADR-018 now licenses and which the scrub benchmark is waiting to measure
through) or clearing the open questions below.

## Phase 1 plan — guardrails

[INTENT] The order below is dependency order, not priority order. Each item is
verifiable on its own.

- [x] Packaging per ADR-012: `[project]` + `[build-system]` in
      `pyproject.toml`, Hatchling backend, `dev` extra, committed `uv.lock`.
      Distribution name `antscihub-sieve`, import package `sieve`. Entry points
      deliberately absent — see above.
- [x] `noxfile.py` per ADR-009 with the required session names. Sessions with
      nothing to run yet skip with a stated reason and carry a tripwire: when
      the precondition appears in the tree, the session fails and names what it
      now owes. Verified in both directions. A session that passes silently
      forever is worse than no session.
- [x] Ruff and Pyright gates wired per ADR-003, strict on `core/` and
      `pipeline/`, clean baseline established before enforcement.
- [x] Layer-enforcement contract encoding `ARCHITECTURE.md` §3 in
      `.importlinter`, including the Qt-free constraint on `core/`,
      `pipeline/`, and `bench/` and the `gui/`-never-imports-`workers/` rule.
      Written against layer packages that are otherwise empty, so the rule
      precedes the first import that could break it.
- [x] Benchmark harness with the §1 budget table as data rather than as
      assertions scattered through tests, plus environment metadata capture per
      ADR-008. One real measurement proves it end to end: `scrub-seek` decode
      at a median 8.6 ms against 30 ms allotted. `nox -s benchmark`.
- [x] Code-health report: `tools/code_health.py`, `nox -s code_health`. Signals
      worth a second look (module size outliers, fan-in/fan-out, deep
      cross-layer reach, suppression census, brittle-test heuristics). A report
      to read, not a gate to pass. Stdlib-only and deliberately outside `src/`,
      so extending it costs nothing and ships nothing.
- [ ] Documentation voice checker — flags imperative constructions and
      absolutes ("always", "never", "must") in `docs/` and reports untagged
      claims about runtime behaviour. A report first; a gate once the corpus
      passes it. **Handed off** — see `docs/06-ops/handoff-voice-checker.md`.
- [ ] Voice rewrite of the existing corpus against that checker: every ADR, the
      architecture doc, the vision and requirements prose. Sequenced after the
      checker so the pass is verifiable. **Handed off** — see
      `docs/06-ops/handoff-voice-rewrite.md`.
- [x] One end-to-end smoke test that grows with the vertical slice rather than
      one test per phase. `tests/test_smoke.py` today asserts every layer
      package imports and that no headless layer pulls in a Qt binding — the
      runtime counterpart to the static contract, checked in a subprocess so a
      lazy import inside a function body cannot hide. It is meant to be
      rewritten as the slice grows; that there is exactly one of it is the
      part to preserve.

**Ruff formats Python code blocks inside Markdown, and must not.** It silently
reformatted the snippets in `FILTER_CONTRACT.md` — collapsing an expanded class
stub and stripping aligned trailing comments, both of which carry meaning in a
specification. ADR-003 already scopes Ruff to Python source and says it is not
the gate for Markdown prose, so `extend-exclude = ["*.md"]` enforces what the
ADR states. Worth knowing before the voice-checker work: whatever tool checks
documentation is a separate decision, and it operates on files Ruff does not
touch.

## Environment notes

[STABLE] `uv` is not on the system PATH. It lives in the repository `.venv`,
installed with `python -m pip install uv`. Nox needs it findable to use the uv
venv backend, so the canonical local invocation puts `.venv/Scripts` on PATH
first; `nox.options.default_venv_backend` falls back to `virtualenv` when it
cannot. Sessions build their own environments under `.nox/` and reuse them, so
a dependency *removed* from `pyproject.toml` survives in a reused session env
until `.nox/` is cleared. CI creates them fresh and does not have this problem.

[STABLE] napari registers a pytest plugin, so it loads into any test session in
an environment where it is installed and emits Pydantic deprecation warnings
that have nothing to do with SIEVE code. The headless `dev` environment does
not have napari, so the gate output is clean; a `dev-gui` run will not be.

## Observations worth remembering

[STABLE] The decoder benchmark harness is importable at
`src/sieve/bench/decoder_benchmark.py` and the viewer comparison is at
`tests/benchmark_image_viewers.py`. Both are executable architectural
experiments rather than unit tests, and both are re-runnable — evidence for
ADR-001 and the pending decoder ADR can be regenerated rather than trusted from
a table.
