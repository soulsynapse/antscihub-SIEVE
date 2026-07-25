# ADR-009: Use Nox for task orchestration

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE has several required development and validation tasks:

- Ruff lint and format checks;
- Pyright type checking;
- fast and slow pytest suites;
- canonical-pipeline determinism checks;
- performance regression checks; and
- generated schema and documentation builds.

These tasks need stable local and CI entry points and a composed quality gate.
Copying command sequences into contributor instructions and CI workflow files
would let local and automated validation drift.

The task graph will also accumulate conditional behavior. GPU tests should run
when CUDA and the required backend are available, while CPU-only environments
must report why they were skipped. GL-dependent GUI tests require a capable
display, while ordinary PySide6 tests use Qt's offscreen platform. Some tasks
will need platform-specific arguments, environment variables, generated-file
checks, or dependency groups.

SIEVE's repository instructions currently require validation and tests to use
the repository `.venv`. The initial task runner must preserve that operational
contract rather than silently selecting a different interpreter.

## Decision

Use Nox as SIEVE's development and CI task orchestrator.

Keep the canonical session definitions in a repository-root `noxfile.py`.
Express orchestration and capability checks in ordinary Python. Keep tool
policy in each tool's authoritative configuration:

- Ruff, Pyright, and pytest configuration remains in `pyproject.toml`;
- documentation and schema generators own their own configuration; and
- `noxfile.py` defines how those tools are composed and invoked, not duplicate
  rule sets.

Provide focused sessions with stable names, including at least:

```text
lint
typecheck
test
test_slow
determinism_check
benchmark
build_docs
checks
```

`checks` is the composed, non-mutating quality gate. It runs linting, type
checking, the fast test suite, the determinism check, and generated
documentation/schema freshness checks. Slow tests and performance benchmarks
may be separate scheduled sessions when their runtime or hardware requirements
make them unsuitable for every inner-loop run, but the full CI and release
workflow must invoke them explicitly.

Session names are the supported automation interface. CI calls Nox sessions
instead of restating their internal commands. Contributor documentation should
show the same session invocations.

Run local Nox and its validation commands through the repository `.venv` until
the repository's environment policy is superseded. On Windows, the canonical
form is:

```console
.\.venv\Scripts\python.exe -m nox -s checks
```

Initial sessions use Nox's `venv_backend="none"` pass-through mode so their
commands execute in that activated interpreter environment instead of creating
per-session virtual environments.

Nox is selected here primarily for task orchestration and composition, not to
silently create a second local dependency universe. If isolated or
multi-version Nox environments are added later, their interpreter and
dependency-lock relationship to the repository `.venv` must be explicit and
CI must exercise the same resolved dependencies used for supported
validation.

Use Python capability checks for optional hardware and platform sessions. A
GPU session:

1. detects the required backend and CUDA capability;
2. runs the marked GPU tests when capability is present; and
3. emits a clear skip reason when capability is absent.

CI jobs intended to prove GPU support must run in a required-GPU mode where
missing or unusable CUDA is a failure, not a skip. Conditional execution on a
developer's CPU-only machine must not allow a nominal GPU CI job to pass
without exercising GPU code.

Ordinary GUI test sessions set `QT_QPA_PLATFORM=offscreen`. GL-dependent
renderer sessions detect or require a GL-capable environment and remain
separate from the ordinary offscreen test session.

Gate sessions are non-mutating. Formatting, autofix, schema regeneration, and
documentation regeneration may have explicit developer sessions, but CI
checks freshness and fails rather than rewriting the checkout.

Pin Nox and task dependencies in the project's development dependency
definition. Use shared Python helpers in `noxfile.py` for repeated setup,
capability detection, and command construction rather than copying logic
between sessions.

## Alternatives considered

### tox

tox is mature and particularly strong at testing packages across interpreter
and dependency matrices. Its conventional configuration is declarative, which
is effective for regular environment matrices but less direct for the
platform and hardware conditionals SIEVE expects to accumulate. Implementing
CUDA probing, conditional GPU requirements, GL-capable sessions, generated
artifact checks, and composed project tasks is more naturally expressed in
Nox's Python session file.

tox remains a reasonable choice if multi-interpreter packaging matrices become
the dominant orchestration concern. That is not SIEVE's current task shape.

### CI workflow commands

Putting all commands directly in GitHub Actions or another CI system avoids an
additional local dependency. It duplicates the task graph between CI and
developer workflows and makes local reproduction of composed checks harder.

### Make

Make can compose commands effectively, but Windows is a supported development
environment and cannot be assumed to provide it. Python-based sessions also
handle capability detection and cross-platform path behavior more naturally.

### PowerShell and shell scripts

Platform-specific scripts provide complete control but require parallel
Windows and POSIX implementations or a mandatory compatibility shell. Nox
keeps orchestration in the project's existing implementation language.

### Ad hoc Python scripts

Plain scripts could implement every task, but Nox provides session discovery,
selection, parameterization, lifecycle hooks, and a conventional automation
interface without requiring SIEVE to build a task runner.

## Status

Accepted.

## Consequences

- Local development and CI share named task entry points.
- `nox -s checks` provides a composed quality gate instead of requiring users
  to remember an ordered command list.
- Conditional CUDA, GL, platform, and generated-artifact logic is expressed
  directly in Python.
- Hardware-dependent skips are visible, and required GPU CI cannot silently
  pass without GPU execution.
- Tool rules remain in their native configuration rather than being copied
  into `noxfile.py`.
- The current repository `.venv` remains the local validation interpreter;
  introducing Nox-managed environment matrices requires an explicit,
  reproducible dependency policy.
- Nox and the tools used by its sessions become pinned development
  dependencies.
- CI configuration becomes smaller but depends on the stability of public Nox
  session names.
- Changes to task composition become code changes that receive ordinary
  review and tests where appropriate.
- Non-mutating gate sessions and explicit fix/generation sessions prevent CI
  from concealing stale or incorrectly formatted artifacts.

## References

- [Nox documentation](https://nox.thea.codes/en/stable/)
- [Nox sessions](https://nox.thea.codes/en/stable/config.html)
- [tox documentation](https://tox.wiki/en/stable/)
- [ADR-003: Adopt Ruff as the Python quality gate](ADR-003-adopt-ruff-as-the-python-quality-gate.md)
- [ADR-008: Use pytest, Hypothesis, and pytest-benchmark](ADR-008-use-pytest-hypothesis-and-pytest-benchmark.md)
- [SIEVE architecture: determinism policy](../04-architecture/ARCHITECTURE.md#12-determinism-policy--criteria)
- [SIEVE architecture: maintainability patterns](../04-architecture/ARCHITECTURE.md#19-maintainability-patterns)
