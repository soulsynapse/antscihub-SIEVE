# ADR-010: Use VizTracer and py-spy for complementary profiling

Reference: https://docs.arc42.org/section-9/

## Context

[INTENT] SIEVE needs to answer two different performance questions.

[INTENT] The benchmarking workflow needs planned, repeatable timelines for known
pipeline phases such as decode, downsample, detect, aggregate, and write. The
benchmarking vision selects VizTracer to emit Chrome Trace Event JSON for
inspection in Perfetto. This path is intentionally enabled for a measured run
and can include SIEVE-defined phase boundaries and resource counter events.

[ASSUMPTION] Production diagnosis starts from a different situation: a user reports that
the GUI is stuttering or a worker is unexpectedly slow, but the process was
not launched with tracing enabled. Restarting with instrumentation can lose
the behavior, and instrumentation overhead can perturb the workload being
investigated.

[STABLE] VizTracer is an instrumenting tracer that requires activation for the target run.
py-spy is a sampling profiler that can attach to an already-running Python
process without adding profiling calls to SIEVE's code. They answer related
questions but have different activation, overhead, and output semantics.

[STABLE] CPU-side Python tools do not provide authoritative GPU-kernel timing. The
benchmarking vision already assigns PyTorch GPU profiling to `torch.profiler`
and CuPy or custom-kernel profiling to NVTX and Nsight Systems.

## Decision

Use VizTracer for planned, opt-in SIEVE timeline traces.

Implement `bench/tracer.py` as SIEVE's VizTracer integration boundary. It
controls trace activation, records stable algorithmic phase names, attaches
run and process metadata, emits resource counters when available, and writes
Chrome Trace Event JSON suitable for Perfetto. Phase-level tracing is the
default; function-level tracing is an explicit deeper diagnostic mode.

Use py-spy for ad hoc sampling of an already-running GUI or worker process,
including production and user-reported stutter investigations.

Implement `bench/pyspy.py` as a thin diagnostic wrapper around the external
py-spy executable. The wrapper may:

- identify or accept the target PID and process role;
- validate that py-spy is available;
- construct supported `record`, `top`, or `dump` invocations;
- choose a repository-standard output location and filename;
- record profiling metadata such as timestamp, PID, process role, run ID,
  git revision, sampling rate, duration, and command; and
- report actionable permission or attachment failures.

The wrapper must not reimplement a sampler or treat py-spy as an in-process
SIEVE library. It must display the command being executed and must not request
administrator, root, ptrace, or container capabilities automatically.

For a GUI-stutter report, profile the GUI process first to distinguish event
loop, painting, serialization, and orchestration stalls. If the GUI is waiting
on compute, profile the responsible worker PID separately. Preserve run and
process-role identifiers so multiple profiles from the same incident can be
correlated.

Use distinct artifact roles:

- **VizTracer trace:** instrumented event timeline with SIEVE-defined phase
  spans and counters for a deliberately traced run.
- **py-spy profile:** sampled Python stack distribution or snapshot from a
  live process, especially one not started in tracing mode.
- **benchmark results table:** authoritative run-level measurements and
  scientific outcomes.
- **structured logs:** operational context and correlation events.

Do not compare VizTracer and py-spy timings as if they were measurements from
the same instrument. Record the profiler type and settings with each artifact.
Do not enable both profilers during a benchmark used for performance
regression claims unless the measurement explicitly studies profiler
overhead.

Make VizTracer and py-spy optional diagnostic dependencies rather than
mandatory imports on SIEVE's normal runtime path. A production installation
intended to support live diagnosis should make the py-spy executable available
through a documented diagnostic dependency or deployment option.

Treat captured profiles as potentially sensitive. Stack samples and trace
metadata can expose paths, function names, source structure, arguments
included in event metadata, and workload timing. Do not capture secrets or raw
pipeline parameter values by default, and obtain the appropriate authorization
before attaching to a process outside the current user's diagnostic scope.

## Alternatives considered

### VizTracer alone

[ASSUMPTION] VizTracer supplies the planned phase timeline and integrates with the chosen
Chrome Trace Event workflow. It does not reconstruct the behavior of a process
that was not launched with tracing active. Continuous tracing would add overhead
and storage cost and could perturb intermittent GUI behavior.

### py-spy alone

[ASSUMPTION] py-spy can attach to a live process with no SIEVE code instrumentation and is
well suited to locating hot Python stacks. Sampling does not provide the same
explicit pipeline-phase spans, async relationships, or SIEVE-defined resource
counters as the planned VizTracer trace.

### cProfile

[ASSUMPTION] cProfile is built into Python and useful for bounded local investigations, but
its deterministic call tracing has higher perturbation for Python-heavy code
and does not address attachment to an already-running uninstrumented process.
The benchmarking vision already rejects it as SIEVE's primary benchmarking
trace tool.

### Scalene

[ASSUMPTION] Scalene provides CPU, memory, and Python-versus-native attribution and may be
useful for focused investigations. It adds another profiling workflow and does
not replace the selected Perfetto timeline or the simple attach-to-PID
production diagnostic provided by py-spy.

### Continuous application profiling

[ASSUMPTION] Continuous profiling would make incidents observable from process start,
but imposes continuous overhead, storage, privacy, and lifecycle costs.
SIEVE instead retains structured operational logs and activates
profilers deliberately.

## Status

Accepted.

## Consequences

- Planned benchmark runs retain VizTracer's phase-level Perfetto timeline.
- A running GUI or worker can be sampled after a stutter or slowdown is
  observed without first restarting it in an instrumented mode.
- `bench/tracer.py` and `bench/pyspy.py` provide explicit, separate integration
  surfaces.
- Profile metadata and process-role identifiers allow GUI and worker artifacts
  from one incident to be correlated.
- Operators need documented PID discovery, output collection, and
  platform-specific attach-permission guidance.
- py-spy availability in production diagnostics is a deployment choice, not a
  mandatory application-runtime dependency.
- Sampling has overhead even though it requires no SIEVE instrumentation;
  benchmark claims must identify profiler state.
- Neither tool replaces GPU-native profiling for authoritative kernel timing.
- Profile artifacts require retention and privacy handling because they may
  reveal implementation and environment details.
- Tests should verify wrapper command construction, metadata, missing-tool
  behavior, and permission-error reporting without requiring privileged
  attachment in the ordinary suite.

## References

- [SIEVE benchmarking vision](../01-vision/benchmarking-vision.md)
- [VizTracer documentation](https://viztracer.readthedocs.io/en/stable/)
- [py-spy documentation](https://github.com/benfred/py-spy)
- [Perfetto trace viewer](https://ui.perfetto.dev/)
- [ADR-007: Use structlog for structured logging](ADR-007-use-structlog-for-structured-logging.md)
- [SIEVE architecture: component decomposition](../04-architecture/ARCHITECTURE.md#14-component-decomposition)
