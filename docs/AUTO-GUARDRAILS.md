---
reviewed: 75ee2a6
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

**Enforced by:** `.importlinter`, four contracts, run by `nox -s imports` inside
`checks`.

**OPEN:** "`gui/` never bypasses `pipeline/` to reach `workers/`" is not
expressible in the current contract and is not checked. `pipeline/` and
`(workers/)` are siblings on one tier, which import-linter reads as mutually
independent — so the encoded rule forbids `pipeline → workers`, the path the
intent requires, and permits `gui → workers`, the one it forbids. Harmless while
`workers/` does not exist. **Settle it in the commit that creates `workers/`**,
by moving it to its own tier or writing a forbidden contract.

## 2. One execution path, and artifact purity — ENFORCED for purity, OPEN for parity

Rule 1 and rule 2 are checked by the same things and are listed together for
that reason. `pipeline/executor.execute` is the only frame-computing loop; the
layer contract keeps `gui/` above `pipeline/` and `decode/` the only route to a
frame, so a second execution path cannot be assembled quietly out of the parts.

The serialized pipeline contains no GUI-only state (panel layout, zoom, scrub
position).

**Enforced by:** `tests/unit/test_pipeline_model.py` —
`test_gui_state_cannot_be_stashed_in_the_artifact`,
`test_node_carries_identity_and_nothing_else`, plus YAML round-trips there and
in `tests/gui/test_project_io.py`.

**OPEN:** the second half — *a pipeline saved from the GUI loads and executes
identically in the CLI* — has no check. `tests/integration/test_cli_run.py`
builds its projects directly rather than from a GUI-saved document, and nothing
diffs GUI-run against CLI-run output. This is the one that would catch a real
divergence rather than a schema slip, and it is the most valuable unwritten
check in this file — it is the only thing that would make rule 1 a guarantee
rather than a property of how the code currently happens to be arranged.
**Trigger:** the next item that touches serialization.

## 3. Filter self-registration — ENFORCED, and the strongest of the five

A filter is one class plus one colocated markdown. Discovery finds it with no
edit to any registry, manifest, or import list.

**Enforced by:** `tests/unit/test_filter_discovery.py`.
`test_discovery_imports_no_filter_module` AST-parses `filters/__init__.py` and
fails if it names any filter module — so the guardrail cannot be defeated by
adding an import. `test_every_discovered_filter_has_guidance_markdown` enforces
the `.md`.

## 4. Latency budgets — ENFORCED for the table and the producers, PARTIAL for the timings

**Enforced by:** `tests/bench/test_budget_table.py` compares the prose table in
`ARCHITECTURE.md` against `bench/budgets.py` bidirectionally and character-exact,
so those two cannot drift. `noxfile.py`'s `benchmark` session selects by marker
rather than by `--benchmark-only`, so deleting the budget checks yields pytest
exit code 5 and breaks the gate instead of reporting green on skips.

**Enforced by, as of 2026.07.27:** `tests/bench/test_budget_producers.py`, which
is rule 4's other half. 7 of the 11 budgets are named by a module under `src/`;
the other 4 are declared in `budgets.WITHOUT_PRODUCER` and the test fails both on
an undeclared budget with no producer and on a declared one that has since grown
a producer, so the gap is a list that only shrinks. It also AST-checks every
module-level `*_BUDGET` constant against the table — which closes the hole the
layer diagram opens, since `pipeline/` may not import `bench/` and so spells its
two keys as string literals.

**PARTIAL:** 2 of the 11 budgets are actually *timed* —
`tests/bench/test_perf_regression.py` covers `open_to_first_frame` and
`scrub_settle`, both pre-pipeline. **Every in-pipeline budget is published but
nothing asserts a limit on it in CI**, which matters because in-pipeline is the
regime the product is sold on. **Trigger:** each in-pipeline budget gets its
benchmark when the thing that produces it lands; `filter_to_first_tick`,
`knob_to_graphs`, and `knob_to_first_partial` all now have producers and so are
takeable today.

## 5. Cache isolation — ENFORCED

Changing a parameter on one DAG branch does not invalidate sibling branches.

**Enforced by:** `tests/unit/test_cache_key.py::TestIsolation` — the described
mutation test on an a→{b,c} graph, plus
`test_a_pinned_replicate_ignores_the_default_moving_under_it`.

## 6. Documentation that asserts facts about the code — ENFORCED

Three docs make checkable claims and each is checked, which is why they stayed
true while the prose around them drifted:

- `docs/*/.index.md` against their folders — `tests/docs/test_doc_index.py`
- `docs/SCAFFOLD.md`'s Built and Projected halves against the tree —
  `tests/docs/test_scaffold.py`
- `ARCHITECTURE.md`'s budget table against `budgets.py` —
  `tests/bench/test_budget_table.py`

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
be seen. **Trigger:** the next module that calls into a library whose default is
every core.

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

---

## Adding one

A guardrail earns its place when it converts a class of mistake into a test
failure — not when it restates a preference. Write the check in the same commit
as the rule; a rule with a **Trigger:** line instead of a check is acceptable
only when the thing it would guard does not exist yet.
