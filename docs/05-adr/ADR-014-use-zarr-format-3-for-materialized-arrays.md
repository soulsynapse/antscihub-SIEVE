# ADR-014: Use Zarr format 3 for materialized arrays

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE keeps intermediate arrays in memory while the user edits a pipeline and
materializes them only when the user requests compaction or the application
explicitly responds to memory pressure. Architecture §5 assigns those persisted
N-dimensional intermediates to Zarr because they must retain dtype and shape,
support partial access, and remain practical for local and HPC workflows.

The architecture has not yet selected a Zarr on-disk format version. That
choice affects metadata, codec configuration, storage layout, downstream
interoperability, and whether the store can use standardized sharding.

Zarr format 3 is the current specification generation and is the default for
new arrays created by Zarr-Python 3. It provides an indexed sharding codec that
places multiple independently compressed inner chunks in one storage object.
This can reduce file or object counts while retaining chunk-level reads, which
is relevant to shared filesystems and object stores used in HPC workflows.

Zarr format 2 remains readable by Zarr-Python 3, but supporting both formats in
SIEVE would require format detection, two codec/configuration paths,
compatibility fixtures, and decisions about which format is emitted at each
boundary. SIEVE has no current downstream consumer that requires format 2 and
no repository-owned format 2 data that requires an in-place migration path.

The Zarr-Python package major version and the Zarr on-disk format version are
related but distinct. Installing Zarr-Python 3 makes the v3 API available and
defaults new arrays to format 3, but the library can still create or read format
2 when asked. A dependency constraint alone therefore does not enforce SIEVE's
storage format.

## Decision

Write all SIEVE-managed Zarr arrays and groups using Zarr format 3.

Set `zarr_format=3` explicitly at the repository's storage boundary even when
that is the library default. Centralize Zarr creation and opening in
`io/zarr_store.py`; pipeline, filter, GUI, CLI, and HPC code must not construct
stores independently.

Declare Zarr-Python as a runtime dependency using:

```toml
dependencies = [
  "zarr>=3,<4",
]
```

`zarr>=3` by itself is a lower bound, not a pin. The `<4` upper bound keeps
SIEVE on the selected API major, while the committed uv lockfile selected by
ADR-012 records the exact resolved version. Upgrading to Zarr-Python 4 requires
an intentional compatibility review and dependency update; it does not
necessarily require changing the Zarr format if version 4 still supports
format 3.

Do not implement a Zarr format 2 writer, reader fallback, dual-format store, or
v2 compatibility test matrix in the SIEVE runtime. Do not pass through a
caller's arbitrary `zarr_format` option. The format version is an application
storage invariant, not a per-run preference.

Reject an existing format 2 store with a clear diagnostic before attempting to
use it as a SIEVE compaction artifact. If a concrete downstream tool later
requires format 2, handle that requirement as an explicit export or offline
conversion boundary and record it in a new ADR. Do not weaken the internal
format invariant preemptively.

Store enough SIEVE metadata at the group root to validate the artifact before
reading array payloads. At minimum, record:

- a SIEVE store-schema version distinct from `zarr_format`;
- pipeline, node, filter, backend, and cache identities;
- array names and their semantic roles;
- dtype, dimension names, units, and declared valid ranges where applicable;
- source and code provenance needed by the cache contract; and
- completion state or a committed manifest that distinguishes a published
  store from an interrupted write.

Zarr format 3 does not replace SIEVE's own schema version. The Zarr format
describes the storage protocol; the SIEVE schema describes what arrays and
attributes mean.

Use v3 sharding when the access pattern and storage target justify it. Treat
inner chunk shape and outer shard shape as separate choices:

- inner chunks are chosen for the smallest useful read/write unit and working
  memory;
- shards group inner chunks to reduce filesystem or object-store object count;
  and
- compression remains inside the shard so inner chunks are independently
  addressable.

Do not enable one universal shard shape for every array. Video-like
time-height-width data, masks, derived channels, and other tensors can have
different access patterns. Establish defaults from representative local and
HPC workloads, record the resolved chunk, shard, codec, and storage
configuration in artifact metadata, and include that configuration in any
identity whose physical-layout reproducibility matters.

HPC workers must not concurrently mutate the same shard without a storage
coordination design that explicitly makes that safe. Prefer assigning workers
disjoint stores, arrays, or shard regions and publish completed artifacts
atomically. Sharding reduces object count; it is not itself a concurrent-write
protocol.

Use public Zarr-Python 3 APIs and format-3 codecs. Do not depend on private
`zarr.core` modules or reintroduce v2-era APIs such as `DirectoryStore`,
`create_dataset`, `zarr_version`, or codecs configured through the old
format-2 path.

Validate the storage boundary with tests that:

- assert newly written arrays and groups report Zarr format 3;
- round-trip representative dtypes, shapes, dimension metadata, and fill
  values;
- read slices spanning inner chunks and shard boundaries;
- detect incomplete or incompatible SIEVE store schemas;
- reject format 2 fixtures with the intended diagnostic;
- verify cache and provenance metadata survives reopen; and
- exercise the supported local-directory store plus each remote or HPC store
  adapter before that adapter is advertised as supported.

No Zarr v2-versus-v3 benchmark is required for this format decision. There is
no downstream v2 constraint, and maintaining two format paths has an immediate
complexity cost. Benchmarks remain necessary for choosing chunk shapes, shard
shapes, codecs, concurrency, and store-specific tuning.

## Alternatives considered

### Zarr format 2

Format 2 has broad historical ecosystem support and could be required by an
older downstream reader. SIEVE currently has no such consumer. Selecting it
would give up the v3 storage model and standardized sharding while creating a
future migration obligation for no present benefit.

If an actual v2-only consumer appears, an explicit export path is preferable
to making SIEVE's internal materialization format legacy-compatible.

### Read v2 and write v3

This is a common migration posture for an established application with old
artifacts. SIEVE does not currently own legacy v2 stores. Adding a read path
would create compatibility code and tests for hypothetical data and make it
unclear whether v2 artifacts satisfy current SIEVE schema and provenance
requirements.

### Configurable v2 or v3 output

A format switch appears flexible but doubles the meaningful storage
configurations and lets projects silently become dependent on different
capabilities. Storage-format choice does not vary with scientific intent, so
it should remain an application invariant.

### HDF5

HDF5 provides mature typed N-dimensional storage and efficient slicing.
Concurrent and distributed access depends on deployment-specific HDF5 builds
and file-locking behavior, and the single-file model is less natural for the
filesystem/object-store and HPC handoff architecture already selected. This
ADR narrows an existing Zarr architecture choice rather than reopening the
container-format decision.

### TileDB or another array database

An array database can provide sophisticated sparse storage, querying, and
concurrency. It would introduce a larger storage abstraction and operational
surface than SIEVE currently needs. Zarr format 3 supplies the portable
chunked/sharded artifact required by the existing architecture.

### Unsharded Zarr v3 everywhere

Unsharded v3 is valid and may be the right layout for small arrays or
filesystems where individual chunk objects are cheap. Prohibiting sharding
would discard a useful v3 capability for large HPC artifacts. The storage
policy permits both layouts and chooses between them from measured workload
geometry.

### Sharded Zarr v3 everywhere

Always sharding may reduce object counts but can increase read amplification,
write contention, and partial-shard update cost when shard geometry does not
match the workload. Format 3 is mandatory; sharding is a layout decision.

## Status

Accepted.

## Consequences

- Every SIEVE-created Zarr artifact uses format 3 explicitly.
- Zarr-Python `>=3,<4` becomes a constrained runtime dependency, with the uv
  lockfile selecting the exact installed release.
- `io/zarr_store.py` becomes the sole supported construction and validation
  boundary for materialized array stores.
- SIEVE carries one Zarr-format implementation and test matrix rather than v2
  and v3 paths.
- Existing or externally supplied v2 stores fail clearly instead of being
  interpreted as current SIEVE artifacts.
- A future v2-only downstream requirement must be handled explicitly through
  export/conversion or by superseding this ADR.
- The SIEVE artifact-schema version remains separate from the Zarr format
  version.
- Sharding is available to reduce chunk-object counts on HPC and object
  storage while preserving independently compressed inner chunks.
- Chunk, shard, codec, and concurrency policy still require workload-specific
  measurement; format selection does not settle performance tuning.
- Parallel writers require disjoint ownership or an explicit coordination
  design because shards are not a synchronization primitive.
- Store creation records resolved physical layout and scientific/provenance
  metadata so artifacts remain diagnosable and reproducible.
- Downstream tools must support Zarr format 3 or consume an explicitly
  converted/exported representation.
- Zarr-Python major upgrades and codec changes receive explicit compatibility
  review instead of entering through an unconstrained dependency update.

## References

- [Zarr-Python 3 migration guide](https://zarr.readthedocs.io/en/stable/user-guide/v3_migration/)
- [Zarr format 3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/)
- [Zarr v3 indexed sharding codec](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/)
- [Zarr-Python performance guide](https://zarr.readthedocs.io/en/stable/user-guide/performance/)
- [Zarr-Python glossary: sharding](https://zarr.readthedocs.io/en/stable/user-guide/glossary/)
- [SIEVE architecture: storage
  substrate](../04-architecture/ARCHITECTURE.md#5-storage-substrate--filesystem-as-truth-without-the-cost)
- [SIEVE architecture: cache-key
  criteria](../04-architecture/ARCHITECTURE.md#8-cache-key--criteria)
- [SIEVE architecture: component
  decomposition](../04-architecture/ARCHITECTURE.md#14-component-decomposition)
- [SIEVE architecture: CLI and
  HPC](../04-architecture/ARCHITECTURE.md#16-cli-and-hpc)
- [ADR-012: Use uv and Hatchling for
  packaging](ADR-012-use-uv-and-hatchling-for-packaging.md)
- [ADR-013: Use DuckDB over Parquet for analytical
  results](ADR-013-use-duckdb-over-parquet-for-analytical-results.md)
