# SIEVE — Filter Contract

This document specifies the interface every filter implements. It is the
single source of truth referenced by `ARCHITECTURE.md §6`. Every other
load-bearing spec (`PIPELINE_SCHEMA`, `CACHE_KEY_SPEC`, `BACKEND_DISPATCH`,
`PREVIEW_SEMANTICS`, `DETERMINISM_POLICY`) assumes the filter contract as
defined here.

Related ADRs: 004 (Pydantic v2), 011 (Array API + NumPy typing),
016 (CuPy v1 GPU backend), 014 (Zarr v3).

Related visions: `replicate-vision.md` (calibration and scope).

---

## 1. Overview

A filter is a Pydantic model plus one or more backend implementations,
registered by decorator, colocated with a markdown guidance file. The model
is the only declaration of the filter's parameters; every other subsystem
(GUI widgets, CLI flags, YAML schema, cache key, cost model, guidance panel)
derives from it.

Minimal shape:

```python
@register_filter
class GaussianBlur(Filter):
    name: ClassVar[str] = "gaussian_blur"
    version: ClassVar[str] = "1.0.0"

    # Parameters (Pydantic fields)
    sigma: float = Field(1.0, ge=0.0, le=50.0, description="Std. dev. in px")
    kernel_size: int = Field(0, ge=0, description="0 = derived from sigma")

    # Static declarations
    input_specs: ClassVar[tuple[StreamSpec, ...]] = (StreamSpec.image_any,)
    output_specs: ClassVar[tuple[StreamSpec, ...]] = (StreamSpec.image_like_input,)
    output_topology: ClassVar[Topology] = Topology.SHAPE_PRESERVING
    warmup_frames: ClassVar[int] = 0
    is_streaming: ClassVar[bool] = True
    is_deterministic: ClassVar[bool] = True
    storage_dtype: ClassVar[DTypePolicy] = DTypePolicy.MATCH_INPUT
    backends: ClassVar[frozenset[BackendId]] = frozenset({"cpu_numpy", "gpu_cupy"})

    def estimate_cost(self, input_spec: StreamSpec, backend: BackendId) -> CostEstimate: ...
    def process(self, frame: Array, ctx: FilterContext) -> Array: ...
```

Every element above is required. Missing elements cause registration to fail loudly at import time.

Filters may optionally declare a `refinement_widget` for bespoke GUI interaction (see §12).

## 2. Identity and versioning

- `name` — snake_case string, globally unique across the registry. Used in pipeline YAML, cache keys, log records, and filesystem paths. Never change after release; a rename is a new filter.
- `version` — semver string. Any change to the filter's numerical output for the same params must bump at least the patch version. Cache entries key on `(name, version, code_hash)`; a version bump invalidates entries.

Versioning rules:

- Patch: bugfix producing different output on inputs that were previously wrong.
- Minor: new optional parameters with backward-compatible defaults.
- Major: parameter renamed or removed, semantics changed, output shape or topology changed.

The registry rejects two filters sharing a name. It permits multiple versions of the same name only if explicitly opted in (for regression testing); production runs pin one version per name.

## 3. Parameters — the single source of truth

### 3.1 Declaration

Parameters are Pydantic v2 model fields (ADR-004). No other declaration mechanism is permitted. GUI widgets, CLI flags, YAML validation, JSON Schema, cache-key contribution, and cost-model input all read the model.

Every field must carry:

- a type annotation (used by `schema_to_qt.py` to choose a widget class)
- a default value (used when the YAML omits the field)
- validation constraints (`ge`, `le`, `min_length`, `pattern`, and so on)
- a description (rendered as a tooltip and in generated docs)

Recommended: `json_schema_extra` for GUI-only hints (widget preference, slider step, unit label). These never affect execution.

### 3.2 Canonicalization for cache keys

The cache key derivation (see `CACHE_KEY_SPEC.md`) requires a canonical form of the params. The contract guarantees:

- field order follows the model's declaration order
- floats are serialized with `repr()` (round-trip exact)
- optional fields at their default value are included in the canonical form
- sets are sorted; dicts are key-sorted
- fields marked `json_schema_extra={"cache_key": False}` are excluded from the key; use sparingly and only for fields that provably cannot affect output

### 3.3 Validation

Validation runs at:

- pipeline load — YAML is coerced into the model; invalid graphs fail before any frame is decoded
- GUI edit — widget writes are validated on commit; invalid values revert
- runtime never — the executor trusts the model was validated at load

Cross-field validation uses Pydantic `@model_validator(mode="after")`. Validation that depends on replicate calibration (for example, a temporal filter's frequencies versus frame rate) happens at graph-bind time, when the replicate context is known, rather than at model construction.

## 4. Stream specs and I/O typing

### 4.1 StreamSpec

Each filter declares `input_specs` and `output_specs` as tuples of `StreamSpec`. A `StreamSpec` captures:

| Field | Meaning |
| --- | --- |
| axes | Ordered tuple of `AxisRole` — `TIME`, `HEIGHT`, `WIDTH`, `CHANNEL`, `SCALE`, `FREQUENCY`, `BLOCK_Y`, `BLOCK_X`, or user-defined |
| channels | `int`, or `None` for any |
| dtype | One of `uint8`, `uint16`, `float16`, `bfloat16`, `float32`, or a `DTypeSet` |
| value_range | `(min, max)` or `None` (arbitrary) |
| sign | `NONNEGATIVE`, `SIGNED`, or `ANY` |
| role | Semantic tag: `image`, `mask`, `flow`, `energy`, `coords`, `power`, `scalogram` |

`axes` replaces a flat layout string. A conventional image is `(HEIGHT, WIDTH, CHANNEL)`; a video is `(TIME, HEIGHT, WIDTH, CHANNEL)`; a Morlet-style scalogram over blocks is `(TIME, FREQUENCY, BLOCK_Y, BLOCK_X)`. The axis vocabulary is what lets the executor and cache reason about shape-changing operations without each filter reinventing the description.

The sentinel `StreamSpec.image_like_input` in `output_specs` means “same as the Nth input” and is resolved by the executor.

### 4.2 Multi-input filters

`input_specs` is a tuple. Filters that combine multiple upstream streams declare each input separately. Example:

```python
@register_filter
class OpticalFlow(Filter):
    name: ClassVar[str] = "optical_flow"
    version: ClassVar[str] = "1.0.0"

    input_specs: ClassVar[tuple[StreamSpec, ...]] = (
        StreamSpec.image_grayscale,  # frame N
        StreamSpec.image_grayscale,  # frame N-1
    )
    output_specs: ClassVar[tuple[StreamSpec, ...]] = (
        StreamSpec.flow_field,       # signed, 2-channel, same H×W
    )
    output_topology: ClassVar[Topology] = Topology.SHAPE_PRESERVING
    warmup_frames: ClassVar[int] = 1
    ...

    def process(self, frames: tuple[Array, Array], ctx: FilterContext) -> Array:
        current, previous = frames
        ...
```

Pipeline YAML wires each input by node ID and output slot (see `PIPELINE_SCHEMA.md`); the ordering in `input_specs` is significant.

### 4.3 Static graph validation

The executor validates the DAG before execution: every edge's producer `output_specs[i]` must be a subtype of the consumer's `input_specs[j]`. Mismatches produce a targeted error identifying the offending edge.

### 4.4 Array typing in code

Per ADR-011:

- Filter kernels are Array API-compatible (accept NumPy or CuPy arrays).
- Type annotations use `numpy.typing.NDArray[...]` for the CPU path.
- Selective `jaxtyping` annotations are used on the `process` signature where shape discipline matters.

## 5. Output topology

`output_topology: ClassVar[Topology]` declares the structural relationship between input and output shape.

| Value | Meaning |
| --- | --- |
| `SHAPE_PRESERVING` | Output has the same axes as input, possibly with a different channels count. Blur, HSV convert, threshold, optical flow. |
| `SPATIAL_REDUCTION` | Output collapses or blocks spatial axes. Downsample, block-count, ROI. `HEIGHT` and `WIDTH` may become `BLOCK_Y` and `BLOCK_X` or disappear. |
| `TEMPORAL_REDUCTION` | Output collapses or windows the time axis. Temporal integration into a single-frame MEI, decimation. |
| `AXIS_INTRODUCING` | Output adds a new axis not present in input. Morlet bank (`SCALE`/`FREQUENCY`), multi-scale pyramid, filter bank. |
| `AXIS_ELIMINATING` | Output drops an axis. Scalogram-to-power-per-time, connected-component reduction to counts. |

This is what `is_streaming` alone cannot express. `is_streaming` is a scheduling property (can this filter be pipelined frame-by-frame?); `output_topology` is a type property (what shape family does its output belong to?). A shape-preserving filter is usually streaming but need not be; an axis-introducing filter usually isn't but might be (if the new axis is fixed-size and independent per frame).

The executor uses `output_topology` for:

- static shape inference through the DAG before execution
- deciding materialization boundaries (topology changes often warrant materialization even when both sides are streaming)
- rejecting nonsensical downstream connections (for example, a spatial-blur filter cannot consume a scalar time series)

## 6. Dtype policy

Per architecture §20 (resolved policy):

### 6.1 Storage dtype

Each filter declares `storage_dtype: DTypePolicy`. Options:

| Value | Meaning |
| --- | --- |
| `MATCH_INPUT` | Output uses the input dtype. Default. |
| `FLOAT16` | Output stored as `float16`. Safe for most spatial ops. |
| `BFLOAT16` | Output stored as `bfloat16`. Preferred for wide-range values (flow magnitudes, integration accumulators near zero). |
| `FLOAT32` | Output stored as `float32`. Required for coefficient-quantization-sensitive filters (Morlet banks, 3D wavelets near band edges). |
| `UINT8` / `UINT16` | Integer storage for masks and quantized outputs. |

### 6.2 Accumulator dtype

Temporal state (IIR history, MEI/MHI buffers, integration accumulators, coefficient buffers) is always `float32`, regardless of `storage_dtype`. Casts happen at read/write boundaries.

### 6.3 Edges

Decoded input arrives in its native dtype (typically `uint8`). Terminal outputs are written in the dtype declared by the pipeline's output node. Intermediate dtype policy applies to non-terminal nodes only.

## 7. Warmup declaration

`warmup_frames: ClassVar[int]` — number of frames of upstream input the filter must consume before its output is trustworthy. `0` for stateless filters.

Semantics (see `PREVIEW_SEMANTICS.md`):

- The executor composes warmup along temporal paths in the DAG.
- Preview extraction pads the user's clip by the composed warmup on each temporal path leading to the visible node; padded frames are computed but not displayed.
- Filters do not know whether they run in preview or full-video mode. Warmup is a filter property; composition is the executor's job.

For filters where warmup depends on parameters:

```python
def warmup_frames_for(self) -> int:
    return int(math.ceil(5.0 / self.alpha))
```

The class variable is a conservative upper bound for static analysis; `warmup_frames_for` refines it at runtime.

## 8. Streaming capability

`is_streaming: ClassVar[bool]` — whether the filter can process frame-by-frame with bounded state.

- `True` — implements `process(frame, ctx)` for a single frame (or a tuple of frames for multi-input filters). The executor pipelines consecutive streaming filters and avoids materializing intermediates between them.
- `False` — implements `process_all(stream, ctx)` and receives a lazy frame iterator (or a windowed view for filters that need lookahead). Non-streaming filters force a materialization boundary before and after them.

A filter that is streaming for some parameter regimes and not others declares `is_streaming = False` or splits into two registered filters. No runtime toggling.

## 9. Determinism declaration

`is_deterministic: ClassVar[bool]` — whether the filter produces bit-identical output under `DETERMINISM_POLICY.md`.

- Deterministic filters participate in the CI byte-comparison test.
- Non-deterministic filters are legal; their cache entries are keyed by the run's seed (recorded in the pipeline artifact), and the bench layer flags them.

Per-backend determinism, when it varies:

```python
determinism_by_backend: ClassVar[Mapping[BackendId, bool]] = {
    "cpu_numpy": True,
    "gpu_cupy": False,  # atomic reductions
}
```

Overrides `is_deterministic` per backend when present.

## 10. Cost estimation

```python
def estimate_cost(
    self,
    input_spec: ResolvedStreamSpec,
    backend: BackendId,
) -> CostEstimate: ...
```

Returns:

```python
@dataclass(frozen=True)
class CostEstimate:
    wall_time_per_frame_s: float
    peak_resident_bytes: int
    peak_gpu_bytes: int
    confidence: Literal["measured", "modeled", "guess"]
```

Requirements:

- Rough is fine; about $2\times$ error is tolerated. What matters is that pointless-on-GPU filters return higher GPU cost than CPU cost.
- It must not run the filter. Closed-form or cached prior only.
- It may be refined at runtime. After $N$ frames of a real run, the bench layer replaces the estimate with measurement in the results table.

## 11. Backend registry and dispatch

`backends: ClassVar[frozenset[BackendId]]` declares which backends the filter implements. Valid IDs for v1: `"cpu_numpy"`, `"gpu_cupy"` (ADR-016).

Preferred: an Array API-compatible single implementation:

```python
def process(self, frame: Array, ctx: FilterContext) -> Array:
    xp = array_namespace(frame)
    return xp.multiply(frame, self.gain)
```

Fallback: dispatch on `ctx.backend` internally. The filter never selects its own backend; `BACKEND_DISPATCH.md` policy picks.

## 12. Colocated guidance and refinement

### 12.1 Guidance markdown

For a filter at `sieve/core/filters/<category>/<name>.py`, a markdown file `<name>.md` sits beside it. It is loaded by the guidance panel verbatim (see `GUIDANCE_FORMAT.md`). Content changes are documentation changes.

The registry validates that the sidecar exists at registration time. Empty files are rejected.

### 12.2 Refinement widget (optional)

The auto-generated widget from a filter's Pydantic schema covers the common case: spin boxes, sliders, dropdowns. Some filters need bespoke interaction — an HSV color picker on the current frame, a draggable frequency/value band overlay, or a click-to-focus overlay.

Filters may declare an optional refinement widget:

```python
refinement_widget: ClassVar[str | None] = "sieve.gui.widgets.hsv_clicker:HSVClicker"
```

The value is an import path resolved at GUI load time. The widget is displayed in the operation-detail panel when the filter is active, in addition to the auto-generated parameter widgets. The widget receives the filter's Pydantic model and mutates it directly; changes propagate through the same validation path as auto-generated widgets.

Filters with `refinement_widget = None` (the default) use only the auto-generated widgets. This preserves the “no GUI changes when adding a filter” promise for the 80% case and provides a clean opt-out for the 20% case (linked scalograms, density rasters, calibration drawing).

The core package must not import the widget module; the reference is a string. This preserves the layer boundary from architecture §3.

## 13. Registration

Registration is decorator-driven. Adding a file with a decorated class in `sieve/core/filters/` is sufficient — no registry list to edit.

```python
from sieve.core.contract import Filter, register_filter

@register_filter
class MyFilter(Filter):
    ...
```

The decorator:

- validates that the class satisfies the contract (all required `ClassVar`s present, sidecar `.md` exists, `estimate_cost` and `process` defined, `output_topology` set)
- registers under `MyFilter.name`
- raises `FilterRegistrationError` on any failure; import-time failure is intentional — a broken filter must not silently disappear

Discovery happens by explicit imports in `sieve/core/filters/__init__.py`. No dynamic filesystem scanning.

## 14. FilterContext

Passed to `process` / `process_all`:

```python
@dataclass(frozen=True)
class FilterContext:
    backend: BackendId
    frame_index: int              # 0-based, absolute in the replicate's stream
    is_warmup: bool               # True while producing frames the executor will discard
    run_seed: int | None          # set for non-deterministic filters
    logger: structlog.BoundLogger # per-node logger with node_id bound
    replicate: ReplicateContext   # calibration + geometry, see §14.1
```

### 14.1 Replicate context

Filters that consume calibrated inputs read from `ctx.replicate` rather than from filter parameters:

```python
@dataclass(frozen=True)
class ReplicateContext:
    replicate_id: str
    frame_rate_hz: float
    pixels_per_mm: float | None
    pixels_per_body_length: float | None
    source_geometry: tuple[int, int, int, int]  # x, y, w, h in source
    # additional fields per replicate-vision.md
```

This is what keeps a temporal filter's frequencies in Hz rather than in frames, and a spatial filter's scale in mm rather than in pixels, without each filter storing calibration as a parameter.

Filters must not read from disk, spawn threads, or mutate global state via the context.

## 15. What is not in the contract

Explicitly excluded:

- GUI widget layout. Derived from the Pydantic schema by `gui/widgets/schema_to_qt.py`, plus optional `refinement_widget`.
- CLI flag names. Derived from field names.
- Storage layout on disk. `io/zarr_store.py` decides chunking, sharding, compression (ADR-014).
- Cache implementation. The filter contributes to the cache key (§3.2); it does not know whether a cache exists.
- Scheduling. The executor decides when to run the filter, on which worker, with what parallelism.
- Replicate geometry. The filter reads calibration from `ctx.replicate`; it does not know or care how the replicate was drawn.

## 16. Testing requirements

Every filter ships with:

- a property-based test (Hypothesis, ADR-008): for any valid params, output shape matches `output_specs` and `output_topology`, output dtype matches storage policy, and (if `is_deterministic`) two runs on the same input produce byte-identical output
- a golden-output test on one canonical fixture, byte-compared with documented tolerance for GPU float ops
- a cost-estimate sanity test — the estimate is within an order of magnitude of measured wall time on a small canonical input

The generic property test harness lives in `tests/contract/`. Filter-specific tests live beside the filter module.

## 17. Open questions deferred

Non-load-bearing decisions:

- whether `warmup_frames_for` becomes the sole API and the `ClassVar` is dropped
- whether `DTypePolicy` and `Topology` enums should be concrete enums or more flexible types
- whether `AxisRole` is a closed enum or extensible per-filter
- whether `StreamSpec` should carry sample-rate metadata directly; currently calibration (including frame rate) lives on the replicate context rather than on the stream. Revisit if a filter needs to output a stream whose effective sample rate differs from its input's (temporal decimation is the obvious case)
- whether `refinement_widget` gets a richer contract (signals for undo integration, preview redraw triggers) or stays as a raw widget hook