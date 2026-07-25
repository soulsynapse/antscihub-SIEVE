# ADR-004: Use Pydantic v2 for the filter contract

Reference: https://docs.arc42.org/section-9/

## Context

[INTENT] SIEVE's filter contract is the single source of truth for filter parameters.
The GUI, CLI, pipeline loader, cache-key construction, cost model, validation
command, and generated documentation consume that contract without
maintaining parallel parameter declarations.

The contract needs to:

- [INTENT] User-authored pipeline parameter validation and readable errors for
  the user-facing `sieve validate pipeline.yaml` command described in
  `ARCHITECTURE.md` section 16;
- export JSON Schema so editor support and `PIPELINE_SCHEMA.md` can be
  generated rather than maintained by hand;
- represent the pipeline's `filter type + params` polymorphism without custom
  dispatch code;
- immutable parameter objects, so validated parameters remain unchanged
  after their canonical cache-key representation has been computed; and
- validate cheaply enough that parameter validation is not a meaningful part
  of per-frame processing cost.

[INTENT] Application configuration has a related but distinct requirement: settings
are loaded from supported external sources such as environment variables
without mixing source-loading behavior into the scientific filter models.

## Decision

Use Pydantic v2 models as the authoritative schema and validation mechanism
for SIEVE filter parameters and serialized pipeline models.

Define filter parameter models with `model_config = ConfigDict(frozen=True)`.
All cache-key inputs must be derived from the validated, immutable model using
one canonical serialization path. Mutable objects nested inside a model must
either be represented by immutable types or normalized before they contribute
to a cache key; `frozen=True` alone does not make arbitrary nested values
deeply immutable.

Represent polymorphic filter nodes with Pydantic discriminated unions keyed by
the serialized filter-type field. Each filter type maps to its own parameter
model, and validation selects that model through the discriminator.

Generate JSON Schema from the Pydantic models. Generate the schema content in
`PIPELINE_SCHEMA.md` from that exported schema; do not maintain a second,
hand-written parameter schema in documentation.

Use `pydantic-settings` for application and runtime configuration. Keep
configuration-source concerns separate from filter parameter and pipeline
models: settings models may read environment or other configured sources,
while scientific contract models validate explicit values.

Validation belongs at contract boundaries such as pipeline load, GUI edits,
CLI input, and job submission. Per-frame filter implementations consume
already validated parameter objects; they do not need to reconstruct the same
model for every frame.

## Alternatives considered

### Standard-library dataclasses

Dataclasses can express typed parameter containers but do not provide the
required validation and JSON Schema generation. SIEVE would need to build or
adopt separate schema, error-reporting, and discriminated-union layers,
undermining the single-source-of-truth requirement.

### msgspec

[ASSUMPTION] msgspec prioritizes serialization and validation performance and may be faster
for some workloads. Pydantic has the broader validation, JSON Schema,
settings, editor, and integration ecosystem needed by SIEVE. Parameter
validation is not expected to dominate frame-processing cost, so the narrower
performance advantage does not outweigh that ecosystem fit.

### attrs

attrs is a capable model-building library, but it does not itself supply the
required JSON Schema and settings stack. Selecting it would require SIEVE to
assemble and maintain those layers separately.

### Hand-written dictionaries and validators

Hand-written parsing would duplicate the contract across validation, schema
generation, GUI generation, and serialization. It is incompatible with the
architecture's single-source-of-truth requirement.

## Status

Accepted.

## Consequences

- Filter parameter declarations, validation, serialized schema, and generated
  editor metadata share one source.
- `sieve validate pipeline.yaml` can report structured Pydantic validation
  errors with precise locations instead of custom parser failures.
- Discriminated unions make the serialized filter type determine the
  corresponding parameter schema and error path.
- Frozen parameter models prevent attribute reassignment and support stable
  cache-key construction, provided nested values are also immutable or
  canonicalized.
- `PIPELINE_SCHEMA.md` becomes a generated artifact and requires a
  deterministic generation command plus a check that detects stale output.
- Pydantic v2 and `pydantic-settings` become runtime dependencies whose
  versions must be constrained and upgraded deliberately.
- Settings source precedence, prefixes, secrets handling, and supported config
  sources must be specified when runtime configuration is implemented.
- Pydantic's validation overhead is acceptable at pipeline and parameter
  boundaries, but models must not be needlessly rebuilt inside the per-frame
  processing loop.
- The project is committed to Pydantic v2 APIs such as `ConfigDict`,
  `model_validate`, `model_dump`, and `model_json_schema`; v1 compatibility
  patterns are not part of the contract.

## References [STABLE]

- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [Pydantic discriminated unions](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions)
- [Pydantic configuration](https://docs.pydantic.dev/latest/api/config/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [SIEVE architecture: filter contract criteria](../04-architecture/ARCHITECTURE.md#6-filter-contract--criteria)
- [SIEVE architecture: cache-key criteria](../04-architecture/ARCHITECTURE.md#8-cache-key--criteria)
- [SIEVE architecture: CLI and HPC](../04-architecture/ARCHITECTURE.md#16-cli-and-hpc)
