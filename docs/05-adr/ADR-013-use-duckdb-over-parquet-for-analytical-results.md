# ADR-013: Use DuckDB over Parquet for analytical results

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE's benchmarking workflow produces parametric sweeps across filters,
parameters, backends, hardware, and code revisions. The results layer must
support questions such as:

- what is the economy-versus-detection Pareto frontier for each filter;
- where does signal preservation begin to fall off as spatial or temporal
  reduction increases;
- how do CPU and GPU runs compare at fixed parameters; and
- did performance or detection regress at a later code revision?

Architecture §13 makes signal-preservation measurement a prerequisite for
guidance such as "this alternative preserves similar signal at lower cost."
The benchmarking vision assigns one typed row per run to an authoritative
results table and links each row by `run_id` to its detailed trace artifact.
ADR-007 separately assigns operational diagnostics to structured logs and
live HUD values to the metric bus. The analytical results store must preserve
those boundaries rather than turning logs or transient HUD events into the
benchmark record.

Sweep results are naturally tabular and analytical. Typical access scans a
subset of columns, filters many runs, groups by filter or hardware, and computes
rankings or frontiers. SIEVE also needs portable artifacts that can be copied
from an HPC system, inspected without a running service, and read by tools
other than the application.

This decision concerns analytical benchmark results and queryable cache
inventory metadata. It does not select the payload format for content-addressed
frame, tensor, video, or N-dimensional array caches. The architecture already
assigns persisted array intermediates to Zarr and terminal outputs to their
declared formats.

## Decision

Store authoritative analytical result rows as Parquet files and use embedded
DuckDB as the canonical query engine over those files.

Parquet files are the durable source of truth. DuckDB queries them directly
with `read_parquet` or views over `read_parquet`; result ingestion does not
require loading every file into native DuckDB tables. A `.duckdb` file may
contain disposable views, macros, or materialized query accelerators, but it
must be rebuildable from the Parquet dataset and must not become the sole copy
of authoritative results.

Use `bench/results_table.py` as the application boundary for:

- validating result rows against a versioned schema;
- writing result fragments;
- discovering a result dataset;
- opening DuckDB query connections and registering stable views;
- exposing common projections used by the GUI, CLI, and reports; and
- migrating or rejecting incompatible schema versions.

Do not scatter pandas loading, concatenation, grouping, or ad hoc SQL path
construction across callers. pandas may consume a completed query result when
a plotting or interoperability API requires a DataFrame; it is not the
repository's query layer.

Keep one logical benchmark-run relation with one row per completed run, as
specified by the benchmarking vision. Its stable typed columns include at
least:

- `schema_version` and `run_id`;
- run completion timestamp and status;
- pipeline, filter, backend, and code identities;
- source or benchmark-fixture identity;
- hardware identity;
- wall time, CPU time, memory peaks, and throughput with explicit units;
- signal-preservation metric name, value, and ground-truth or baseline
  identity;
- the complete validated parameter document; and
- portable references to associated trace and output artifacts.

Promote dimensions used routinely for filtering, grouping, joining, or plotting
to typed columns. Retain the complete validated parameters in a structured
column so uncommon or newly introduced parameters are not lost. Do not require
every query to parse an opaque JSON blob for core dimensions such as filter,
backend, spatial factor, temporal factor, or detection metric.

Expose named SQL views or query functions for recurring projections, including
the economy-versus-detection candidates used to compute a Pareto frontier.
Keep the mathematical frontier calculation and its direction conventions
explicit: lower cost is better, while the direction and comparability of the
signal metric come from its declared metric contract. Do not compare rows with
different metric definitions, fixtures, baselines, or incompatible run
semantics merely because their numeric columns have the same names.

Write immutable Parquet fragments rather than having workers update a shared
file. Each completed run or collector batch writes to a temporary file in its
target directory, validates it, and publishes it with an atomic rename. File
names include collision-resistant run or batch identity. Readers ignore
temporary and incomplete files.

HPC workers may write independent fragments. Collection and optional compaction
occur as separate operations. Do not make multiple worker processes coordinate
writes through one native DuckDB database file. If a run is retried, retain
attempt identity and define explicitly which attempt is eligible for default
analysis; do not silently overwrite prior evidence.

Start without Hive partitioning. The expected initial dataset is small enough
that premature directory partitioning would add path and small-file complexity.
Add partitioning only after observed dataset size and query predicates identify
a stable, useful partition key. Compaction must preserve row values, provenance,
and schema meaning.

Schema changes are deliberate:

- adding a nullable column is compatible within the same major schema;
- changing a column's type, unit, null meaning, or scientific interpretation
  requires a migration or a new incompatible schema version;
- readers may use name-based schema union for compatible additive changes but
  must not use it to conceal incompatible types or semantics; and
- query views must make unsupported schema versions visible rather than
  silently dropping rows.

DuckDB is an in-process dependency, not a service. Supported local, CI, and HPC
workflows require no database daemon, credentials, listening port, or schema
deployment step.

No tool benchmark is required to accept this decision. Direct SQL over typed
Parquet datasets removes enough recurring query and DataFrame-assembly code to
decide the architecture on ergonomics and artifact portability. Performance
still matters operationally, but broad claims that DuckDB is always faster than
SQLite or pandas are not part of the decision.

## Alternatives considered

### Parquet files queried only through pandas or PyArrow

Parquet alone provides portable columnar storage. pandas and PyArrow can read,
filter, and combine datasets, but every analytical question would need Python
loading, grouping, joining, null-handling, and projection code. DuckDB supplies
a common relational query surface directly over the same files and can return
Arrow or pandas results when a downstream API needs them.

Parquet remains the storage format; selecting DuckDB does not make the files
proprietary to DuckDB.

### SQLite

SQLite is embedded, mature, transactional, and excellent for operational
metadata and point lookups. It could store benchmark rows and answer the
required SQL queries. The dominant SIEVE access pattern is analytical scanning
over portable columnar artifacts, not transactional row updates. SQLite would
also make a database file the interchange artifact or require an additional
Parquet export path.

SQLite remains a valid choice for a future operational queue, mutable job state,
or other transactional subsystem. This ADR does not prohibit using it for a
different workload.

### Native DuckDB tables as the authoritative store

Native tables provide transactions, indexes where appropriate, cached catalogs,
and simpler mutation within one process. A single `.duckdb` file is less
transparent as an HPC collection artifact and introduces coordination limits
for multiple writer processes. Keeping Parquet authoritative allows independent
fragment production and direct access from DuckDB and other analytical tools.

### CSV or JSON Lines

Both formats are portable and easy to inspect. They provide weaker type
preservation, larger scans, and less efficient column projection for growing
sweep datasets. JSON Lines remains the structured logging format selected by
ADR-007; logs are not the authoritative benchmark-results table.

### A client-server analytical database

PostgreSQL, ClickHouse, or another service could centralize concurrent writes,
access control, and shared dashboards. SIEVE does not currently need an
always-running service to analyze local or copied HPC artifacts. A server can
be added as a publication or fleet-aggregation layer later without replacing
the Parquet interchange format.

### A dataframe-native query framework

Polars, pandas, or another dataframe library can express the required
analytics. They would make Python expression code the shared query interface
and provide less direct interoperability with command-line SQL exploration.
DuckDB's SQL layer is the more suitable stable interface for the stated
cross-run questions.

## Status

Accepted.

## Consequences

- Parquet becomes the authoritative, portable analytical result artifact.
- DuckDB becomes a constrained runtime dependency and the supported SQL query
  surface over result datasets.
- No database server is required for local, CI, or HPC analysis.
- The GUI, CLI, reports, and agents can share named SQL projections instead of
  independently assembling pandas pipelines.
- Columnar scans, column projection, and predicate pushdown align with
  cross-run sweep analysis.
- Independent immutable fragments avoid a shared multi-process writer and make
  HPC result collection append-oriented.
- Small files may accumulate; collection needs validation and eventually may
  need measured, non-destructive compaction.
- A versioned results schema, units, null semantics, provenance, retry policy,
  and migration behavior must be defined before results become durable.
- Core analytical dimensions must be typed columns; placing every parameter in
  JSON would recreate query boilerplate inside SQL.
- A native `.duckdb` catalog is disposable unless a later ADR explicitly
  promotes it to authoritative state.
- pandas remains available at visualization and interoperability boundaries but
  is not required for routine relational queries.
- Content-addressed cache payload lookup remains deterministic through cache
  identity and filesystem manifests; DuckDB/Parquet is not placed on the
  per-frame or per-node cache-hit critical path.
- Cached array and media payloads retain their architecture-defined formats,
  including Zarr for persisted N-dimensional intermediates.
- Performance should be measured when choosing file sizes, row-group sizes,
  partitioning, and compaction thresholds; those details are not decided by
  generic tool benchmarks.

## References

- [DuckDB: reading and writing Parquet](https://duckdb.org/docs/stable/data/parquet/overview)
- [DuckDB: Parquet query guide](https://duckdb.org/docs/stable/guides/file_formats/query_parquet)
- [DuckDB: concurrency](https://duckdb.org/docs/stable/connect/concurrency)
- [DuckDB: Parquet tips](https://duckdb.org/docs/stable/data/parquet/tips)
- [Apache Arrow: reading and writing Parquet](https://arrow.apache.org/docs/python/parquet.html)
- [SIEVE architecture: storage
  substrate](../04-architecture/ARCHITECTURE.md#5-storage-substrate--filesystem-as-truth-without-the-cost)
- [SIEVE architecture: cache-key
  criteria](../04-architecture/ARCHITECTURE.md#8-cache-key--criteria)
- [SIEVE architecture: signal-preservation
  measurement](../04-architecture/ARCHITECTURE.md#13-signal-preservation-measurement)
- [SIEVE benchmarking vision: results
  table](../01-vision/benchmarking-vision.md#layer-a--results-table-tenets-1--2)
- [ADR-007: Use structlog for structured logging](ADR-007-use-structlog-for-structured-logging.md)
