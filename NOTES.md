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

**The decode boundary exists.** `src/sieve/io/video_read.py` is the module
ADR-018 licensed: `VideoReader` over a pinned OpenCV VideoCapture, index-based
seek-and-decode, `SourceInfo` carrying the source's bit depth beside the uint8
BGR it delivers, and `DecoderIdentity` for the §12 code-version hash.
`tests/io/test_video_read.py` covers the contract in 16 tests, unmarked so they
run in `checks`. `tests/bench/test_decode_seek.py` now measures through the
boundary instead of reaching `cv2` directly, and its `[STALE WHEN]` is
discharged.

The bit-depth report is the part worth knowing about. OpenCV exposes source
depth only through `CAP_PROP_CODEC_PIXEL_FORMAT`, whose value is a fourcc:
`I420` for the 8-bit encodes, and FFmpeg's planar-YUV tags — `MKTAG('Y','3',11,10)`
— for the 10-bit ones, which carry depth in a raw byte rather than as text.
An unrecognized tag reports `None` rather than defaulting to 8, because a
warning that silently says "no depth lost" in the one case it cannot read is a
warning that fails where it is needed. The corpus manifest already records
`expected_bit_depth` per clip, so the test asserts the decode across all five
codecs against a number written down independently of OpenCV.

[ASSUMPTION] Kept out of the boundary for now: the keyframe index, the ring
buffer, and eager head-decode that `ARCHITECTURE.md` §5.5 also asks of this
module. They exist to keep a widget fed, no widget exists, and a buffering
policy built before its consumer is tuned against a guess.

**Session 3's number holds through the boundary.** The scrub measurement reads
8.2, 9.2, and 10.1 ms median across three consecutive runs on this machine
against 30 ms allotted — the ~±1 ms run-to-run spread swamps the wrapper's
cost, and session 3's 8.6 ms sits inside it. Worth recording as the noise floor
the deferred CI gate has to clear, since a regression margin narrower than the
spread would fire on thermal state.

**`test_gui` joins `checks`, by notification rather than inline.** Kendrick's
call. `checks` calls `session.notify("test_gui")`, so the GUI suite builds its
own `dev-gui` environment and the `checks` environment stays installed from
`dev` alone. Inlining it would have put a Qt binding into the environment
`_test` uses to demonstrate the headless guarantee, which is the one place that
guarantee is observed. The session skips with a stated reason while no test
carries the `qt` marker — pytest exits 5 on an empty collection, so a gate
wired to it would otherwise fail for having nothing to do. Verified in both
directions.

**ADR-019 records the extras split.** Kendrick's call, against the argument
that a derived decision does not need one: ADRs are cheap and the archaeology
they prevent is not. `pyproject.toml` carries the generating rule as a comment
block at the extras — a package belongs in `dependencies` when a CLI or HPC run
with no display and no GPU would fail without it — pointing at §3 and ADR-016.
No code changed; the split was already built this way.

**The license is deferred.** Kendrick's call, not an oversight. Nothing is
blocked by it until distribution, and ADR-001's PySide6 choice already fixes
the constraint the eventual answer has to satisfy.

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
needs.** Now ADR-019 — see "Resolved this session".

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

**No license is declared,** deliberately deferred. There is no LICENSE file and
`pyproject.toml` carries no `license` field. ADR-001 chose PySide6 precisely to
avoid being bound by PyQt6's GPLv3, so a license position exists in the
reasoning without existing in the repository. [STALE WHEN] Distribution becomes
real — that is the point at which the deferral stops being free.

**No console entry points are declared,** deliberately. `cli/` and `gui/` have
no module to point at, and a script naming a module that does not exist is the
exact stale-metadata failure this work replaced. They land with the commit that
creates the entry module.

**`checks` will get slower at the first GUI test.** `test_gui` is now notified
by `checks`, so the first `qt`-marked test turns the gate from one `dev` install
into two, the second of which carries PySide6 and napari. That cost is the
decision, not a surprise; recording it because a seven-second gate is a habit
and a two-minute one is a thing people start skipping. If it bites, the lever
is a CI job that runs `checks` and `test_gui` as separate parallel jobs, which
the session split already permits.

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

Session 4 — the voice checker has landed as `tools/doc_voice.py` with a
`nox -s doc_voice` session (report by default, `--gate` for later CI wiring).
Two defects were fixed on receipt: it crashed printing its own report on a
cp1252 Windows console, and it failed `ruff format --check`. The corpus rewrite
is still in flight, so the docs are unrewritten: 971 findings across the tree,
542 in the main body and 429 in ADRs. [ASSUMPTION] The `runtime` check fires on
policy prose that merely uses a word from its vocabulary — the flag-and-continue
list in `00-agent-orientation.md` is one — so the count overstates the rewrite's
real surface. Worth a look once the rewrite settles the true number.

The session-shape and stopping-point rules from `SIEVE-HANDOFF.md` are now
restated in `docs/06-ops/00-agent-orientation.md` rather than living only in the
handoff. [INTENT] Kendrick's ask: a session declares its checkpoint goal at the
start and knows where it halts without reading the handoff, so the two-file
read-set stays sufficient.

Session 4 checkpoint — the decode boundary exists and the benchmark measures
through it. Done: `io/video_read.py`, its 16-test contract suite, the
`test_decode_seek` refactor onto it, `test_gui` notified by `checks`, ADR-019
and the `pyproject.toml` rule block, the orientation's session-shape and
stopping-point sections, and the voice checker's two defects. `nox -s checks`
green in seven seconds; `nox -s test_gui` skips with a reason.

Session 5 — the video viewer, which is where the pre-pipeline loop starts
having a feel. It is also the first `[STOP]` in `SIEVE-HANDOFF.md`: the loop
running end to end wants a screen recording before anything moves past it. The
things this session deferred land there rather than earlier, because they are
tuned against the widget they feed: the keyframe index, the ring buffer, eager
head-decode on open, and the decoder thread. `DECODE_SHARE = 0.6` becomes
replaceable with a measured repaint cost at the same point. The first
`qt`-marked test also arrives, which is what turns `test_gui` from a logged
skip into a real leg of the gate — expect the gate's wall time to change that
day.

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
- [x] Documentation voice checker — flags imperative constructions and
      absolutes ("always", "never", "must") in `docs/` and reports untagged
      claims about runtime behaviour. A report first; a gate once the corpus
      passes it. `tools/doc_voice.py`, `nox -s doc_voice`, stdlib-only, with
      `--gate` as the wired enforcement point on the same pattern as
      `SIEVE_BENCH_ENFORCE`. Brief at `docs/06-ops/handoff-voice-checker.md`.
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

[ASSUMPTION] On Windows, the first `nox -s checks` after a source edit fails
reproducibly with `failed to remove directory ...antscihub_sieve-0.1.0.dev0.dist-info:
Access is denied (os error 5)`, and the immediate retry succeeds. It looks like
a scanner or an indexer holding the freshly built `dist-info` while uv tries to
replace it, which would make it a local-environment property rather than a repo
one — CI creates environments fresh and has not shown it. Recorded because
retrying looks like flakiness in the gate and is not.

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
