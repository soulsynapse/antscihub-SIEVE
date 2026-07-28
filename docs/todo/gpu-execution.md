---
title: GPU execution
status: deferred
gated_on: >
  a filter whose CPU kernel is measurably the bottleneck of a tuning session —
  not merely slow, but one where `bench/budgets.py` is being missed because of
  it and the profile says so
reads:
  - docs/SCAFFOLD.md
  - src/sieve/backend/dispatch.py
  - docs/completed-todo/2026.07.25-executor.md
---

# GPU execution

**Why not now.** There are zero GPU kernels and two filters. The product is not
at feature parity with what VISION describes on the backend that already works,
and adding a second backend before the first one carries a real workflow means
maintaining two of everything to make nothing new possible.

**What would make it the right time.** A filter whose CPU kernel is measurably
the bottleneck of a tuning session — not a kernel that is merely slow, but one
where `bench/budgets.py` is being missed because of it and the profile says so.
VISION's detection and tracking steps are the likely first candidates;
`downsample` is not.

**`background_ema` is the first filter for which the arithmetic below no longer
refuses.** At 9.9 ms/MP it is ~30x `downsample`, so on the reference source a
frame costs order 200 ms on CPU against ~10 ms of round trip — the transfer is
now 5% of the work rather than double it. That does *not* promote this entry:
the trigger is a missed budget with a profile behind it, and no in-pipeline
budget can be missed until `pipeline/preview.py` exists to publish one. What it
does mean is that the answer to "would a GPU kernel pay?" has flipped from
"provably not, for the only filter we have" to "probably, and somebody should
measure it" — and that measurement is step one of acting on this entry.

**What it involves, so the size is not a surprise:**

- `backend/namespace.py`, which SCAFFOLD reserves and nothing implements:
  Array-API namespace resolution (numpy vs cupy) and host/device transfer.
- **Frame residency.** `Frame.data` is `NDArray[Any]` — host, by annotation and
  by every consumer. Nothing in the system knows where a frame lives, so a GPU
  kernel doing its own `asarray`/`asnumpy` round-trips per node. See the
  arithmetic below.
- **Automatic backend selection.** `ExecutionPlan.backends` already carries a
  backend per node and the keys are derived from it, so a mixed graph runs and
  keys correctly today — see
  `docs/completed-todo/2026.07.25-per-node-backend.md`. What is missing is
  anything that *chooses*: a caller must state the mapping, and nothing walks
  the kernel shelf against `DEFAULT_PREFERENCE` to build one. That resolution
  needs a policy — fastest available per node, or fewest transfers across the
  graph — and the second is the right answer only once residency below exists.
- **Cache locality.** Does `FrameStore` hold device arrays or host arrays?
  Device exhausts VRAM over a tuning session; host makes every hit an upload.
  This has no obvious answer and should not be given one without a workload.
- **The equivalence test that `backend_agnostic` requires.** `FilterSpec` says
  claiming it "requires an equivalence test"; there is no such test and no
  harness for one. `KernelRegistry.select`'s one-element preference tuple exists
  precisely so a test can drive both sides, and has no caller doing that.
  `@pytest.mark.cuda` is declared in `pyproject.toml` and used by nothing.

**Two postures fixed 2026-07-27, so the item starts from decisions rather
than open ends** (each with the condition that would revise it):

- **Selection policy: fastest-available-per-node until residency exists,
  fewest-transfers after.** The item's own text already implies this ordering;
  it is now the decision. The first version may therefore GPU-place only nodes
  that win *including* their own transfers (which the arithmetic below says is
  none until `background_ema`-class filters) — honest, and it cannot regress a
  working graph. `FrameStore` holds **host arrays** until a measured workload
  says VRAM residency pays; device-side caching is the revision, not the
  default, because VRAM exhaustion over a tuning session is the OOM-kill class
  of failure and nobody has measured a session's device footprint.
- **VRAM joins the resource ledger** (docs/todo/resource-ledger.md) as a third
  column the day the first kernel lands: resolved device allocation, declared
  consumers, a reserve. The ledger item holds the shape; this one brings the
  tenant.

**The arithmetic that says this is not free — not a measurement.** On the
reference source (5312x2988 BGR, ~47 MB a frame), a PCIe round trip is order
5 ms each way, against `downsample`'s declared 0.35 ms/MP — about 5 ms for that
frame on CPU. So a GPU downsample that transfers per node is *slower* than the
CPU kernel it replaces, and GPU pays only when frames stay resident across
consecutive GPU nodes. This is arithmetic from a declared cost and a bandwidth
figure, not something anybody has measured on this hardware; measuring it is
step one of acting on this entry, and the result belongs in `docs/findings/`.

Read: `docs/SCAFFOLD.md` `backend/`, `src/sieve/backend/dispatch.py`,
`docs/completed-todo/2026.07.25-executor.md`.
