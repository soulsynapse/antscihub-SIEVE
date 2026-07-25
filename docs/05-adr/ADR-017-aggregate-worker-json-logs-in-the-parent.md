# ADR-017: Aggregate worker JSON logs in the parent

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE runs compute in long-lived `multiprocessing.Process` workers under the
versioned supervisor protocol selected in ADR-015. ADR-007 selects structlog,
UTC timestamps, stable event fields, and JSON Lines for machine-readable logs.
It requires each worker to initialize logging independently while preserving
run, process, worker, and generation context.

Without a subprocess bridge, worker logs can:

- interleave unreadably on an inherited console;
- write separate files whose rotation, naming, retention, and discovery drift;
- bypass the parent application's console/file configuration;
- lose supervisor-authoritative worker identity; or
- become confused with worker result messages and high-volume trace data.

The parent process already owns worker identity, process generation, lifecycle,
restart policy, and user-facing presentation. It is therefore the correct
aggregation point for local structured logs.

The logging channel has a different contract from the ADR-015 control channel.
Control messages must remain available for cancellation, health, results, and
shutdown even when logging is noisy. Logs are append-only diagnostic events;
they are not commands, acknowledgements, or scientific results.

The architecture also assigns opt-in algorithmic timelines to VizTracer Chrome
Trace Event Format files through `bench/tracer.py`. CTF events are higher
volume, use a different schema and clock model, and are opened in Perfetto.
Sending them through structlog or stderr would distort execution and erase the
separation selected by ADR-007 and ADR-010.

`multiprocessing.Process` does not expose the `stderr=PIPE` capture option
provided by `subprocess.Popen`. A per-worker stderr bridge must therefore be
created explicitly. On the supported `spawn` context, relying on inherited
console descriptors would not give the parent an independently readable,
worker-specific stream.

## Decision

Render each worker's application log events as one UTF-8 JSON object per line
to its Python-level `sys.stderr`. Aggregate those events in the parent and
forward the parsed event dictionaries through the parent's configured
structlog sink pipeline.

Give every worker a dedicated one-way logging connection separate from its
duplex command/event connection. Create the connection from the same explicit
`multiprocessing` spawn context used by ADR-015. Pass only the worker's writable
endpoint into the child and keep only the readable endpoint in the supervisor.

At the beginning of the worker entry point, before application logging is
initialized:

1. install a write-only, line-buffered text adapter as `sys.stderr`;
2. have that adapter encode complete UTF-8 lines and send them over the
   worker's one-way logging connection;
3. configure structlog with a final `JSONRenderer`;
4. bind worker-local context; and
5. emit a structured logging-ready event.

The adapter is SIEVE's cross-platform Python stderr bridge. It uses public
multiprocessing connection APIs rather than private spawn-handle machinery.
The bytes transported are still newline-delimited JSON records, even if the
connection also preserves message boundaries.

Do not claim that replacing `sys.stderr` captures every native write to
operating-system file descriptor 2. Python `print(..., file=sys.stderr)`,
uncaught Python tracebacks, and logging handlers targeting the current
`sys.stderr` use the adapter. CUDA libraries, C extensions, `faulthandler`, or
external child processes may write directly to the inherited OS handle and
bypass it. If complete native-stderr capture becomes a requirement, add and
test an OS-level redirection path per supported platform; do not imply the
Python stream adapter already provides it.

After logging initialization, application-owned worker code must not write
plain text to `sys.stderr`. Use structlog event dictionaries. Configure
standard-library logging from Python dependencies to enter the same worker
JSON renderer where practical.

Define a versioned worker log envelope. Each worker-emitted JSON object contains
at least:

- log schema version;
- event name and level;
- UTC worker timestamp;
- worker-local monotonic sequence number;
- process PID;
- run and request identifiers when available;
- logger/component name; and
- structured event fields and normalized exception information.

Do not serialize arbitrary exception objects. Render safe exception type,
message, stack information, and structured diagnostic fields according to the
redaction policy in ADR-007.

Treat worker-supplied identity as diagnostic, not authoritative. On ingestion,
the parent adds or overwrites:

- supervisor-assigned worker ID and role;
- process generation;
- observed PID;
- parent receive timestamp;
- parent run/job context; and
- an origin marker identifying the event as worker-produced.

Preserve the original worker timestamp separately from the parent receive
timestamp. Preserve per-worker order using the worker sequence number. Do not
claim a total event order across workers merely from arrival order or wall-clock
timestamps.

Use a dedicated parent reader thread or equivalent non-GUI I/O component to
drain each worker logging connection continuously. It may parse and enqueue
events, but it must not mutate Qt objects. Final GUI presentation is dispatched
onto the Qt main thread. CLI and headless execution use the same aggregator
without the Qt adapter.

The ingestion path:

1. receives one bounded byte record;
2. validates UTF-8, JSON object shape, schema version, and maximum size;
3. attaches supervisor-authoritative context;
4. normalizes the level through an allowlist;
5. passes the event dictionary to the parent ingestion logger; and
6. lets the parent sink configuration render console, JSONL file, or other
   approved outputs.

Do not treat the received JSON as an opaque message string and JSON-encode it a
second time. The parent pipeline operates on the parsed event dictionary. Its
ingestion path must avoid reapplying processors that would overwrite the
worker's timestamp, sequence, exception fields, or event meaning. Parent-only
processors may add reception, presentation, routing, and redaction fields.

If a record is malformed, oversized, undecodable, or uses an unsupported
schema, emit one parent-generated `worker_log_decode_failed` event containing
bounded safe metadata. Never recursively feed the raw malformed line back into
the worker stream. Truncate or hash unsafe raw content rather than copying
unbounded data into logs.

Logging must not deadlock scientific work or cancellation:

- the parent begins draining before the worker can emit ordinary events;
- the logging channel is independent from control IPC;
- event size is bounded;
- per-frame and inner-loop logging remains prohibited or sampled by ADR-007;
- downstream sink work is buffered away from the pipe-drain loop; and
- shutdown drains accepted records to EOF within a bounded grace period.

Use a bounded parent-side buffer and make overload visible. Preferentially
discard debug and informational events under sustained overload, increment
per-worker/per-level drop counters, and emit an aggregate
`worker_logs_dropped` warning when capacity returns or the worker exits. Do not
silently discard warnings, errors, lifecycle events, or the only evidence of a
worker crash. If those cannot be retained, emit a parent-side logging-pipeline
failure signal through an independent emergency sink.

The log connection lifecycle follows the process generation:

- create a fresh logging connection for every worker generation;
- close unused endpoint copies immediately after spawn;
- drain until EOF after graceful worker exit;
- on crash or forced termination, drain available complete records, close the
  old connection, and never reuse it for the replacement worker; and
- stop the aggregator only after all worker readers and parent sinks have
  completed bounded shutdown.

Keep worker logs separate from protocol events. The parent may translate a
supervisor-owned lifecycle transition into a parent log event, but it must not
infer protocol state from log text. A lost log cannot change cancellation,
result publication, resource cleanup, or restart behavior.

### VizTracer channel

VizTracer CTF output is a separate artifact channel. A traced worker writes its
trace to a temporary file and publishes it on successful flush with a name
containing at least:

```text
run_id
worker_role
process_generation
pid
```

PID alone is insufficient because PIDs can be reused and can collide across
HPC nodes. Include hostname or scheduler-task identity when traces from
multiple machines may be collected.

The worker emits only small structured log events describing trace start,
completion, failure, and final artifact path. It does not stream CTF records
through stderr, the parent log pipeline, or the worker control channel.

`bench/tracer.py` owns trace discovery, validation, identity remapping, and
post-hoc merging. It:

- discovers only artifacts belonging to the requested run;
- rejects or clearly marks incomplete/corrupt traces;
- maps process identity into a collision-free merged PID namespace;
- preserves worker role, original PID, process generation, host, and run
  metadata;
- combines valid process traces into one derived CTF artifact;
- records the input trace set and merger/tool version; and
- never deletes the per-process source traces merely because a merge succeeds.

VizTracer documents PID-suffixed per-process reports and post-hoc combination.
The SIEVE wrapper uses explicit filenames because process generation, run, and
host identity are stronger than PID alone.

The merged trace is derived. Per-process trace files remain the diagnostic
sources unless a separately documented retention policy removes them. The
benchmark results table selected in ADR-013 links the run to the merged trace
and may also retain a manifest of source trace paths.

No benchmark is required to select separate JSONL logging and CTF channels.
They have different schemas, consumers, volume, and lifecycle requirements.
Measure logger overhead, pipe-drain capacity, drop behavior, tracer overhead,
trace size, and merge time when tuning the implementation.

This ADR refines ADR-007, ADR-010, and ADR-015. It does not merge logs, metrics,
benchmark rows, protocol events, or traces into one artifact.

## Alternatives considered

### logging QueueHandler and QueueListener

Python's logging cookbook explicitly recommends `QueueHandler` and
`QueueListener` as a multiprocessing aggregation pattern. It is a meaningful
alternative, not an absence of one.

SIEVE prefers the JSONL bridge because it creates a process-neutral, versioned
wire representation that can be inspected independently and does not couple
the worker-parent boundary to pickled `LogRecord` objects or parent logging
internals. The parent still centralizes routing and presentation.

### Send log events over the worker control channel

This avoids another connection and preserves a single ordered stream. Bursty
logging could delay cancellation, health checks, results, and cleanup. Logs and
protocol state also have different delivery and overload semantics, so they
remain separate.

### Workers write separate JSONL files

Per-worker files are simple, crash-tolerant, and useful on distributed systems.
For local supervised workers they duplicate file naming, rotation, retention,
redaction, and console routing while delaying user-visible errors. Separate
files remain a valid HPC collection mode when there is no live parent
aggregator, provided they use the same schema and are ingested later.

### Workers inherit the parent's stderr

This requires almost no setup, but lines from multiple processes can interleave
and the parent cannot reliably attach supervisor identity, route events, or
apply one sink policy. It also fails the per-worker lifecycle boundary.

### Workers send unrendered event dictionaries

Sending dictionaries avoids JSON parsing and can preserve richer Python types.
It couples the IPC boundary to Python serialization and processor versions and
makes the raw stream less inspectable. Rendering JSON in the worker freezes the
wire contract at the process boundary.

### syslog, journald, Windows Event Log, or OpenTelemetry

System or telemetry collectors can aggregate many processes and hosts. They add
platform-specific configuration or external services that SIEVE does not need
for its local GUI/CLI supervisor. A parent sink may forward accepted events to
one of these systems later without changing the worker JSON schema.

### Stream VizTracer events through the log bridge

This would combine two JSON-shaped streams but not two equivalent data models.
CTF volume and timing semantics would pressure cancellation/logging IPC, and
structlog processing would add overhead to trace events. Disk artifacts with
post-hoc merge preserve the profiler contract.

### One shared CTF file written by all workers

Concurrent writes would require coordination and turn a worker crash into
shared-file corruption risk. Independent files align trace ownership with
process lifecycle and can be merged deterministically after completion.

## Status

Accepted.

## Consequences

- Workers emit one versioned structlog JSON object per Python stderr line.
- Every worker generation has a dedicated one-way log connection independent
  from its bidirectional command/event connection.
- The parent is the single routing and presentation point for supervised local
  worker logs.
- Parent-authoritative worker identity and process generation are added during
  ingestion rather than trusted from worker JSON.
- Parsed event dictionaries enter the parent pipeline without nested JSON or
  destructive reprocessing.
- Per-worker ordering is recoverable; cross-worker arrival is not treated as a
  total order.
- A continuously draining reader prevents ordinary pipe backpressure from
  blocking control handling or compute.
- Bounded buffers, level-aware overload behavior, and explicit drop accounting
  become implementation requirements.
- Python-level stderr is captured; complete native file-descriptor-2 capture is
  not promised by this decision.
- Malformed worker output becomes a bounded parent diagnostic instead of
  corrupting the aggregate stream.
- Worker logging failure cannot drive protocol state or scientific result
  selection.
- Standard-library `QueueHandler`/`QueueListener` remains a credible rejected
  alternative; the rationale does not depend on claiming universal consensus.
- VizTracer writes one CTF file per traced process generation rather than
  sending trace events through logs or IPC.
- Trace filenames include stronger identity than PID alone, avoiding PID reuse
  and cross-host collision.
- `bench/tracer.py` owns post-hoc validation, identity remapping, merge
  provenance, and the derived combined trace.
- Per-process CTF files remain source artifacts under an explicit retention
  policy.
- Logging and tracing overhead, capacity, drop behavior, and shutdown races
  require tests even though no selection benchmark is needed.

## References

- [structlog documentation](https://www.structlog.org/en/stable/)
- [structlog processors](https://www.structlog.org/en/stable/processors.html)
- [structlog standard-library
  integration](https://www.structlog.org/en/stable/standard-library.html)
- [Python logging cookbook: logging from multiple
  processes](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes)
- [Python multiprocessing
  connections](https://docs.python.org/3/library/multiprocessing.html#connection-objects)
- [VizTracer concurrency and report
  combination](https://viztracer.readthedocs.io/en/stable/concurrency.html)
- [VizTracer API](https://viztracer.readthedocs.io/en/stable/viztracer.html)
- [SIEVE benchmarking vision: per-run
  timeline](../01-vision/benchmarking-vision.md#layer-b--per-run-timeline-tenet-3)
- [ADR-007: Use structlog for structured
  logging](ADR-007-use-structlog-for-structured-logging.md)
- [ADR-010: Use VizTracer and py-spy for complementary
  profiling](ADR-010-use-viztracer-and-py-spy-for-complementary-profiling.md)
- [ADR-013: Use DuckDB over Parquet for analytical
  results](ADR-013-use-duckdb-over-parquet-for-analytical-results.md)
- [ADR-015: Manage long-lived workers with
  multiprocessing.Process](ADR-015-manage-long-lived-workers-with-multiprocessing-process.md)
