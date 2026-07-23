# Reusable benchmarks are product diagnostics

Status: accepted on 2026-07-23.

## Decision

A benchmark that can help a user estimate responsiveness, runtime, throughput,
or feasibility is a product diagnostic. Its reusable measurement logic must
live in an importable package module and should be reported through a supported
CLI or UI surface.

Top-level scripts are appropriate only for:

- A disposable hypothesis test that will not be rerun as a product diagnostic.
- One-time migration or investigation work.
- Reproducible fixture construction that is not itself the measurement.
- A thin development launcher whose reusable logic lives in the package.

The presence of a JSON result in `findings/` does not by itself make a benchmark
a supported product contract. Promotion happens when the measurement has a
clear user question, declared inputs and representation, useful human output,
and a versioned machine-readable result.

## Initial application

The reusable media-service benchmark is exposed as:

```powershell
sieve media benchmark ASSET
sieve media benchmark ASSET --native
sieve media benchmark ASSET --json
```

The default measures the same capped display representation used by Isolate and
reports:

- Open-to-first-frame latency.
- Adjacent-frame latency and p95.
- Random-seek latency.
- Estimated media-service sequential frame capacity.
- Estimated realtime factor against the asset's native rate.
- Whether the media-service path fits the native frame budget.

The CLI labels this as a media-service estimate. It does not claim that GUI
painting, future overlays, or scientific processing fit the same budget. Those
layers require measurements through their own product surfaces.

Full-resolution measurement is explicit because it can be substantially more
expensive and answers a different question.

Qt viewer and interaction measurements now live in importable GUI package
modules. They are not imported by the headless CLI. They can be connected to a
future UI diagnostics panel when the application has a deliberate place to run
and explain visible-window measurements.

## Reporting rules

Every supported estimate must identify:

- The asset and content identity when available.
- Source codec, dimensions, and rational rate.
- The representation measured, including any size cap.
- Sample count and cache conditions.
- Median and a tail statistic when the sample count supports it.
- The software/backend environment.
- Whether the result is a measured duration, an extrapolated estimate, or a
  pass/fail interpretation.

An estimate must not silently run expensive whole-asset work during ordinary
application startup. Expensive diagnostics require an explicit user action.
Cheap, previously measured, or safely cached estimates may later be displayed
in the UI if their provenance and age remain visible.

## Consequences

- Reusable benchmark code gains compatibility and testing responsibilities.
- Human output is designed alongside JSON output rather than added as an
  afterthought.
- Findings may use the supported benchmark directly, improving reproducibility.
- UI integration can reuse the same result schema instead of parsing developer
  script output.
- Throwaway microbenchmarks remain cheap to write and delete.
