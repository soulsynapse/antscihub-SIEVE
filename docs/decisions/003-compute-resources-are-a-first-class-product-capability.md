# Compute resources are a first-class product capability

Status: accepted on 2026-07-23.

## Context

SIEVE is intended to remain useful from an ordinary workstation through local
CPU and GPU execution and later HPC-assisted analysis. Scientific feasibility
is not determined by an algorithm alone. It also depends on the current
execution environment:

```text
CPU topology and usable concurrency
available and total memory
storage read/write behavior at the selected paths
GPU devices, memory, drivers, and supported compute backends
decoder and encoder capabilities
configured local or remote execution limits
```

The first-channel review exposed this directly through its retained-result
memory budget. Treating that budget as a channel-specific constant would solve
one immediate admission check while hiding the larger product responsibility.
The same mistake would recur for worker counts, decode concurrency, GPU use,
temporary storage, and whole-asset jobs.

HPC readiness therefore cannot be a late export feature or a collection of
developer environment variables. The product needs an explicit, inspectable
model of the resources available to an execution and the policy the user wants
SIEVE to apply.

## Decision

Available compute resources and execution policy are first-class product
concepts.

SIEVE will grow a dedicated **Resources** surface, likely a top-level tab placed
before Replicates. Exact navigation and visual design remain a later UI
decision, but current scientific and orchestration APIs must not prevent that
surface from becoming the owner of local capability assessment and execution
policy.

The product resource model must eventually cover:

- CPU model/topology and configurable thread or process concurrency.
- CPU backend capabilities, affinity/topology constraints, and supported
  parallel execution modes.
- Total, available, and user-allocatable memory.
- GPU inventory, usable device memory, driver/runtime/backend compatibility,
  and explicit device selection.
- Guided workflows that explain how a compatible workload can use available
  CPU parallelism or a GPU, when each path is appropriate, and what dependency
  or environment change is required when a selected path cannot run.
- Read and write diagnostics for user-relevant source, temporary, result, and
  scratch paths.
- Media decoder/encoder/backend capabilities relevant to the selected
  workload.
- Local execution limits and later portable HPC profiles, including scheduler,
  container/environment, scratch, and worker-allocation facts when those
  surfaces exist.

Resource capability and resource policy are separate:

```text
capability
  observed machine, backend, device, memory, and storage facts

execution policy
  selected limits and preferences such as result-memory budget,
  thread/process count, GPU/device/backend, scratch path, and concurrency
```

Both need provenance and age. A cached storage benchmark from another disk, a
GPU report from a different environment, or yesterday's available-memory
reading must not be represented as a current guarantee.

Resource policy is not scientific identity merely because it affects whether or
where work can run. Thread count, admission budget, scratch path, and queue
width normally remain execution policy. The chosen numerical implementation or
backend does belong in result provenance and, when it can change valid
numerical results, in the computation identity.

Headless scientific requests must remain usable by GUI, CLI, and later
distributed/HPC runners. They may accept a Qt-free immutable execution-resource
snapshot or explicit resource limits, but must not read widgets, global GUI
state, or one workstation's implicit defaults.

## Diagnostic behavior

Resource assessment is a supported product diagnostic under
`001-reusable-benchmarks-are-product-diagnostics.md`.

- Cheap capability inventory may be refreshed automatically when safe.
- Expensive read/write, CPU/GPU, media, or sustained-throughput measurements
  require a clear user action or a deliberate guided assessment.
- Storage diagnostics target an explicit path and use bounded temporary data
  with verified cleanup.
- Results report the target device/path, sample size, cache conditions,
  backend, environment, timestamp, and whether a value is observed, estimated,
  configured, or currently available.
- The UI may recommend a policy from measured capabilities, but must show the
  recommendation and allow the user to inspect or override it.
- Ordinary startup must not silently run large writes, saturate the CPU or GPU,
  scan an entire asset, or reserve the user's available memory.

## Consequences for current implementation

- Milestone 5 still needs exact retained-result admission before opening its
  working-window source.
- Its maximum result bytes must enter through a small Qt-free execution/resource
  policy seam rather than becoming an intensity-specific scientific constant.
- A minimal initial policy may precede the complete Resources tab, but its
  ownership and naming must allow the tab, CLI, and later HPC runner to supply
  the same value.
- Scientific workers must not infer unrestricted concurrency from host CPU
  count or automatically consume every visible GPU.
- CPU execution remains a complete first-class path; the design must not assume
  that GPU availability is required for scientific work or HPC execution.
- CPU and GPU backend/device choices remain explicit and provenance-bearing
  where they can affect numerical results or reproducibility.
- GPU acceleration remains opt-in and provenance-bearing until compatibility,
  numerical agreement, failure behavior, and fallback are validated.
- Storage and throughput estimates must be measured for the relevant paths and
  representations; a generic machine score is not sufficient for job
  admission.
- Future processing plans can be portable because scientific identity remains
  distinct from resource discovery, admission, placement, and scheduling.

## Deferred design work

This decision does not authorize implementation of the complete Resources tab,
automatic scheduler submission, CPU/GPU kernels or parallel executors, remote
execution, or a general job planner during milestone 5.

Later design must specify:

- The Qt-free capability report and execution-policy schemas.
- Refresh, caching, staleness, and provenance rules.
- Supported CPU compute, memory, storage, media, and GPU diagnostics.
- Safe defaults and the recommendation/override interaction.
- Resources-tab placement and workflow.
- Export/import of execution profiles for reproducible local and HPC runs.
- How admission combines current availability, configured limits, estimated
  peak buffers, result size, scratch requirements, and backend constraints.

## Relationships

- `001-reusable-benchmarks-are-product-diagnostics.md` governs supported
  capability measurements.
- `002-headless-scientific-identity-is-not-gui-lifecycle.md` keeps resource
  policy and GUI state outside durable scientific identity.
- `docs/handoffs/5-First-channel.md` provides the first concrete consumer
  through retained-result memory admission.
