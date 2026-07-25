# ADR-007: Use structlog for structured logging

Reference: https://docs.arc42.org/section-9/

## Context

[ASSUMPTION] SIEVE runs work across the CLI, GUI, long-lived worker subprocesses, local
benchmarks, and eventual HPC jobs. Operators and developers need to correlate
events across those boundaries and answer questions such as which pipeline
node ran, which backend was selected, why a fallback occurred, how long a
stage took, and which run produced an error.

The benchmark architecture also expects data to be inspected with DuckDB.
Machine-readable event records make diagnostic and operational data queryable
alongside benchmark results. Plain formatted log messages force downstream
tools to parse prose and make fields such as run identity, filter identity,
backend, duration, and failure reason inconsistent.

Python's standard-library `logging` module supports extensible records and
formatters, but it does not itself establish a convenient event-dictionary
workflow, contextual binding, or a consistent structured schema. SIEVE would
need to build those conventions and adapters.

The architecture separately assigns authoritative benchmark outputs to a
Parquet/DuckDB results table and performance timelines to CTF traces. Logging
[INTENT] Logging complements those products rather than becoming an accidental replacement
for either one.

## Decision

Use structlog as SIEVE's application logging API.

Emit structured event dictionaries with stable field names. At minimum, every
rendered event includes:

- an event name;
- timestamp;
- severity level; and
- process identity.

Bind relevant context at lifecycle boundaries rather than repeating it at
every call. Depending on scope, that context includes:

- run, job, and generation identifiers;
- pipeline and node identifiers;
- filter name and version;
- selected backend;
- source asset or replicate identity; and
- worker identity.

Use UTC timestamps for persisted logs. Use a human-readable console renderer
for interactive local use and newline-delimited JSON for machine-readable
files, automated runs, and HPC collection. JSON records must remain directly
ingestible by DuckDB without parsing message prose.

Integrate standard-library logging into the same rendering pipeline so logs
from dependencies and existing modules have consistent timestamps, levels,
destinations, and process metadata. Application code should use structlog
event fields rather than embedding structured values in formatted message
strings.

Define and version a small logging field contract before logs become an
analysis interface. Adding optional fields is compatible; renaming or changing
the meaning or type of an established field requires a deliberate migration.
Do not rely on arbitrary event prose as a stable query key.

Use logs for operational events, diagnostics, decisions, warnings, failures,
and coarse timing context. Continue to use:

- the benchmark results table as the authoritative typed record of benchmark
  inputs and outcomes;
- the metric bus for live HUD values; and
- CTF traces for high-volume timing and execution timelines.

Benchmark code may derive exploratory tables from structured logs, but a
queried log stream is not the canonical benchmark-results schema.

Avoid unbounded per-frame logging in normal operation. Per-frame or inner-loop
events must be disabled by default, sampled, or sent to the tracing/metrics
layer. Measure durations with a monotonic clock and render them as numeric
fields in an explicit unit; wall-clock timestamps are for event ordering, not
elapsed-time measurement.

Redact secrets and credentials before rendering. Do not log full model dumps,
environment mappings, or configuration-source contents by default. Exception
events include structured exception information while preserving the bound
run and worker context.

## Alternatives considered

### Standard-library logging alone

The standard library is stable, ubiquitous, and sufficient for plain
application logs. It can emit JSON with custom formatters and adapters, but
SIEVE would need to construct its own contextual event-dictionary conventions
and keep them consistent across processes. structlog supplies those mechanisms
while retaining interoperability with `logging`.

### Loguru

Loguru offers a concise API, convenient sinks, and structured serialization.
Its logger model is less centered on explicit event dictionaries and
processor pipelines. structlog is a closer fit for stable, queryable fields
and context binding while still accepting standard-library log records.

### OpenTelemetry logs

OpenTelemetry could unify logs with distributed traces and metrics, but SIEVE
does not currently require a telemetry collector or distributed observability
backend. Adopting that stack now would add deployment and schema complexity.
Structured event fields can be mapped to OpenTelemetry later if those
requirements emerge.

### Benchmark results stored only as logs

Logs are flexible for diagnostics and exploratory DuckDB queries, but they do
not replace the typed, purpose-specific benchmark table. Treating logs as the
only result store would make schema evolution, completeness, and authoritative
result selection harder.

## Status

Accepted.

## Consequences

- Operational and diagnostic events are queryable by stable fields rather
  than by parsing prose.
- Local console output can remain readable while automated and HPC runs emit
  JSON Lines from the same event calls.
- Run, pipeline, node, backend, and worker context can follow events through
  nested application operations.
- DuckDB can inspect structured logs alongside benchmark data for diagnosis
  and exploratory analysis.
- A documented event-field contract, context-binding policy, and
  initialization path are required for the GUI, CLI, and spawned workers.
- Worker processes must initialize logging independently and preserve
  correlation identifiers supplied by the parent process.
- Standard-library and third-party log records require integration and may
  contain less structured context than native structlog events.
- High-frequency events remain the responsibility of metrics and tracing;
  unrestricted per-frame logging would distort performance and create
  excessive storage.
- Benchmark results, live metrics, traces, and logs remain separate artifacts
  with explicit responsibilities.
- structlog becomes a constrained runtime dependency.
- Tests should assert event names and structured fields before rendering,
  rather than snapshotting colored console output.

## References

- [structlog documentation](https://www.structlog.org/en/stable/)
- [structlog standard-library integration](https://www.structlog.org/en/stable/standard-library.html)
- [Python logging documentation](https://docs.python.org/3/library/logging.html)
- [DuckDB JSON overview](https://duckdb.org/docs/stable/data/json/overview.html)
- [SIEVE architecture: component decomposition](../04-architecture/ARCHITECTURE.md#14-component-decomposition)
- [SIEVE architecture: backend dispatch criteria](../04-architecture/ARCHITECTURE.md#9-backend-dispatch--criteria)
- [SIEVE architecture: CLI and HPC](../04-architecture/ARCHITECTURE.md#16-cli-and-hpc)
