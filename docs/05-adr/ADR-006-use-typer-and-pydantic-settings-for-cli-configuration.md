# ADR-006: Use Typer and pydantic-settings for CLI configuration

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE has three configuration sources with different lifetimes and
responsibilities:

1. Pipeline YAML describes a particular run: its graph, filter types,
   parameters, edges, and schema version.
2. User preferences persist ergonomic and runtime defaults across runs.
3. CLI flags express ephemeral choices for one invocation.

Without explicit ownership and precedence, the same setting can acquire
different values depending on where it was supplied. That makes runs difficult
to explain and reproduce and makes the GUI, CLI, and HPC paths drift.

The architecture already assigns composition to the pipeline artifact.
`ARCHITECTURE.md` section 17.2 states that pipeline YAML is the interchange
format and that every GUI pipeline action mutates the graph. Introducing
another general-purpose configuration-composition layer would duplicate that
responsibility.

SIEVE also exposes a `sieve bench pipeline.yaml --sweep params.yaml` command.
Its sweep semantics may eventually require parameter matrices, derived values,
conditional combinations, or large multirun expansion. The current
architecture does not yet establish that level of complexity.

## Decision

Use Typer to define SIEVE's command-line interface. CLI commands remain thin
adapters that:

- parse command names, arguments, and flags;
- load the pipeline and relevant settings;
- resolve the effective invocation configuration;
- call application services shared with the GUI and other entry points; and
- render structured results and errors for terminal users.

Do not place pipeline composition, validation rules, execution policy, or
scientific behavior in Typer callbacks.

Use `pydantic-settings`, as selected in ADR-004, for persistent user
preferences and runtime settings. Use ordinary Pydantic v2 models for pipeline
data and for the resolved invocation passed to application services.

Keep the three sources distinct:

- **Pipeline YAML** owns the scientific graph and per-run filter parameters.
- **User preferences** provide persistent defaults for settings that are
  explicitly preference-controlled. They must not silently rewrite the
  pipeline graph or filter parameters.
- **CLI flags** provide explicit, ephemeral overrides for the fields exposed
  by a command. They do not mutate the pipeline file unless a command is
  specifically documented as an editing command.

For a field that is intentionally available from more than one source, use
this precedence:

```text
explicit CLI flag > pipeline value > user preference > application default
```

Absence is different from an explicitly supplied false, zero, empty, or null
value. The resolver must retain that distinction when applying precedence.

After resolution, application services receive one validated effective
configuration. Diagnostics, run metadata, and HPC handoff must be able to
report the effective values and their sources where those values affect
execution or reproducibility. Cache keys continue to include every resolved
value that can change scientific output, as required by the cache-key
contract.

Do not adopt Hydra initially. The pipeline artifact is already SIEVE's
composition system, and a Hydra composition tree on top of it would create two
ways to describe a run.

Reconsider Hydra, in a separate ADR, only if real `--sweep` requirements
outgrow a validated sweep-spec model and a straightforward Cartesian or
explicit-case expander. Evidence for reconsideration would include recurring
needs for conditional sweep composition, reusable hierarchical experiment
groups, override grammars, launch plugins, or multirun orchestration that
SIEVE would otherwise have to rebuild. Hydra must not become a second
authoritative representation of an individual pipeline even if adopted for
experiment expansion.

## Alternatives considered

### argparse

`argparse` is in the standard library and can implement the required commands,
but Typer provides typed command declarations, conversion, help generation,
and shell-completion support with less adapter code. The CLI remains thin
enough that Typer's abstraction is sufficient.

### Click

Click is mature and underlies Typer. Using it directly would provide more
low-level control, but SIEVE benefits from Typer's type-driven declarations
and alignment with the Pydantic-typed application boundary.

### Hydra

Hydra provides powerful hierarchical configuration, overrides, sweeps, and
multirun support. Those capabilities are valuable when configuration
composition is the application's primary run-description system. In SIEVE,
pipeline YAML already fills that role. Adopting Hydra now would duplicate
composition, introduce a second override syntax, and make configuration
provenance harder to explain.

Hydra remains a candidate if implemented sweep requirements demonstrate that
its experiment-composition and launcher ecosystem would replace substantial
custom machinery rather than duplicate the pipeline contract.

### Configuration logic inside individual commands

Letting each command independently merge files, preferences, and flags would
be simple initially but would produce inconsistent precedence and validation
across `run`, `preview`, `bench`, `hpc-export`, and `validate`.

## Status

Accepted.

## Consequences

- Pipeline YAML remains the single composition and interchange format for an
  individual run.
- Typer supplies a typed, discoverable CLI without becoming an application or
  scientific-logic layer.
- Persistent preferences, per-run pipeline data, and ephemeral flags have
  explicit ownership.
- Overlapping values use one documented precedence rule and preserve the
  distinction between absent and explicitly supplied values.
- A shared resolver and effective-configuration model are required so every
  command and frontend applies identical precedence and validation.
- Run diagnostics should expose configuration provenance instead of showing
  only the final values.
- Settings that affect scientific output must be included in cache identity
  and recorded in reproducibility metadata even when sourced from preferences
  or CLI flags.
- `--sweep` starts with a Pydantic-validated sweep specification and simple
  expansion semantics rather than a second configuration framework.
- Advanced sweep requirements may trigger a future Hydra evaluation, but
  Hydra is not a dependency or supported configuration surface under this
  decision.
- Typer and its compatible Click version become constrained runtime
  dependencies.

## References

- [Typer documentation](https://typer.tiangolo.com/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Hydra documentation](https://hydra.cc/docs/intro/)
- [ADR-004: Use Pydantic v2 for the filter contract](ADR-004-use-pydantic-v2-for-the-filter-contract.md)
- [ADR-005: Use YAML for pipeline files](ADR-005-use-yaml-for-pipeline-files.md)
- [SIEVE architecture: CLI and HPC](../04-architecture/ARCHITECTURE.md#16-cli-and-hpc)
- [SIEVE architecture: coherence mechanisms](../04-architecture/ARCHITECTURE.md#17-coherence-mechanisms)
