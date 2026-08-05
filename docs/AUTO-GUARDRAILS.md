---
status: current
reviewed: 07c379e
subjects: [noxfile.py, .github/workflows/, pyproject.toml, tests/docs/, .importlinter]
---

# AUTO-GUARDRAILS

Guardrails exist so the constraints do not have to be held in your head. Build
them, then trust them and move fast.

CI is real: `.github/workflows/ci.yml` runs `uv run nox -s checks benchmark` on
every push and PR, which is ruff + ruff format + pyright strict + import-linter +
the full suite + the timed benchmarks. So "enforced" below means enforced.

**Each guardrail names the artifact that enforces it and states honestly how
much of it is covered.** That last part is the fix for what this file used to
do: it wrote "**Check:** <the test that should exist>" in the same voice for
checks that existed and checks that did not, so three unbuilt checks read as
done for two weeks. A guardrail with no check is a guardrail nobody is keeping —
write it as **OPEN** and it stays visible.

---

## 1. Import boundaries — ENFORCED, with one open half

- `core/` imports nothing above it, and no Qt, Zarr, or subprocess.
- `pipeline/`, `bench/`, `cli/`, `decode/`, `filters/`, `backend/` import no Qt.
- `core/`, `bench/`, `gui/`, `cli/` import no `cv2`. `filters/` deliberately may.

**Enforced by:** `.importlinter`, five contracts, run by `nox -s imports` inside
`checks`. The fifth (`gui-computes-nothing`, 2026-07-29) is §9's — the layer
contract governs direction of dependency and could never say it.

**OPEN:** "`gui/` never bypasses `pipeline/` to reach `workers/`" is not
expressible in the current contract and is not checked. `pipeline/` and
`(workers/)` are siblings on one tier, which import-linter reads as mutually
independent — so the encoded rule forbids `pipeline → workers`, the path the
intent requires, and permits `gui → workers`, the one it forbids. Harmless while
`workers/` does not exist. **Settle it in the commit that creates `workers/`**,
by moving it to its own tier or writing a forbidden contract. **Trigger: NOT
FIRED** (re-checked 2026.07.28) — `workers/` is still four lines in
SCAFFOLD.md's Projected half, and the stated resolution is still the right one.

## 2. One execution path, and artifact purity — ENFORCED

Rule 1 and rule 2 are checked by the same things and are listed together for
that reason. `pipeline/executor.execute` is the only frame-computing loop; the
layer contract keeps `gui/` above `pipeline/` and `decode/` the only route to a
frame, so a second execution path cannot be assembled quietly out of the parts.

The serialized pipeline contains no GUI-only state (panel layout, zoom, scrub
position).

**Enforced by:**
`tests/unit/test_pipeline_model.py::test_gui_state_cannot_be_stashed_in_the_artifact`
and `tests/unit/test_pipeline_model.py::test_node_carries_identity_and_nothing_else`,
plus YAML round-trips there and in `tests/gui/test_project_io.py`.

**Enforced by, as of 2026.08.04:** the second half — *a pipeline saved from the
GUI loads and executes identically in the CLI* —
`tests/gui/test_gui_cli_parity.py::test_the_series_the_gui_shows_is_the_series_the_cli_computes`
and
`tests/gui/test_gui_cli_parity.py::test_the_intervals_agree_and_are_stated_in_the_same_frames`.
A document is tuned through `ReplicateDocument`'s commands, saved by the real
writer, and then run twice: through `PreviewRunner` + `SeriesCollector` +
`detector_worker.derive`, which is the filter tab without the widget, and
through `sieve detect --csv`. The per-frame series and the claimed intervals are
diffed. This is what makes rule 1 a guarantee rather than a property of how the
code currently happens to be arranged, and it is **output, not plan** —
comparing resolved plans would pass while both sides computed the same wrong
thing.

**What the third test in that module is for.** `test_the_two_arenas_are_not
_running_the_same_thing` asserts the fixture still deviates — different block
sizes, different detection windows, reaching the grid and the gate. A parity
check whose two arenas resolve alike passes against a front end that drops
replicate pins entirely, and the first draft of this one was exactly that: over
the shared uniform fixture the in-band count saturates, so a pinned `D` changed
nothing observable. A guard on a parity test is not decoration — it is the half
that fails when *both* sides are wrong together, which is the failure a
comparison cannot see.

**The trigger that used to be here is gone, which is the point of one.** It read
"the next item that touches serialization", and schema v3 landed `Edge.port`,
`Project.detector`, and the pin fields with nobody polling it — a trigger nobody
polls makes a check a lottery ticket, and this one went unclaimed for a week.
A **Trigger:** line stands in for a check only while the thing it would guard
does not exist (see *Adding one*), so it leaves with the check's arrival rather
than staying on as a record; the record is
`docs/completed-todo/2026.08.04-gui-cli-execution-parity.md`.

## 3. Filter self-registration — ENFORCED, and the strongest of the eight

A filter is one class plus one colocated markdown. Discovery finds it with no
edit to any registry, manifest, or import list.

**Enforced by:**
`tests/unit/test_filter_discovery.py::test_discovery_imports_no_filter_module`,
which AST-parses `filters/__init__.py` and fails if it names any filter module —
so the guardrail cannot be defeated by adding an import — and
`tests/unit/test_filter_discovery.py::test_every_discovered_filter_has_guidance_markdown`,
which enforces the `.md`.

**Enforced by, as of 2026.08.04:** the half both of those are blind to —
`tests/unit/test_filter_id_spelling.py::test_no_filter_id_is_spelled_outside_its_module_undeclared`,
REWORK.md R4's literal half. The import check makes a manifest impossible; it
cannot see `"block_signal"` typed into a widget, which is the same enumeration
spelled as data. Eleven `(module, filter_id)` pairs across `gui/chain_model.py`,
`gui/filter_tab.py`, and `gui/wizard_model.py` are the shrink-only exception
list, and it is the work list — `test_the_declared_spellings_only_shrink` fails
on an entry whose literal has gone, so removing the code and removing its
exception are one edit. The owning module is asked of the registered params
class rather than assumed to be `filters/<id>.py`, so the check does not quietly
stop working for the first filter that breaks the convention.

A second check in the same module is **vacuous today and deliberately so**: no
name declared in a `TableSpec.columns` may be spelled in two top-level packages,
with the package list read off the tree. Nothing declares columns yet, so it is
pinned against a planted tree instead — the `.importlinter` idiom of governing a
layer before it exists. The first table emitter is the moment a column name
starts being typed twice, and a check written after that arrives as an exception
list rather than as a rule.

## 4. Latency budgets — ENFORCED for the table and the producers, PARTIAL for the timings

**Enforced by:** `tests/bench/test_budget_table.py` compares the prose table in
`ARCHITECTURE.md` against `bench/budgets.py` bidirectionally and character-exact,
so those two cannot drift. `noxfile.py`'s `benchmark` session selects by marker
rather than by `--benchmark-only`, so deleting the budget checks yields pytest
exit code 5 and breaks the gate instead of reporting green on skips.

**Enforced by, as of 2026.07.27:** `tests/bench/test_budget_producers.py`, which
is rule 4's other half. 8 of the 12 budgets are named by a module under `src/`;
the other 4 are declared in `budgets.WITHOUT_PRODUCER` and the test fails both on
an undeclared budget with no producer and on a declared one that has since grown
a producer, so the gap is a list that only shrinks. It also AST-checks every
module-level `*_BUDGET` constant against the table — which closes the hole the
layer diagram opens, since `pipeline/` may not import `bench/` and so spells its
two keys as string literals.

**PARTIAL:** 3 of the 12 budgets are actually *timed* —
`tests/bench/test_perf_regression.py` covers `open_to_first_frame` and
`scrub_settle`, both pre-pipeline, and `tests/bench/test_density_rebuild.py`
covers `density_rebuild`, which is the one in-pipeline budget with a clock on
it and is also the one currently in `IN_DEBT`. **Eight of the nine remaining
in-pipeline budgets are published and nothing asserts a limit on any of them in
CI**, which matters because in-pipeline is the regime the product is sold on.
**Trigger: FIRED** (audited 2026.07.28) →
`docs/todo/ceilings-in-the-dimension-they-bound.md` — `filter_to_first_tick`,
`knob_to_graphs`, and `knob_to_first_partial` have had producers since
2026.07.27. It fired meaning *write those three CI benchmarks*, and REWORK.md
R6 answers it differently: all three bound user-perceived latency, so they stay
denominated in wall time, and wall-clock verification moves to a calibration
job that does not gate. The item named above is where that split is decided,
and it names this section as the place to state it — so the honest reading of
the count below is that it will not go to zero by benchmarking these three. The
remaining gap is a count this section states, so the counts above are the thing
to correct when it moves; before this audit they read "7 of the 11" and "2 of
the 11", against a table of twelve.

## 5. Cache isolation — ENFORCED

Changing a parameter on one DAG branch does not invalidate sibling branches.

**Enforced by:** `tests/unit/test_cache_key.py::TestIsolation` — the described
mutation test on an a→{b,c} graph, plus
`tests/unit/test_cache_key.py::test_a_pinned_replicate_ignores_the_default_moving_under_it`.

## 6. Documentation that asserts facts about the code — ENFORCED

Nine claims are machine-checked, which is why they stayed true while the prose
around them drifted:

- `docs/*/.index.md` against their folders — `tests/docs/test_doc_index.py`
- `docs/SCAFFOLD.md`'s Built and Projected halves against the tree —
  `tests/docs/test_scaffold.py`
- `ARCHITECTURE.md`'s budget table against `budgets.py` —
  `tests/bench/test_budget_table.py`
- `docs/SETTLED.md` against the `settled:` blocks it is generated from, and
  every `where:` in one against the tree — `tests/docs/test_todo_hygiene.py`
- every item's `status:` and `priority:` inside their vocabularies, *and the
  primer's open list actually sorted by the latter* —
  `tests/docs/test_todo_hygiene.py`. The second half is the one worth having:
  a required field that nothing orders on is a cell somebody fills and no
  reader is served by
- every `docs/*.md` declaring `status: current | record | working`, so a
  reader can tell whether a file even claims to be true now —
  `tests/docs/test_doc_status.py`
- every link, backticked file path, and item `reads:` entry across the live
  docs resolving to something that exists — `tests/docs/test_doc_refs.py`,
  which found twelve dangling pointers the first time it ran
- every check *this file* and ARCHITECTURE name — as `path.py::name`, resolved
  by AST — and every `.importlinter` contract they cite, resolved by parse —
  `tests/docs/test_guardrail_refs.py`. The path half was already covered; a
  renamed test is the half that reads as done forever
- every **Trigger:** line here parsing, and a FIRED one naming a
  `docs/todo/` item that exists; every **Gate:** line in REWORK.md naming a
  live check or saying OPEN — same file. §2's trigger fired at schema v3 with
  nobody noticing, which is the failure this converts

**The rule this generalizes:** when a doc asserts something about the code,
prefer a form a test can parse. The audit that produced this file found five
false claims, and every one of them was in prose while every machine-checked
claim was correct.

## 7. Dividing the machine — ENFORCED at the call site, PARTIAL for the sum

Rule 5: no consumer improves its latency at another's expense.

**Enforced by:** `gui/concurrency.py` declares the split and
`tests/unit/test_concurrency.py` asserts the sum leaves the machine a core for
the GUI thread. As of 2026.07.27, `chain_model.recompute` takes `workers` as a
required argument, so **pyright** rejects a caller that does not state its share —
which is the half that actually holds, because it fires where a violation is
written.

**Why the second mechanism exists.** The sum test passed for the whole time
`gui/filter_tab.py` was running a full Morlet transform over every core on the
GUI thread, by omitting an argument that defaulted to `ALL_CORES`. A test that
sums declared constants can only check the declaration; it is blind to a consumer
that never declared itself. Any future shared-resource cap should be a required
argument before it is a constant with a test.

**PARTIAL:** the arithmetic still assumes the three declared pools are the only
consumers. Nothing detects a fourth that arrives by some route other than
`recompute` — a new `scipy` or `cv2` call with a thread-count default would not
be seen. **Trigger: NOT FIRED** (re-checked 2026.07.28 against `e394636`, which
moved the density surface out of the widget, and against `gui/detector_worker.py`,
the new consumer it feeds). `detector_worker.derive` takes its share from
`resolve_worker_split().detector` and passes it explicitly to both `morlet_power`
calls, so the fourth consumer arrived *through* the declared mechanism rather
than around it. That is the required-argument half of this section working as
designed, which is the outcome worth recording — the trigger stays armed.

## 8. Results that do not overstate themselves — OPEN, and probably not mechanical

Rule 6. There is no check and there may never be a general one; it is enforced by
review and by design precedent. What exists is a consistent habit worth pointing
at when reviewing: the executor refuses node shapes it cannot run rather than
approximating them, `cli/run_cmd.py` refuses a project whose sinks it cannot
write, and `cache_key.py` refuses to key what it cannot describe.

The specific instances that *will* be checkable have their checks written when
the thing they guard lands — the unexamined-versus-quiet rendering rule most of
all, which `docs/todo/coverage-and-detection-lanes.md` names as V1's standing
failure and which is inherited
by three widgets that do not exist yet.

## 9. Placement — the GUI computes nothing — ENFORCED, with the violations as the work list

REWORK.md R1: everything that touches the footage, or anything derived from it,
is a filter — so `gui/` renders values and emits intents, and holds no second
implementation of a computation. The layer contract cannot say this: `gui` sits
above `core`, which makes importing `morlet_power` into a widget legal under
every direction-of-dependency rule while being exactly what rule 1 forbids.
This is the gap through which the most expensive computation in the tuning
loop came to run in a widget, in full compliance (§7's story, one level
deeper).

**Enforced by:** `.importlinter`'s `gui-computes-nothing` forbidden contract —
`sieve.gui` may not import `sieve.core.ops.wavelet`, `sieve.core.ops.detection`, or
`sieve.detect`. Indirect imports are allowed for `opencv-containment`'s
reason: reaching computation *through* `pipeline/` is the supported path; what
is forbidden is holding it. The seven current violations are the
`ignore_imports` exception list, and `unmatched_ignore_imports_alerting =
error` makes it shrink-only — a stale entry fails the contract, so deleting
the code and its exception are one edit, and *adding* an entry is a visible
widening of the rework.

**OPEN:** the same rule for fields rather than imports — `primary_params` is
GUI policy declared in `core/`, and no import contract can see a field. Its
gate is the spec-channel partition, REWORK.md R5's Gate line, not yet written.

---

## Adding one

A guardrail earns its place when it converts a class of mistake into a test
failure — not when it restates a preference. Write the check in the same commit
as the rule; a rule with a **Trigger:** line instead of a check is acceptable
only when the thing it would guard does not exist yet.
