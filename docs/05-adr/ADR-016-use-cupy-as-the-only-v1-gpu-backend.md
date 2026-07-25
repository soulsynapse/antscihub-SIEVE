# ADR-016: Use CuPy as the only v1 GPU backend

Reference: https://docs.arc42.org/section-9/

## Context

[STABLE] SIEVE's backend architecture supports explicit CPU and GPU registrations,
capability-based dispatch, cost-aware selection, visible fallback, and backend
identity in cache keys. ADR-011 selects Array API-compatible kernels where
possible so numerical code is not needlessly tied to one array library.

[STABLE] Those architectural seams make multiple GPU libraries possible, but they do
not make multiple GPU libraries free. CuPy and PyTorch each bring CUDA binary
compatibility requirements, device and stream semantics, memory allocation and
caching behavior, failure modes, profiling integration, determinism controls,
and a large validation matrix.

[INTENT] CuPy is a direct NumPy-like GPU array library and is sufficient for SIEVE v1's
planned array filters and custom kernels. No accepted v1 filter requires
PyTorch autograd, neural-network modules, a Torch-only pretrained model, or a
Torch-specific operator.

[STABLE] CuPy and PyTorch can technically coexist and exchange arrays through protocols
such as DLPack. The issue is not whether coexistence is technically feasible.
The issue is that one process would then own two allocator/stream/library
surfaces and their packaging constraints without a filter requirement that
justifies the integration and test burden.

[STABLE] The current architecture already marks `backends/gpu_torch.py` as "only if a
filter uses torch." ADR-011's references to NumPy, CuPy, and PyTorch describe a
portable-kernel capability and possible future registrations, not a requirement
to ship three backends in v1.

[STALE WHEN] Architecture §12 currently gives only Torch-specific examples for deterministic
GPU mode. That language is not an operative v1 implementation prescription:
v1 needs CuPy/CUDA-specific reproducibility declarations and tests. Torch
determinism controls become relevant only if a Torch backend is accepted later.

## Decision

Ship one GPU array backend in SIEVE v1: CuPy.

The v1 backend registry contains:

```text
cpu_numpy
gpu_cupy
```

Do not create `backends/gpu_torch.py`, a Torch adapter, Torch capability probe,
Torch dependency extra, Torch worker mode, Torch cache identity, or Torch test
matrix until an accepted filter has a concrete Torch-only requirement.

Do not install PyTorch as an application or development dependency merely to
prove theoretical backend portability. Array API-compatible kernels should
remain backend-neutral where ADR-011 requires it, but v1 cross-backend
correctness tests exercise only the backends actually registered: NumPy and
CuPy.

Use the singular serial GPU worker required by architecture §10 and manage it
through the process protocol selected in ADR-015. That process imports and
initializes CuPy only. It owns:

- its CUDA device selection and context use;
- CuPy streams and events;
- CuPy's memory pool and any configured allocator;
- compiled kernel/module caches;
- device-resident request state; and
- cleanup, health, and out-of-memory recovery for its process generation.

The CPU/controller process must be able to import and run without importing
CuPy or initializing CUDA. GPU capability detection occurs at an explicit
boundary and reports unavailable, incompatible, or failed initialization
without preventing CPU-only operation.

Package CuPy as an optional GPU dependency, not a base runtime dependency.
Select exactly one CuPy distribution compatible with the supported CUDA major
for each released environment. Do not install conflicting `cupy`,
`cupy-cuda12x`, or `cupy-cuda13x` distributions in one environment. Record the
chosen CuPy distribution, CuPy version, CUDA runtime/toolkit compatibility,
driver requirement, and supported platform in packaging and deployment
documentation.

The uv lock and CI environments must make the chosen CUDA variant explicit.
CPU-only resolution and tests must not need to download a CUDA wheel. A
required-GPU CI job installs the supported CuPy extra and fails, rather than
skips, when the declared CUDA capability is unavailable, as required by
ADR-009.

Register `gpu_cupy` only for filters that have:

- a valid CuPy or shared Array API implementation;
- explicit dtype, shape, range, and device behavior;
- no hidden host transfer;
- numerical-equivalence or declared-tolerance tests against the authoritative
  CPU implementation;
- a determinism declaration;
- backend-specific cost and memory estimates;
- out-of-memory and unsupported-operation behavior;
- cache identity including the backend and relevant implementation version;
  and
- profiling ranges appropriate to CuPy/custom CUDA work.

Do not treat all Array API-compatible filters as automatically GPU-supported.
Registration is explicit per filter. A shared kernel can serve both NumPy and
CuPy only after its semantics and performance contract are validated for both.

Define v1 GPU determinism in terms of the actual CuPy implementation and CUDA
libraries used. Each registered GPU filter declares whether its operations are
deterministic under the supported configuration and what tolerance is used
against CPU results. Pin or record CUDA-relevant library, kernel, and algorithm
configuration where it affects cache validity or reproducibility. Do not copy
Torch determinism calls into the CuPy worker.

CPU fallback remains visible and evidence-preserving. If the GPU is absent,
incompatible, out of memory, or unsupported for a filter, dispatch may fall
back only under the explicit policy in architecture §9. Logs, benchmark rows,
HUD state, and cache identity record the backend that actually ran.

Defer Torch until a specific accepted filter genuinely requires it, for example
a pretrained model whose supported implementation is PyTorch. That proposal
must include:

- the filter and why CuPy, ONNX Runtime, or another existing path is
  insufficient;
- the model artifact, license, version, and reproducibility contract;
- CUDA/driver/package compatibility with SIEVE's supported deployment targets;
- memory, stream, transfer, determinism, cache, profiling, and failure
  semantics; and
- CPU fallback or a clear declaration that no fallback exists.

If accepted, run Torch in a separate long-lived worker process that implements
the same versioned supervisor protocol but owns no CuPy runtime. Do not import
CuPy and Torch into the same GPU worker. Resource admission must serialize or
otherwise explicitly coordinate CuPy-worker and Torch-worker access to each
physical GPU; process isolation does not create additional GPU memory.

Create `backends/gpu_torch.py` only as part of that accepted filter/backend
change. The file's absence in v1 is intentional and tested through registry and
dependency assertions rather than filled with a placeholder.

`BACKEND_DISPATCH.md` does not yet exist. When the backend-dispatch
specification is created, it must include an "Add a new backend" path covering:

1. backend identifier and registry entry;
2. concrete filter requirement and supported filter set;
3. process/runtime isolation and resource-admission policy;
4. dependency extra, lock resolution, CUDA/driver compatibility, and
   capability probing;
5. array namespace/adapter and host-device transfer ownership;
6. device, allocator, stream, synchronization, and lifetime rules;
7. dtype, numerical-equivalence, and determinism contracts;
8. cost model, memory estimates, OOM behavior, and fallback policy;
9. cache identity and artifact provenance;
10. logging, HUD, benchmark, and profiler integration;
11. CPU-only, required-GPU, cancellation, crash, and cleanup tests; and
12. deployment, HPC, and user-facing documentation.

Keep that path backend-generic so adding Torch later is a bounded extension
rather than an architectural rewrite. Reversibility comes from the registry,
worker protocol, and documented checklist, not from shipping unused adapter
files.

No CuPy-versus-PyTorch benchmark is required for v1 selection. There is no
Torch-dependent v1 workload to benchmark. A benchmark becomes meaningful only
when a concrete filter has two valid implementations with the same scientific
contract.

This ADR narrows the v1 backend scope described by ADR-011 without superseding
its Array API-compatible kernel and typing decisions.

## Alternatives considered [INTENT]

### CuPy and PyTorch in the same v1 GPU worker

This maximizes immediate library coverage and permits direct DLPack exchange.
It also combines allocator, stream, synchronization, binary compatibility,
profiling, initialization, and failure behavior before SIEVE has a filter that
needs both. The added surface has no v1 payoff.

### CuPy and PyTorch in separate v1 workers

[INTENT] Process isolation is the correct shape if Torch becomes necessary. Adding the
second worker now would still add dependencies, GPU resource coordination,
startup, memory admission, CI, packaging, and backend-equivalence obligations
for no accepted filter.

### PyTorch only

[INTENT] PyTorch provides a mature tensor library, custom operators, pretrained-model
ecosystem, and strong profiling tools. SIEVE v1's expected GPU operations are
array transformations and custom numerical kernels rather than model training
or inference. CuPy is the smaller conceptual match for the NumPy-oriented
filter contract.

### JAX

JAX offers compiled array programs, transformations, and accelerator dispatch.
It would add XLA compilation, functional-programming constraints, and another
deployment/runtime stack not required by v1 filters.

### Numba CUDA or handwritten CUDA only

[INTENT] These approaches provide direct kernel control and may be appropriate for a
specific hotspot. They do not replace the general GPU array, memory, and
namespace surface needed by ordinary filters. A measured custom kernel can
remain an implementation detail of `gpu_cupy` where CuPy's raw-kernel path is
suitable.

### CPU-only v1

[INTENT] Deferring GPU support would minimize deployment complexity but fail the
architecture's GPU dispatch, cost comparison, and HPC goals. CuPy provides the
single GPU path needed to validate those contracts without multiplying
runtimes.

### Placeholder gpu_torch.py

[INTENT] A stub could advertise intended extensibility. It would imply a backend exists,
invite imports or registrations before its contract is defined, and create
dead code. The documented addition path and registry boundary provide cheaper,
more honest reversibility.

## Status

Accepted.

## Consequences

- SIEVE v1 has exactly one GPU backend identifier: `gpu_cupy`.
- `cpu_numpy` and `gpu_cupy` are the only v1 cross-backend correctness targets.
- PyTorch is absent from runtime, development, packaging, worker, registry, and
  CI dependency surfaces.
- `backends/gpu_torch.py` is intentionally absent until an accepted filter
  requires it.
- The GPU worker owns one array library, allocator/stream model, and CUDA
  integration surface.
- CPU-only startup and operation remain independent of CuPy import and CUDA
  initialization.
- Packaging must select exactly one supported CuPy/CUDA distribution and avoid
  conflicting CuPy packages.
- Required-GPU CI validates the chosen CuPy stack; ordinary CPU CI can remain
  CUDA-free.
- Array API-compatible source remains open to future backends, but registration
  and testing stay limited to implementations SIEVE actually supports.
- CuPy-specific determinism, tolerance, profiling, OOM, transfer, and cache
  contracts must replace the current architecture's Torch-only examples for
  v1.
- Adding Torch later requires a concrete filter, a separate worker, explicit
  physical-GPU admission, and the complete backend checklist.
- Separate processes isolate Python/CUDA library state but do not eliminate
  shared device-memory and scheduling contention.
- A future Torch proposal can be evaluated and implemented without changing the
  filter registry, Array API kernel policy, worker supervisor, or backend
  identity model.
- The missing `BACKEND_DISPATCH.md` remains future architecture work; this ADR
  defines the minimum reversible-addition content it must contain.
- Profiling for v1 GPU work uses CuPy/custom-kernel mechanisms rather than
  `torch.profiler`.
- No speculative backend file or compatibility matrix is maintained.

## References [STABLE]

- [CuPy installation documentation](https://docs.cupy.dev/en/stable/install.html)
- [CuPy interoperability documentation](https://docs.cupy.dev/en/stable/user_guide/interoperability.html)
- [CuPy memory management documentation](https://docs.cupy.dev/en/stable/user_guide/memory.html)
- [Python Array API standard](https://data-apis.org/array-api/latest/)
- [DLPack specification](https://dmlc.github.io/dlpack/latest/)
- [SIEVE architecture: backend dispatch
  criteria](../04-architecture/ARCHITECTURE.md#9-backend-dispatch--criteria)
- [SIEVE architecture: worker
  criteria](../04-architecture/ARCHITECTURE.md#10-worker-architecture--criteria)
- [SIEVE architecture: determinism
  policy](../04-architecture/ARCHITECTURE.md#12-determinism-policy--criteria)
- [ADR-009: Use Nox for task
  orchestration](ADR-009-use-nox-for-task-orchestration.md)
- [ADR-011: Use Array API-compatible filter code and NumPy
  typing](ADR-011-use-array-api-compatible-filter-code-and-numpy-typing.md)
- [ADR-015: Manage long-lived workers with
  multiprocessing.Process](ADR-015-manage-long-lived-workers-with-multiprocessing-process.md)
