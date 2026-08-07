---
title: The tool contract ports with its rename
step: "01.2"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py tests/unit/test_tool_discovery.py -q"
opened: 2026-08-06
---

# The tool contract ports with its rename

`core/tool_base.py` and `core/tool_registry.py` from v2's `filter_base.py`
and `filter_registry.py`, renamed per `adr/tools-not-filters.md` and cut to
what v3 consumes: id, version, params model, window shape (`mode`,
`stateful`, `warmup_frames`), state factory. The cut list is exhaustive —
cost estimates, `backend_agnostic`, `frame_bytes_ratio`, and the merging
protocol do not come; each returns with its consumer
(`adr/declared-means-verified.md`). Registration refuses by name anything
declared and unconsumed — a state factory without `stateful` is the worked
example (`adr/no-kernel-apparatus.md`). The v2 module docstrings are the
contract's primary source; the ported docstring is cut the same way the code
is. Tests port from `test_filter_contract.py` and `test_filter_discovery.py`
under the new names, minus cases covering cut declarations (PLAN.md, porting
discipline).

## Worker note, 2026-08-07

`tool_base.py`, `tool_registry.py`, and `test_tool_contract.py` are in;
`ruff check . && lint-imports && pytest -q` is green at 113 passed, 5
contracts kept. **`test_tool_discovery.py` is not written and `done_when` as
stated cannot pass** — the blocker is below, and the item is at
`awaiting-review` rather than claiming otherwise.

Discovery has no subject at 01.2. v2's `test_filter_discovery.py` is five
cases and every one of them needs something this item does not build: three
(the scan imports no tool module, every tool ships guidance markdown, every
tool declares a caption) need `sieve.tools.discover` — a third module
the item's file list does not name — *and* at least one tool on the shelf,
which is 02.4; the guidance case additionally needs the per-tool `.md` that
PLAN.md's open questions have not decided and its porting discipline
currently forbids. The remaining two (params round-trip through JSON,
canonical params stable across processes) are about `ParamsBase` and are
portable, but only by substituting a locally declared params model for
`DownsampleParams` — adapting a case, which the discipline reserves for a
decision rather than a port. Rewriting the three into a file named for
discovery that discovers nothing would be wrong-but-green, which is the one
outcome the loop cannot detect.

The narrow reading is that `done_when` was drafted from v2's file list before
anyone noticed discovery needs a shelf. The proposal: strike
`test_tool_discovery.py` from this item and hang it on 02.4, which is where
the first tool, the first guidance question, and the first real scan all
arrive together. That is a `done_when` edit, so it is the reviewer's.

Three judgment calls inside the cut, none of which the item decides outright:

- **The cut list and the keep list disagree, and the cut list won.** "Cut to
  what v3 consumes: id, version, params model, window shape, state factory"
  omits `emits` and `summary`, without which no spec can be written, so it is
  not an enumeration; "the cut list is exhaustive" is. So everything v2 had
  that is not cost, `backend_agnostic`, `frame_bytes_ratio`, or the merging
  protocol came over: `accepts`/`emits` and the stream specs, the element
  axis, `settling_epsilon`, `rate_changing`/`selecting`/`deterministic`, the
  presentation trio, `SPEC_CHANNELS`, and the warmup arithmetic. Each of
  those either has a registration-time check standing in as its consumer or
  is consumed by a Phase-2 port — `declared-means-verified`'s licensed shape.
- **`run` did not come; `state_factory` did.** The item names the factory and
  not `run`, and the two are not symmetric under `declared-means-verified`:
  the factory has a consumer at registration (refused without `stateful` —
  `no-kernel-apparatus`), while `run`'s only consumer is the executor at 02.3
  and its signature is what 01.3's lookahead reshapes. A `run` field landing
  now would be a declaration with neither a check nor a reader.
- **The refusal is one-directional**, exactly as `no-kernel-apparatus` states
  it: a factory without `stateful` raises, `stateful=True` without a factory
  does not. The paired-flag family beside it (`rate_changing`,
  `selecting`) is checked both ways, so the asymmetry is visible in the file
  and worth a reviewer's yes or no rather than my quiet default.

Two smaller deviations from the v2 blob, both forced rather than chosen.
`pydantic>=2` joins the runtime dependencies with its reason. And ruff's
default rules here — unlike v2's — reject `TypeAlias` and `range(0, N)`, so
the three type aliases use the `type` keyword and `ALL_FRAMES` drops its
explicit start; neither changes what the names mean.
