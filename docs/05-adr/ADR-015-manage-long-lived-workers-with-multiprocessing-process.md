# ADR-015: Manage long-lived workers with multiprocessing.Process

Reference: https://docs.arc42.org/section-9/

## Context

[STABLE] Architecture §10 places compute outside the Qt process, prefers a
long-lived worker over per-job process creation, and makes cancellation of an
in-flight preview a first-class operation. ADR-002 already selects subprocess
workers and named shared memory for frame payloads, but deliberately leaves the
worker lifecycle and control protocol unspecified.

[STABLE] SIEVE's interactive workload is not a conventional bag of independent
functions. A worker may retain a decoder, filter state, allocated shared-memory
buffers, and a CPU or GPU backend across requests. While one request is
running, the controller sends cancellation or shutdown commands,
observe progress and health, reject stale results, and recover from a crashed
or unresponsive child.

[STABLE] The standard `multiprocessing.Pool` abstraction owns a pool and a task queue,
but its per-task `AsyncResult` does not provide cancellation of running work.
Terminating a pool stops its worker processes rather than cooperatively
cancelling one request while preserving a known worker lifecycle.

[STABLE] `concurrent.futures.ProcessPoolExecutor` provides a useful `Future` interface,
but `Future.cancel()` does not cancel a call that is already running. Its
executor-owned process lifecycle and one-way submitted-call model do not expose
the bidirectional, stateful control loop required here.

[INTENT] The remaining mechanism is small enough to own directly: a
`multiprocessing.Process`, a duplex command/event channel, a versioned message
protocol, explicit cancellation checkpoints, and bounded shutdown/restart
logic.

## Decision

Build SIEVE's worker supervisor and protocol directly on
`multiprocessing.Process`.

Use an explicit multiprocessing context rather than the module-global default:

```python
import multiprocessing as mp

mp_context = mp.get_context("spawn")
```

Use `spawn` on every supported platform. This gives Windows, Linux, local, CI,
and HPC execution one initialization model and avoids inheriting a live Qt
runtime, decoder threads, locks, or an initialized CUDA context through
`fork`. Worker targets must therefore be top-level importable callables, and
application entry points must use the normal `if __name__ == "__main__"` and
frozen-executable support required by multiprocessing.

Create each long-lived worker with `mp_context.Process`. Give the parent and
child opposite ends of a `multiprocessing.Pipe(duplex=True)` or an equivalent
pair of single-writer `multiprocessing.connection.Connection` endpoints. One
process owns each endpoint, and only one thread within that process may write
to it unless access is explicitly serialized.

The control channel carries small protocol messages only. Frame and array
payloads continue to use the named shared-memory transport selected in ADR-002.
Do not pickle scientific arrays into commands, progress events, or results.

Define the protocol as versioned, typed messages rather than arbitrary tuples
or callable pickles. Every message includes:

- protocol version;
- worker identity and process generation;
- message kind;
- request ID and request generation when applicable; and
- a typed payload appropriate to that message kind.

The initial parent-to-worker commands are:

```text
RUN
CANCEL
SHUTDOWN
PING
```

The initial worker-to-parent events are:

```text
READY
STARTED
PROGRESS
COMPLETED
CANCELED
FAILED
PONG
STOPPED
```

`RUN` contains a validated, immutable request descriptor. `COMPLETED` contains
small result metadata and shared-memory or artifact descriptors, not bulk
payload bytes. `FAILED` contains a normalized error code, safe message, and
structured diagnostic fields; do not depend on pickling arbitrary exception
objects across the process boundary.

Give each worker a monotonically increasing process generation and each
submitted operation a unique request ID plus the caller's current request
generation. The parent publishes a result only when worker identity, process
generation, request ID, and request generation all match the active request.
Late progress, completion, cancellation, and failure events from superseded
requests are drained and discarded without changing current UI or CLI state.

Cancellation is cooperative first:

1. the parent marks the request obsolete locally, so no later event can be
   published;
2. the parent sends `CANCEL` for the request;
3. the worker observes cancellation at documented checkpoints;
4. the worker stops producing new externally visible outputs, releases
   request-owned resources, and replies `CANCELED`; and
5. the parent acknowledges or releases shared-memory resources according to
   ADR-002's ownership protocol.

Long-running SIEVE loops and pipeline boundaries must contain bounded-latency
cancellation checkpoints. A filter that delegates to a long, indivisible
native call must declare that limitation. Cancellation latency is part of the
filter/worker behavioral contract and should be visible in tests and
diagnostics.

Do not describe cancellation as instantaneous. The interactive target is that
the current result becomes stale immediately and cooperative work stops at the
next checkpoint. Define and test a cancellation-latency budget separately for
preview, batch, and shutdown operations.

Escalate only when a worker crashes, fails its health/liveness contract, or
does not honor cancellation or shutdown within its bounded grace period:

1. stop accepting work for that worker generation;
2. mark all of its outstanding requests failed or canceled with an explicit
   reason;
3. request graceful `SHUTDOWN` and wait for the configured grace period;
4. call `Process.terminate()` only if the process remains alive;
5. wait again, then use `Process.kill()` where available if termination also
   fails;
6. join the child and record its exit code;
7. discard the old connection rather than attempting to reuse it;
8. clean up parent-owned shared memory and record suspected child-owned leaks;
   and
9. start a new process generation only when restart policy allows it.

Forced termination may skip `finally` blocks, leave descendants alive, corrupt
active pipes or queues, and strand acquired locks. It is a containment action,
not the ordinary cancellation mechanism. A force-killed worker's channel and
worker-owned synchronization state are never reused.

Make ownership explicit:

- the supervisor owns the `Process`, parent connection, process-generation
  counter, restart policy, and final join;
- the worker owns its child connection, backend/decoder state, and cleanup of
  resources it created;
- request messages identify shared-memory owner and release/acknowledgement
  duties; and
- the process that creates a child is the only process that calls its
  lifecycle methods.

Use the process sentinel and connection readiness to supervise exit and
messages without blocking the Qt event loop. The protocol client may use a
small dedicated I/O thread or bounded event-loop integration to wait on IPC,
but no scientific compute runs in that thread and GUI mutation still occurs on
the Qt main thread. The CLI uses the same supervisor and message models without
a Qt adapter.

Maintain bounded queues and admission:

- a CPU worker has at most one active request and a small bounded pending set;
- the singular GPU worker selected in architecture §10 serializes its jobs;
- preview requests use latest-request-wins coalescing instead of accumulating
  stale slider positions;
- batch work uses explicit backpressure rather than unbounded submission; and
- control commands needed for cancellation and shutdown must not be trapped
  behind an unbounded work queue.

Separate protocol, supervisor, and worker-loop responsibilities. The
implementation may be roughly a few hundred lines initially, but line count is
not an architectural requirement. Keep the surface small through typed state
machines and shared helpers rather than omitting lifecycle states or failure
handling to meet an arbitrary size.

Test the protocol under the `spawn` context on supported platforms. Tests cover:

- readiness and successful request/result flow;
- cancellation before start and during cooperative work;
- late/stale progress, success, failure, and cancellation events;
- repeated latest-wins requests;
- worker exception and unexpected exit;
- ignored cancellation followed by forced termination and clean replacement;
- graceful application shutdown with active and idle workers;
- parent or GUI teardown while the worker is sending;
- shared-memory acknowledgement and cleanup after every terminal path;
- bounded admission and GPU serialization; and
- no surviving child process or leaked resource after the test.

GUI tests continue to set `QT_QPA_PLATFORM=offscreen` as required by the
repository instructions.

No throughput benchmark is required to select this abstraction. In-flight
cancellation, state retention, bidirectional control, and explicit recovery are
functional constraints that eliminate the task-pool alternatives. Benchmark
worker startup, command latency, cancellation latency, shared-memory transport,
and steady-state throughput when tuning the implementation.

This ADR refines ADR-002. It does not replace ADR-002's separate-process,
shared-memory transport, descriptor lifetime, or zero-copy boundary.

## Alternatives considered [INTENT]

### multiprocessing.Pool

[INTENT] `Pool` provides worker creation, task distribution, and result collection.
Its `AsyncResult` supports waiting and timeouts but not cancellation of an
already running task. `Pool.terminate()` stops workers and outstanding work
rather than expressing cooperative cancellation and stateful recovery for one
request.

### concurrent.futures.ProcessPoolExecutor

[INTENT] The futures API is convenient for independent calls and queued-work
cancellation. Once a future is running, `Future.cancel()` returns false. Adding
a separate cancellation channel and persistent worker state around the
executor would bypass its abstraction while leaving SIEVE without direct
ownership of the process protocol.

### billiard

[INTENT] billiard extends Python multiprocessing and is used by Celery. SIEVE does not
need Celery-compatible pool behavior or another multiprocessing fork. Its
required long-lived single-worker protocol can be expressed with the standard
library, avoiding an additional runtime dependency and compatibility layer.

### One Process per request

[INTENT] Per-request processes make hard cancellation and failure isolation easy because
the process is disposable. They repeatedly pay interpreter, import, decoder,
model, and GPU initialization costs and do not naturally retain state across
interactive previews. They remain a possible isolation boundary for a future
untrusted or uniquely failure-prone operation, not the default worker model.

### Threads or QThread

[INTENT] Threads avoid process IPC but do not provide the process isolation selected in
ADR-002. Native compute, decoder behavior, or the GIL can still interfere with
the GUI process, and Python has no safe thread force-termination mechanism.

### asyncio subprocesses

[INTENT] `asyncio.create_subprocess_exec` is useful for supervising external executables
and streaming bytes. SIEVE's worker needs Python object protocol models, named
shared-memory descriptors, retained Python backend state, and integration with
both Qt and non-async CLI callers. Adding an asyncio event loop does not solve
cooperative in-flight cancellation inside the worker.

### Celery or another distributed task system

[INTENT] A distributed task system supplies brokers, retries, routing, monitoring, and
fleet execution. It adds services and delivery semantics beyond a local GUI/CLI
worker and still requires task code to cooperate for prompt cancellation.
SIEVE can add an HPC scheduler handoff without making the local interactive
worker a distributed queue.

## Status

Accepted.

## Consequences

- SIEVE owns a small, versioned worker state machine instead of delegating
  lifecycle semantics to a task pool.
- `multiprocessing.Process` and `multiprocessing.connection.Connection` are the
  standard-library lifecycle and control primitives.
- All supported platforms use the `spawn` start context, making child
  initialization explicit and testable.
- Workers can retain decoder, filter, shared-memory, and backend state across
  requests.
- Cooperative cancellation can interrupt in-flight work at defined
  checkpoints while stale-result rejection takes effect immediately.
- Filters and pipeline stages acquire a cancellation-latency responsibility;
  indivisible native calls must expose their limitation.
- Forced process termination remains available for containment but requires
  discarding IPC and synchronization state and carefully cleaning resources.
- Request and process generations prevent obsolete results or errors from
  mutating current state.
- GUI and CLI share protocol and supervisor code; only event-delivery adapters
  differ.
- Latest-wins coalescing and bounded admission prevent interactive work from
  building an obsolete queue.
- Shared-memory payload ownership and acknowledgement remain coupled to the
  protocol and must be correct on success, cancellation, failure, crash, and
  shutdown.
- Parent and worker shutdown, restart limits, heartbeat policy, and user-facing
  failure diagnostics become explicit implementation responsibilities.
- The custom implementation requires substantial race, crash, leak, Windows
  spawn, and offscreen-GUI testing.
- No billiard, Celery, or other process-pool runtime dependency is introduced.
- The implementation is expected to stay focused, but an approximate
  200-line estimate is not used as a correctness constraint.

## References [STABLE]

- [Python multiprocessing documentation](https://docs.python.org/3/library/multiprocessing.html)
- [Python multiprocessing connections](https://docs.python.org/3/library/multiprocessing.html#connection-objects)
- [Python multiprocessing process lifecycle](https://docs.python.org/3/library/multiprocessing.html#process-and-exceptions)
- [Python concurrent.futures documentation](https://docs.python.org/3/library/concurrent.futures.html)
- [SIEVE architecture: worker
  criteria](../04-architecture/ARCHITECTURE.md#10-worker-architecture--criteria)
- [SIEVE architecture: determinism
  policy](../04-architecture/ARCHITECTURE.md#12-determinism-policy--criteria)
- [ADR-002: Use subprocess workers and shared memory for
  frames](ADR-002-use-subprocess-workers-and-shared-memory-for-frames.md)
- [ADR-007: Use structlog for structured
  logging](ADR-007-use-structlog-for-structured-logging.md)
- [ADR-008: Use pytest, Hypothesis, and
  pytest-benchmark](ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
