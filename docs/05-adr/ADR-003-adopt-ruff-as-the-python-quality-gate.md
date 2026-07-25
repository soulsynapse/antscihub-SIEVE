# ADR-003: Adopt Ruff as the Python quality gate

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE needs one repository-wide standard for Python linting, import ordering,
and formatting. The standard must give developers fast local feedback and
produce deterministic pass/fail results in automated checks. It must cover
application code, tests, scripts, and top-level Python files without requiring
different tool configurations for different parts of the repository.

The project also needs strict static type checking in its core and pipeline
code. Linting and type checking catch different classes of defects, so choosing
a linter must not displace Pyright.

Ruff combines lint rules derived from tools including Pyflakes, pycodestyle,
isort, pyupgrade, flake8-bugbear, and Pylint with a formatter. A combined tool
reduces configuration, dependency, and editor-integration overhead compared
with assembling equivalent behavior from several independent tools.

The repository is early enough that stronger rules can be adopted without a
large legacy cleanup, but making every prospective rule mandatory immediately
would create avoidable churn. The quality gate therefore needs a ratcheting
path toward stricter enforcement.

## Decision

Use Ruff as SIEVE's required Python linter, import sorter, and formatter.

Keep the canonical Ruff configuration in the repository-root
`pyproject.toml`. The root location ensures that the same policy applies to
`src/`, `tests/`, scripts, and top-level Python files.

The non-mutating quality-gate commands are:

```console
ruff check .
ruff format --check .
```

Developers may use `ruff check --fix .` and `ruff format .` locally. Automated
workflows must not apply fixes or use `--unsafe-fixes`; they report a failing
gate and leave the source unchanged.

Use stable Ruff behavior in the gate. Preview rules and preview formatting are
not enabled. Pin the Ruff version in the development and CI dependency
definition when those environments are added, and update it deliberately.

Treat the enabled rule set as a ratchet. Establish a clean baseline, make that
baseline mandatory, and then add stricter rule families or remove targeted
exceptions. Do not weaken the baseline merely to make new code pass. The
root `pyproject.toml` is authoritative for the currently enforced rules; this
ADR does not freeze the individual rule-code list.

Continue using Pyright for static type checking, with strict checking focused
on `src/sieve/core` and `src/sieve/pipeline`. Ruff supplements Pyright; it does
not replace it.

Ruff may enforce Python docstring conventions and format code examples in
docstrings if those rules are enabled later. It is not the quality gate for
Markdown prose, links, or spelling; documentation-specific tooling may be
adopted separately.

## Alternatives considered

### Black, isort, and Flake8

This combination is mature and widely understood, but requires multiple
dependencies, configurations, editor integrations, and invocations to provide
the linting, import-ordering, and formatting behavior SIEVE needs.

### Pylint with Black and isort

Pylint provides deep and highly configurable analysis, but the combined
toolchain is slower and more operationally complex. Ruff already implements
the selected Pylint-derived rule families, while Pyright covers the separate
type-analysis responsibility.

### Pyright alone

Rejected because a type checker does not replace formatting, import ordering,
or the broad range of correctness and maintainability checks supplied by a
linter. Pyright remains required alongside Ruff.

### No mandatory repository-wide gate

Rejected because editor-only or contributor-specific checks allow style and
basic correctness failures to vary by development environment and reach shared
branches.

## Status

Accepted.

## Consequences

- All maintained Python files use one root configuration and one lint/format
  tool.
- Local checks should be fast enough to run frequently and the same commands
  can be used by CI.
- Pyright remains a separate required dependency and gate because Ruff is not
  a static type checker.
- Ruff must be installed and version-pinned in the development and CI
  environments before the automated gate is operational.
- Existing code must pass the configured baseline before enforcement can be
  made mandatory.
- Increasing strictness requires deliberate rule changes, cleanup, and
  documented targeted exceptions where a rule does not fit the code.
- Ruff upgrades can change diagnostics or formatting. Version changes require
  an explicit update and a repository-wide check.
- Automated checks do not rewrite source, reducing the risk of an unattended
  fix changing behavior.
- Markdown documentation requires separate tooling if prose, link, or spelling
  checks become mandatory.

## References

- [Ruff configuration](https://docs.astral.sh/ruff/configuration/)
- [Ruff linter](https://docs.astral.sh/ruff/linter/)
- [Ruff formatter](https://docs.astral.sh/ruff/formatter/)
- [Ruff rule reference](https://docs.astral.sh/ruff/rules/)
- [Pyright configuration](https://microsoft.github.io/pyright/#/configuration)
