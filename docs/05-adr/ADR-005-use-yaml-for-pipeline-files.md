# ADR-005: Use YAML for pipeline files and generated JSON Schema

Reference: https://docs.arc42.org/section-9/

## Context

[INTENT] The pipeline artifact is SIEVE's project file, CLI input, and HPC handoff
format. `ARCHITECTURE.md` section 7 requires it to be human-editable, fully
describe a run, round-trip through the GUI without semantic loss, use explicit
DAG references, carry a schema version, and remain stable under changes that
are irrelevant to cache keys.

Users need to inspect and edit pipeline files directly. Editors and the
user-facing `sieve validate pipeline.yaml` command also need a machine-readable
schema for completion, navigation, and precise validation feedback. Maintaining
the file format and a separate hand-written schema would allow them to drift.

ADR-004 selects Pydantic v2 as the authoritative filter and pipeline contract
and requires JSON Schema generation from those models.

## Decision

Use YAML as the serialized pipeline-file format. The conventional filename is
`pipeline.yaml`.

Pipeline YAML is a data format, not an executable configuration language.
Load it with a safe YAML loader. Do not support arbitrary object construction,
code execution, or implicit application settings in pipeline files.

Validate the loaded YAML data against the Pydantic v2 pipeline models selected
in ADR-004. Generate JSON Schema from those same models for editor
autocomplete, tooling, and schema-aware validation. Generate
`PIPELINE_SCHEMA.md` from the exported JSON Schema and associated model
metadata rather than maintaining a parallel schema by hand.

The generated schema must describe the top-level pipeline schema version,
nodes, explicit input-node and output-slot references, filter discriminators,
and filter-specific parameter models. The pipeline schema version is distinct
from individual filter versions.

Cache keys must be computed from validated model data using the canonical
serialization defined by the filter contract, not from YAML bytes, mapping
order, whitespace, comments, anchors, or scalar spelling. Reformatting a
pipeline file must therefore leave its cache identity unchanged.

Saving an unchanged pipeline through the GUI must preserve its represented
pipeline data. Formatting and comments are presentation concerns and are not
part of the scientific or cache-key contract unless a future ADR explicitly
selects a round-trip YAML representation that preserves them.

## Alternatives considered

### JSON pipeline files

JSON aligns directly with JSON Schema and has fewer parser ambiguities, but it
is less convenient for the hand-edited project and HPC handoff files required
by the architecture. JSON remains the schema vocabulary, not the primary
pipeline serialization.

### TOML pipeline files

TOML is human-readable and well suited to configuration, but nested,
heterogeneous DAG nodes and explicit graph edges are a less natural fit than
YAML. Its editor-schema ecosystem also does not align as directly with the
Pydantic-generated JSON Schema used by the contract.

### Python files or an executable DSL

Executable pipeline definitions would provide flexibility but make safe
validation, portable HPC handoff, deterministic inspection, and editor
tooling harder. They would also violate the requirement that the artifact
fully and declaratively describe a run.

### Hand-written YAML and JSON schemas

Maintaining separate schemas would duplicate the Pydantic contract and allow
validation, editor completion, and runtime behavior to diverge.

## Status

Accepted.

## Consequences

- Pipeline files are directly readable and editable by users comfortable with
  YAML.
- The GUI, CLI, local executor, and HPC handoff share one interchange format.
- Editors can use generated JSON Schema for completion and diagnostics even
  though the persisted artifact is YAML.
- YAML parsing and Pydantic validation remain separate stages; syntax errors
  and contract errors should be reported distinctly by `sieve validate`.
- The project must select and constrain a safe YAML library.
- YAML features that do not survive ordinary load/model/dump cycles, including
  comments, anchors, aliases, and presentation choices, are not promised to
  round-trip unless the implementation deliberately preserves them.
- YAML's implicit scalar typing can surprise users. The loader policy and
  validation errors must make ambiguous values visible rather than silently
  coercing them into unintended parameter types.
- Schema generation needs a deterministic command and a stale-artifact check
  so `PIPELINE_SCHEMA.md` and the editor-facing JSON Schema cannot drift from
  the Pydantic models.
- Cache stability depends on canonical validated data, not serialized YAML
  text.

## References [STABLE]

- [YAML 1.2.2 specification](https://yaml.org/spec/1.2.2/)
- [JSON Schema specification](https://json-schema.org/specification)
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [ADR-004: Use Pydantic v2 for the filter contract](ADR-004-use-pydantic-v2-for-the-filter-contract.md)
- [SIEVE architecture: pipeline artifact criteria](../04-architecture/ARCHITECTURE.md#7-pipeline-artifact--criteria)
- [SIEVE architecture: cache-key criteria](../04-architecture/ARCHITECTURE.md#8-cache-key--criteria)
- [SIEVE architecture: coherence mechanisms](../04-architecture/ARCHITECTURE.md#17-coherence-mechanisms)
