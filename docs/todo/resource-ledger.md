---
title: Resource ledger
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — this is the planning pass the retention item asked
  for, written down; the resolver and the ledger are takeable now, and three
  items (retention, eviction, render ring) are each about to invent a memory
  bound if this does not land first
reads:
  - src/sieve/gui/concurrency.py
  - src/sieve/decode/prefetch.py
  - src/sieve/gui/proxy_cache.py
  - docs/todo/proxy-retention-policy.md
---

# Resource ledger: the session's claim on the machine adds up in one place

Rule 5 is enforced today by counting *threads* (`gui/concurrency.py`), and the
bandwidth finding already showed that arithmetic misses a resource that
actually binds. Memory is the next one, and three items are converging on it
from different sides: the retention policy wants a byte budget, cache eviction
wants a bound, and render-fed playback wants a ring size. Each would be a
number in a different file, wrong on most machines, and unaccountable in sum.
This item is the alternative: **the machine is read once, and every consumer
declares its share against that reading** — the same construction
`total_workers` already is, extended from cores to bytes.

This is not a revision of rule 5; it is its own text taken seriously. "Every
path that can take more than one core declares its share" becomes "…more than
one core, or a bounded slab of memory, declares its share", and the
enforcement stays what it is now: a sum a test checks, not a runtime governor.

## Step 1 — `available_memory()`, the honest allocation

The memory twin of `available_cpus()`, and the first thing to build. It
reports the *allocation*, never the machine, in this precedence:

1. cgroup v2 `memory.max` (v1 `memory.limit_in_bytes`) — a container or an
   HPC job step; the number that, exceeded, is an OOM kill and not a slowdown.
2. Scheduler declaration when no cgroup answers — `SLURM_MEM_PER_NODE` /
   `SLURM_MEM_PER_CPU x available_cpus()`. (Slurm normally imposes the cgroup
   too, so this is the fallback for configurations that do not.)
3. Physical memory otherwise — the desktop case. On Windows that is
   `GlobalMemoryStatusEx` via ctypes; do not add a psutil dependency for one
   struct read.

**One resolver, imported, never re-derived** — `resolve_workers` already
documents why two callers disagreeing about the node is a slow job nobody can
explain, and the same holds harder for memory because the failure is a kill.
Placement: beside `available_cpus` (whether that means the same module or a
small shared home for both is a SCAFFOLD call at landing; the constraint is
one definition, importable headless — the CLI and HPC path need it as much as
the GUI does).

## Step 2 — the ledger

`gui/concurrency.py` grows a byte column beside its thread column. Every
bounded slab the interactive session holds is declared there:

| Consumer | Today | Under the ledger |
|---|---|---|
| `ProxyFrameCache` | 96 MB constant | a declared share |
| render ring (render-fed playback) | does not exist yet | a declared share |
| `MemoryFrameStore` | unbounded | gets its bound here when eviction lands |
| prefetch in-flight frames | **undeclared and real** — `PREVIEW_WORKERS x lookahead` full-resolution buffers, order 47.6 MB each on the reference source | a declared share, first |
| player in-flight | one frame | declared for completeness |

The test is the same shape as `test_concurrency.py`: declared bytes plus a
reserve must fit `available_memory()`. The reserve covers what the ledger
cannot see — Python, Qt, the decoder's own buffers — and is a measurement, not
a constant to argue about (H3 below). Provisional until measured:
`min(4 GB, max(2 GB, 25%))`.

Shares should be *fractions of the post-reserve budget* with declared floors,
not absolute numbers — that is what makes the same source file right on a
16 GB laptop and a 256 GB node, which is the whole point. A consumer whose
floor cannot be met degrades explicitly (smaller cache, narrower proxy) or
refuses, per rule 6; it does not quietly overcommit.

## Step 3 — worker counts stop being constants

`PLAYER_WORKERS / PREVIEW_WORKERS / DETECTOR_WORKERS = 1/2/2` assumes a
machine with six cores to spare. The ledger resolves them at startup instead:
the current values are the *floors* on the reference class of machine, and on
smaller allocations the split degrades in priority order — detector first (its
own docstring calls it the weakest claim), then preview. `fits_machine`
already states a single-core allocation is not what the GUI is for; that stays.

Two cautions, both already in the repo's own findings, both saying **cores are
not the resource**:

- The prefetch worker optimum (4) is a memory-bandwidth property of the
  47.6 MB BGR buffer, not a core count — and `prefetch.py` itself flags the
  cap as "inherited, not established" on the luma path (H2).
- Scaling worker counts *up* on big machines is therefore not free headroom;
  it is the exact mistake the 8- and 12-worker measurements already made.
  More cores buy nothing without re-measuring the wall.

## GPU, so the column exists before the tenant

When `docs/todo/gpu-execution.md` lands, VRAM is a third ledger column with
the same shape: resolved allocation (device memory, or the job's declared
share of it), declared consumers (resident frames, kernel workspaces), a
reserve. The residency and cache-locality decisions stay in that item; the
ledger only insists they declare, so a tuning session cannot exhaust VRAM by
accretion the way `MemoryFrameStore` can exhaust RAM today.

## Hypotheses, each with a test that can kill it

- **H1 — the resolver reads every environment honestly.** Unit tests with
  fixture cgroup files (v1 and v2), Slurm env vars, and the bare-metal
  fallback; plus one integration assertion on this workstation that the
  answer equals physical RAM. Failure mode being guarded: a resolver that
  silently falls through to "machine total" inside a 16 GB job step on a
  512 GB node — the OOM-kill case.
- **H2 — the four-worker prefetch optimum does not survive the luma path.**
  The wall was the 47.6 MB buffer; luma is 15.9 MB, so the optimum should
  move. Re-run the worker sweep from the threading finding with `luma=True`.
  Outcome either way is a finding and sets the preview pool's ceiling.
- **H3 — the reserve.** Measure the session's RSS floor (app open, video
  loaded, nothing rendered) on the reference workstation and once on a small
  machine. That number replaces the provisional formula.
- **H4 — the ledger accounts for what the process actually holds.** Instrument
  peak RSS over a reference tuning session and compare to declared-sum plus
  reserve. A large gap means an undeclared consumer exists; finding it is the
  point of the test. This is also the measurement `cache-eviction.md` says
  nobody has taken — one instrumented session serves both.

Measurements land in `docs/findings/`; the ledger's constants cite them.

## What this item is not

Not a runtime governor, not a config surface (a derived budget is exactly the
setting `application-config.md` no longer has to carry — noted there), and not
an eviction policy: *what* to keep under a budget stays with
`docs/todo/proxy-retention-policy.md` and `docs/todo/cache-eviction.md`. This
item only makes "how much may I hold?" a question with one honest answer per
machine.
