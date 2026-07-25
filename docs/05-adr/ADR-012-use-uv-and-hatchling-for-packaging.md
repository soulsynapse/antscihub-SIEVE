# ADR-012: Use uv and Hatchling for packaging

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE needs a packaging and dependency-management toolchain for:

- declaring project metadata and runtime and development dependencies;
- installing the project for local development and Nox sessions;
- resolving and locking dependency versions; and
- building standards-compliant source distributions and wheels.

The repository already uses `pyproject.toml` for Ruff and Pyright
configuration, has a `src` layout, and has selected Nox as its development and
CI task interface in ADR-009. It does not yet declare installable project
metadata, dependencies, a build backend, or a lockfile.

Using separate dependency manifests for runtime, development, CI, and
packaging would create multiple declarations that can drift. The project needs
one authoritative declaration of dependency intent while retaining an exact,
generated resolution for reproducible environments.

The resolver and installer will be used frequently in local development and
CI, so resolution and installation speed matter. The build backend should
support standard `pyproject.toml` metadata and editable installs without
requiring the project to adopt an integrated environment, publishing, and task
management workflow.

This is a tooling choice rather than a product hypothesis. An experiment would
primarily measure team preference and transient tool performance, so no
project-specific spike is required.

## Decision

Use uv for dependency resolution, locking, virtual-environment management, and
package installation.

Use Hatchling as the PEP 517 build backend. Declare it in `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Declare project metadata and direct dependency constraints through the
standard `[project]` tables defined by PEP 621. Runtime dependencies belong in
`project.dependencies`. Declare the development toolchain as a `dev` optional
dependency so the project and its development dependencies can be installed
together:

```toml
[project.optional-dependencies]
dev = [
  # Nox, test, lint, type-check, benchmark, and documentation dependencies.
]
```

`pyproject.toml` is the single source of truth for direct dependency
declarations and version constraints. Do not maintain parallel
`requirements.in`, hand-authored `requirements.txt`, or tool-specific
dependency declarations for the same environments.

Commit the generated `uv.lock` file. It is the exact resolution derived from
`pyproject.toml`, not a second hand-edited dependency manifest. Dependency
changes are made in `pyproject.toml` or with a uv command that updates
`pyproject.toml`; the resulting lockfile change is reviewed with the
declaration change.

Retain Nox as the public task-orchestration interface selected in ADR-009.
Nox sessions that need the installed project create or use their session
environment and install the editable package and development extra with:

```console
uv pip install -e ".[dev]"
```

Centralize that installation in a shared `noxfile.py` helper rather than
repeating it in each session. Invoke `uv` as an external command explicitly
where required by Nox.

This installation command resolves the constraints in `pyproject.toml`; it
does not exact-sync the session from `uv.lock`. Therefore, the default Nox
session contract tests the currently resolvable dependency set allowed by the
declared constraints. Workflows that must reproduce the committed resolution
exactly must use a uv lock-aware sync/export path and must be named explicitly.
Do not describe an ordinary `uv pip install -e ".[dev]"` Nox session as a
locked environment.

This ADR supersedes only the environment-management parts of ADR-009 that
require every Nox command to pass through the repository `.venv` and prescribe
`venv_backend="none"` for initial sessions. ADR-009's selection of Nox,
session names, composed quality gates, capability checks, and non-mutating CI
policy remain in force.

Hatchling is selected as a small standards-based build backend. PEP 621
standardizes the `[project]` metadata table; it does not designate Hatchling
or any other implementation as a reference backend.

## Alternatives considered

### Poetry

Poetry supplies dependency resolution, locking, environment management,
building, and publishing as one integrated workflow. SIEVE does not need that
larger opinionated surface. Its lockfile is specific to Poetry, and adopting
Poetry would couple routine installation and packaging to Poetry's project
model. uv plus Hatchling keeps resolution and building separate while using
standard project metadata.

[ASSUMPTION] Resolver-speed claims vary by dependency graph, platform, cache state, and
tool version. The decision does not depend on a permanent universal claim
that Poetry is slow; uv's observed and documented focus on fast resolution and
installation is sufficient for this repository.

### PDM

PDM supports standards-based metadata, locking, environments, and building
and would be a technically valid choice. It offers no capability SIEVE
currently requires that offsets adding a different project-management
workflow from the uv tooling already selected here. Ecosystem momentum is not
treated as a durable architectural property.

### pip and requirements files

pip is ubiquitous and could install the package through its build backend.
Maintaining requirements files alongside project metadata would either
duplicate direct dependency declarations or require an additional compile
step and convention. It also would not provide the selected cross-platform
project lock and environment workflow as one tool.

### setuptools

setuptools is mature and widely compatible. SIEVE does not currently require
its broader legacy configuration surface or extension-building capabilities.
Hatchling provides the needed standards-based pure-Python build and editable
installation path with less project-specific configuration.

### Flit

Flit is a small standards-based backend and would be suitable for a simple
pure-Python package. Hatchling offers more room for explicit file-selection
and build-hook configuration if SIEVE's application packaging grows, without
adopting Hatch's environment or task runner.

### uv with uv_build

Using uv's own build backend would reduce the number of selected projects.
Hatchling is preferred because the resolver/environment tool and build backend
remain independent choices, and Hatchling is established as a general-purpose
backend. The build backend can be reconsidered independently if SIEVE later
needs a capability Hatchling does not provide.

### Nox-managed installs without uv

Nox can call pip in its session environments. This preserves Nox's default
workflow but gives up the selected uv resolver and installer path. Nox remains
the task interface; uv owns package installation within those tasks.

## Status

Accepted.

## Consequences

- `pyproject.toml` becomes the authoritative declaration for project metadata,
  direct dependencies, development dependencies, and build-system selection.
- `uv.lock` is committed as generated exact-resolution data and is not edited
  as a parallel dependency declaration.
- uv becomes required for supported development and CI setup.
- Hatchling becomes the build dependency and controls wheel, source
  distribution, and editable-install behavior.
- SIEVE becomes installable as a package, so source inclusion, package data,
  entry points, and editable-install behavior must be validated.
- Runtime and development dependency changes are reviewed in
  `pyproject.toml` together with their resulting lockfile changes.
- Nox remains the stable user-facing task interface, but its environment setup
  moves from the repository `.venv` pass-through policy in ADR-009 to uv-backed
  editable session installs.
- Installing `.[dev]` exposes development dependencies as a published optional
  extra in built metadata. This is intentional for the chosen command, even
  though a PEP 735 development dependency group would keep them local-only.
- Default Nox installs are constrained but not lock-exact. Reproducibility
  claims must distinguish `uv pip install -e ".[dev]"` from a workflow that
  syncs the committed lockfile.
- The repository does not adopt Poetry's or PDM's integrated project workflow,
  and does not adopt Hatch's environment or task-management features merely
  because Hatchling is the build backend.
- Packaging-tool performance and ecosystem popularity may change; the durable
  decision rests on standards-based metadata, a small build backend, one
  declared dependency source, and separation between orchestration,
  resolution, and building.

## References

- [uv documentation](https://docs.astral.sh/uv/)
- [uv: project structure and files](https://docs.astral.sh/uv/concepts/projects/layout/)
- [uv: managing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/)
- [uv: locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Hatch build configuration](https://hatch.pypa.io/latest/config/build/)
- [Python Packaging User Guide: `pyproject.toml`
  specification](https://packaging.python.org/specifications/declaring-project-metadata/)
- [PEP 517: A build-system independent format for source trees](https://peps.python.org/pep-0517/)
- [PEP 621: Storing project metadata in `pyproject.toml`](https://peps.python.org/pep-0621/)
- [PEP 735: Dependency Groups in `pyproject.toml`](https://peps.python.org/pep-0735/)
- [ADR-009: Use Nox for task orchestration](ADR-009-use-nox-for-task-orchestration.md)
