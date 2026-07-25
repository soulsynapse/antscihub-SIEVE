# ADR-008: Use pytest, Hypothesis, and pytest-benchmark

Reference: https://docs.arc42.org/section-9/

## Context

[STABLE] SIEVE's architecture makes testable promises about filters and pipelines:

- [STABLE] Section 19 requires property-based tests showing that valid filter
  parameters preserve the filter contract, including declared output shape,
  dtype, and NaN behavior;
- section 12 requires a canonical short clip to produce deterministic pipeline
  outputs across repeated runs and supported platforms; and
- the benchmarking vision requires performance to remain visible as filters,
  backends, and worker behavior evolve.

[ASSUMPTION] Example-based unit tests are necessary but do not practically enumerate the
valid parameter space of each filter. Hand-written parameter loops tend to
miss boundary combinations and do not shrink a failure to a minimal
reproducer.

Correctness, determinism, and performance are distinct signals. A benchmark
runner can detect timing changes, but timing repetition does not prove that
outputs are equal. Likewise, a byte comparison can prove equality for a
fixture without detecting a performance regression.

[INTENT] Some tests will necessarily decode canonical media, run full pipelines,
exercise subprocesses, initialize GUI or GPU resources, or collect stable
benchmark samples. Running the complete set on an inner-loop invocation
would make the routine suite too slow to use frequently.

## Decision

Use pytest as SIEVE's test runner and fixture framework.

Use Hypothesis for property-based tests of the filter contract. Provide shared
strategies that derive valid parameter objects from each filter's authoritative
Pydantic model while retaining filter-specific strategies where semantic
constraints require them.

A representative contract test has this shape:

```python
@given(params=filter_param_strategy(GaussianBlur))
def test_output_shape_matches_declaration(params):
    filter_ = GaussianBlur(params)
    output = filter_.apply(sample_input)

    assert output.shape == filter_.output_spec.shape_for(sample_input.shape)
    assert output.dtype == filter_.output_spec.dtype
```

The shared contract suite must cover, where declared by the contract:

- output shape, dtype, channel count, dimensionality, and valid range;
- NaN and infinity behavior;
- valid parameter boundaries and combinations;
- deterministic equality for filters that declare themselves deterministic;
- streaming and window-size preconditions;
- warmup declarations; and
- cost-estimate invariants such as non-negative time and memory.

Hypothesis tests must generate only contract-valid inputs unless the test is
specifically exercising validation failures. Retain failing examples in
Hypothesis's example database in local and CI environments where practical,
and print the reproducing example or seed in CI failure output.

Use pytest-benchmark for repeatable microbenchmarks and canonical-pipeline
performance checks. Benchmark fixtures must be fixed and deterministic;
property generation must not occur inside the timed region. Separate setup,
decode, worker startup, and steady-state processing when the distinction
matters to the performance claim.

Use ordinary pytest assertions for determinism. The canonical-clip test runs
the standard pipeline repeatedly and compares outputs byte-for-byte where the
determinism policy requires exact equality, or with an explicitly documented
tolerance for allowed platform or GPU floating-point variation.
pytest-benchmark may time the same canonical workload, but its result does not
establish output determinism.

Register a `slow` marker in pytest configuration. Mark tests
`@pytest.mark.slow` when they require material media decode, end-to-end
pipelines, subprocess or HPC-style orchestration, GPU or GL resources,
substantial Hypothesis example counts, or stable benchmark sampling.

The default inner-loop command excludes slow tests:

```console
pytest -m "not slow"
```

The full validation path runs all tests, including slow tests, on an
appropriate schedule and before releases. Do not use `slow` to hide an
ordinary unit test that can be made fast through smaller fixtures or better
isolation.

Run tests through the uv-managed `sieve` environment created by
`uv venv sieve --python 3.11` (for example,
`.\\sieve\\Scripts\\python.exe -m pytest ...`). Run PySide6 GUI tests with
`QT_QPA_PLATFORM=offscreen`; tests that require a real OpenGL context need a
separate GL-capable environment and are slow.

Performance regression gates must compare like-for-like environments. Store
benchmark metadata needed to identify the machine, Python and dependency
versions, backend, thread settings, fixture, and pipeline version. Do not use a
single universal wall-time threshold across heterogeneous developer machines.

## Alternatives considered

### unittest

[STABLE] The standard-library framework can express unit and integration tests but has
a less composable fixture and plugin model for Hypothesis and performance
benchmarking. pytest is the common integration point for the three selected
tools.

### Hand-written parameter matrices

Explicit parameter cases are useful for named regressions and scientifically
important boundaries, but they do not explore combinations broadly or shrink
failures. They supplement rather than replace Hypothesis.

### Custom timing helpers

Ad hoc `perf_counter` loops are easy to write but tend to differ in warmup,
sampling, calibration, reporting, and metadata. pytest-benchmark provides a
consistent test-integrated baseline while SIEVE's product benchmarking layer
continues to own scientific benchmark results.

### Airspeed Velocity

ASV is designed for performance tracking across repository history and may
become useful for a dedicated benchmark lab. It adds its own environment and
publishing workflow. pytest-benchmark is the smaller initial fit for
regression checks beside the tests they protect.

### Including the complete test suite by default

[INTENT] This maximizes coverage per invocation but makes routine feedback progressively
slower as media, subprocess, GUI, GPU, and benchmark tests accumulate. An
explicit slow tier preserves fast feedback while retaining a full validation
path.

## Status

Accepted.

## Consequences

- Filter implementations are tested against generated valid parameter
  combinations rather than only hand-picked examples.
- Shared strategies and shared contract assertions become maintained testing
  infrastructure tied to the Pydantic filter schema.
- Hypothesis can shrink a failing filter case to a smaller reproducible
  parameter set.
- Determinism and performance are tested separately even when they use the
  same canonical clip and pipeline fixture.
- pytest-benchmark supplies consistent sampling and reporting, but meaningful
  regression gates require controlled environments and recorded metadata.
- The `slow` marker keeps expensive integration and performance work out of
  the inner loop while making that exclusion visible and reversible.
- CI needs both a fast required test job and an appropriate slow/full-suite
  job; release validation must not omit the slow tier.
- pytest, Hypothesis, and pytest-benchmark become constrained development and
  test dependencies.
- Hypothesis strategies must track filter-contract evolution, including new
  cross-field constraints.
- Canonical media and expected results need explicit versioning, licensing,
  and update procedures.
- GUI tests follow the repository's offscreen policy, while GL-dependent
  renderer tests require separate infrastructure.

## References

- [pytest documentation](https://docs.pytest.org/en/stable/)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/en/latest/)
- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/en/latest/)
- [SIEVE architecture: determinism policy](../04-architecture/ARCHITECTURE.md#12-determinism-policy--criteria)
- [SIEVE architecture: maintainability patterns](../04-architecture/ARCHITECTURE.md#19-maintainability-patterns)
- [ADR-004: Use Pydantic v2 for the filter contract](ADR-004-use-pydantic-v2-for-the-filter-contract.md)
