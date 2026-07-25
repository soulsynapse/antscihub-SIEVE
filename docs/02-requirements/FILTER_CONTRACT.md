# SIEVE — Filter Contract

This document specifies the interface every filter implements. It is the
single source of truth referenced by `ARCHITECTURE.md §6` and §20. Every
other load-bearing spec (`PIPELINE_SCHEMA`, `CACHE_KEY_SPEC`,
`BACKEND_DISPATCH`, `PREVIEW_SEMANTICS`, `DETERMINISM_POLICY`) assumes the
filter contract as defined here.

Related ADRs: 004 (Pydantic v2), 011 (Array API + NumPy typing),
016 (CuPy v1 GPU backend), 014 (Zarr v3).

---

## 1. Overview

A filter is a Pydantic model plus one or more backend implementations,
registered by decorator, colocated with a markdown guidance file. The model
is the *only* declaration of the filter's parameters; every other subsystem
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
    warmup_frames: ClassVar[int] = 0
    is_streaming: ClassVar[bool] = True
    is_deterministic: ClassVar[bool] = True
    storage_dtype: ClassVar[DTypePolicy] = DTypePolicy.MATCH_INPUT
    backends: ClassVar[frozenset[BackendId]] = frozenset({"cpu_numpy", "gpu_cupy"})

    def estimate_cost(self, input_spec: StreamSpec, backend: BackendId) -> CostEstimate: ...
    def process(self, frame: Array, ctx: FilterContext) -> Array: ...
Every element above is required. Missing elements cause registration to fail loudly at import time.

2. Identity and versioning
name — snake_case string, globally unique across the registry. Used in pipeline YAML, cache keys, log records, and filesystem paths. Never change after release; a rename is a new filter.
version — semver string. Any change to the filter's numerical output for the same params must bump at least the patch version. Cache entries key on (name, version, code_hash); a version bump invalidates entries.
Patch: bugfix producing different output on inputs that were previously wrong.
Minor: new optional parameters with backward-compatible defaults.
Major: parameter renamed / removed, semantics changed, output shape or dtype policy changed.
The registry rejects two filters sharing a name. It permits multiple versions of the same name only if explicitly opted in (for regression testing); production runs pin one version per name.

3. Parameters — the single source of truth
3.1 Declaration
Parameters are Pydantic v2 model fields (ADR-004). No other declaration mechanism is permitted. GUI widgets, CLI flags, YAML validation, JSON Schema, cache-key contribution, and cost-model input all read the model.

Every field must carry:

A type annotation (used by schema_to_qt.py to choose widget class)
A default value (used when the YAML omits the field)
Validation constraints (ge, le, min_length, pattern, ...)
A description (rendered as tooltip and in generated docs)
Recommended: json_schema_extra for GUI-only hints (widget preference, slider step, unit label). These never affect execution.

3.2 Canonicalization for cache keys
The cache key derivation (see CACHE_KEY_SPEC.md) requires a canonical form of the params. The contract guarantees:

Field order is the model's declaration order.
Floats are serialized with repr() (round-trip exact).
Optional fields at their default value are included in the canonical form (so adding a new field with a default does not silently reuse old cache entries — the version bump handles it).
Sets are sorted; dicts are key-sorted.
Fields marked json_schema_extra={"cache_key": False} are excluded from the key. Use sparingly and only for fields that provably cannot affect output (e.g., a display-only label).

3.3 Validation
Validation runs at:

Pipeline load — YAML is coerced into the model; invalid graphs fail before any frame is decoded.
GUI edit — widget writes are validated on commit; invalid values revert.
Runtime never — the executor trusts the model was validated at load.
Custom cross-field validation uses Pydantic @model_validator(mode="after").

4. Stream specs and I/O typing
4.1 StreamSpec
Each filter declares input_specs and output_specs as tuples of StreamSpec. A StreamSpec captures:

Field	Meaning
ndim	2 (single-channel image), 3 (multi-channel), 4 (temporal stack)
channels	int, or None for any
dtype	one of uint8, uint16, float16, bfloat16, float32, or a DTypeSet
value_range	(min, max) or None (arbitrary)
layout	"HW", "HWC", "THWC", ...
role	semantic tag: "image", "mask", "flow", "energy", "coords"
Sentinel StreamSpec.image_like_input in output_specs means "same as the Nth input" and is resolved by the executor.

4.2 Static graph validation
The executor validates the DAG before execution: every edge's producer output_specs[i] must be a subtype of the consumer's input_specs[j]. Mismatches produce a targeted error identifying the offending edge. This is the mechanism §17 relies on to reject bad graphs at load time.

4.3 Array typing in code
Per ADR-011:

Filter kernels are Array API-compatible (accept NumPy or CuPy arrays).
Type annotations use numpy.typing.NDArray[...] for the CPU path.
Selective jaxtyping annotations (Float32[Array, "H W C"]) on the process signature where shape discipline matters.
5. Dtype policy
Per architecture §20 (resolved policy):

5.1 Storage dtype
Each filter declares storage_dtype: DTypePolicy. Options:

Value	Meaning
MATCH_INPUT	Output uses input's dtype. Default.
FLOAT16	Output stored as float16 (space-saving; safe for most spatial ops).
BFLOAT16	Output stored as bfloat16. Preferred when values span wide range (flow magnitudes, integration accumulators near zero).
FLOAT32	Output stored as float32 (default for filters with coefficient-quantization sensitivity: Morlet banks, 3D wavelets near band edges).
UINT8 / UINT16	Integer storage for masks and quantized outputs.
5.2 Accumulator dtype
Temporal state (IIR history, MEI/MHI buffers, integration accumulators, wavelet coefficient buffers) is always float32, regardless of storage_dtype. Casts happen at read/write boundaries.

5.3 Edges
Decoded input arrives in its native dtype (typically uint8 from a video decoder). Terminal outputs are written in the dtype declared by the pipeline's output node. Intermediate dtype policy applies only to non-terminal nodes.

6. Warmup declaration
warmup_frames: ClassVar[int] — number of frames of upstream input the filter must consume before its output is trustworthy. 0 for stateless filters.

Semantics (used by PREVIEW_SEMANTICS.md):

The executor composes warmup along temporal paths in the DAG. If filter A declares 30 and downstream filter B declares 15, the combined warmup on that path is 45.
Preview extraction pads the user's clip by the composed warmup on each temporal path leading to the visible node; padded frames are computed but not displayed.
Filters do not know whether they are running in preview or full-video mode. Warmup is a filter property; composition is the executor's job.
For filters where warmup depends on parameters (e.g., an IIR filter's warmup grows with time constant), implement:

python

def warmup_frames_for(self) -> int:
    return int(math.ceil(5.0 / self.alpha))
The class-var warmup_frames becomes a conservative upper bound used for static graph analysis; warmup_frames_for refines it at runtime.

7. Streaming capability
is_streaming: ClassVar[bool] — whether the filter can process frame-by-frame with bounded state.

True — implements process(frame, ctx) for a single frame. The executor pipelines consecutive streaming filters and avoids materializing intermediates between them.
False — implements process_all(stream, ctx) and receives a lazy frame iterator (or a windowed view for filters that need lookahead). Non-streaming filters force a materialization boundary before and after them.
A filter that is streaming for some parameter regimes and not others (e.g., a spatial filter with an optional global normalization) declares is_streaming = False and dispatches internally, or splits into two registered filters. The contract does not permit runtime toggling.

8. Determinism declaration
is_deterministic: ClassVar[bool] — whether the filter produces bit-identical output for identical inputs under DETERMINISM_POLICY.md's enforcement (fixed thread counts, pinned decoder, optional deterministic GPU mode).

Deterministic filters may participate in the CI byte-comparison test.
Non-deterministic filters (some GPU reductions, some optical-flow variants) are legal. The cache still stores their outputs (keyed by the run's seed, which is recorded in the pipeline artifact), and the bench layer flags them in the results table.
Filters that are deterministic on CPU but not GPU declare is_deterministic = True and rely on the deterministic-GPU-mode flag; the backend registry may narrow the claim per-backend if needed:

python

determinism_by_backend: ClassVar[Mapping[BackendId, bool]] = {
    "cpu_numpy": True,
    "gpu_cupy": False,  # atomic reductions
}
When present, this overrides is_deterministic per backend.

9. Cost estimation
python

def estimate_cost(
    self,
    input_spec: ResolvedStreamSpec,
    backend: BackendId,
) -> CostEstimate: ...
Returns:

python

@dataclass(frozen=True)
class CostEstimate:
    wall_time_per_frame_s: float   # predicted seconds per frame
    peak_resident_bytes: int       # peak host RAM
    peak_gpu_bytes: int            # 0 on CPU backend
    confidence: Literal["measured", "modeled", "guess"]
Requirements:

Rough is fine. The HUD and guidance layer tolerate ~2× error. What matters is that pointless-on-GPU filters (frame decimation, ROI crop) return a higher GPU cost than CPU cost so the dispatcher's cost-model tie-break routes them to CPU.
Must not run the filter. Estimates come from a closed-form model or a cached prior measurement, not a trial execution.
May be refined at runtime. After the first N frames of a real run, the bench layer replaces the estimate with a measured value in the results table. This does not change the filter's declared method.
10. Backend registry and dispatch
backends: ClassVar[frozenset[BackendId]] declares which backends the filter implements. Valid IDs for v1: "cpu_numpy", "gpu_cupy" (per ADR-016 — no speculative Torch backend).

Implementation dispatch:

python

def process(self, frame: Array, ctx: FilterContext) -> Array:
    if ctx.backend == "gpu_cupy":
        return self._process_cupy(frame, ctx)
    return self._process_numpy(frame, ctx)
Or, preferred, an Array API-compatible single implementation (ADR-011) that works on both:

python

def process(self, frame: Array, ctx: FilterContext) -> Array:
    xp = array_namespace(frame)
    return xp.multiply(frame, self.gain)
The filter never selects its own backend. BACKEND_DISPATCH.md policy (user preference × capability × cost estimate) picks; ctx.backend communicates the choice.

11. Colocated guidance
For a filter at sieve/core/filters/<category>/<name>.py, a markdown file <name>.md sits beside it. It is loaded by the guidance panel verbatim (see GUIDANCE_FORMAT.md). Content changes are documentation changes, never code changes.

The registry validates that the sidecar exists at import time and fails registration if it does not. A minimum-viable file is one heading and one sentence; empty files are rejected to prevent accidental omission.

12. Registration
Registration is decorator-driven. Adding a file with a decorated class in sieve/core/filters/ is sufficient — no registry list to edit, no plugin manifest.

python

from sieve.core.contract import Filter, register_filter

@register_filter
class MyFilter(Filter):
    ...
The decorator:

Validates the class satisfies the contract (all required ClassVars present, sidecar .md exists, estimate_cost and process defined).
Registers under MyFilter.name.
Raises FilterRegistrationError on any failure. Import-time failure is intentional — a broken filter must not silently disappear.
Discovery happens by importing sieve.core.filters (which imports each category subpackage's __init__.py, which imports each filter module). No dynamic filesystem scanning; explicit imports keep static analyzers and IDEs honest.

13. FilterContext
Passed to process / process_all:

python

@dataclass(frozen=True)
class FilterContext:
    backend: BackendId
    frame_index: int              # 0-based, absolute in the source stream
    is_warmup: bool               # True while producing frames the executor will discard
    run_seed: int | None          # set for non-deterministic filters; None otherwise
    logger: structlog.BoundLogger # per-node logger with node_id bound
Filters use ctx.is_warmup only for optimizations (skipping expensive optional output). They must produce numerically-correct state updates during warmup regardless.

Filters must not read from disk, spawn threads, or mutate global state via the context. Any such need is a bug in the filter design.

14. What is not in the contract
Explicitly excluded, to keep the surface small:

GUI widget layout. Derived from the Pydantic schema by gui/widgets/schema_to_qt.py. Filter authors influence it only through json_schema_extra.
CLI flag names. Derived from field names.
Storage layout on disk. io/zarr_store.py decides chunking, sharding, and compression (see ADR-014). The filter declares dtype and shape only.
Cache implementation. The filter contributes to the cache key (§3.2); it does not know whether a cache exists.
Scheduling. The executor decides when to run the filter, on which worker, with what parallelism.
15. Testing requirements
Every filter ships with:

A property-based test (Hypothesis, per ADR-008) asserting: for any valid params, output shape matches output_specs, output dtype matches the declared storage policy, and (if is_deterministic) two runs on the same input produce byte-identical output.
A golden-output test on one canonical fixture, byte-compared with documented tolerance for GPU float ops. This is what the CI determinism check runs against (§12 of architecture).
A cost-estimate sanity test — the estimate for a small canonical input is within an order of magnitude of measured wall time.
The generic property test harness lives in tests/contract/. Filter- specific tests live beside the filter module.

16. Open questions deferred to implementation
These are non-load-bearing and can be decided when the code lands:

Exact StreamSpec subclass hierarchy vs. flat with predicates.
Whether warmup_frames_for becomes the sole API and the ClassVar is dropped.
Concrete DTypePolicy enum vs. accepting numpy.dtype directly.
Whether CostEstimate.confidence levels expand.
None of these change what the contract commits to. They change how the commitment is expressed in Python.


A few notes on choices I made that you may want to push back on:

1. **`determinism_by_backend` as an optional override** — the architecture doc talks about single `is_deterministic` but §9's mention of "some GPU reductions" implies per-backend variance. I made the fine-grained version optional so simple filters stay simple.

2. **`warmup_frames` as ClassVar + `warmup_frames_for` for parameter-dependent cases** — the architecture spec only mentions the static version, but IIR-style filters realistically need it to depend on time constants. Flagged as an "open question" in §16 in case you'd rather commit to one form.

3. **Sidecar `.md` required, empty files rejected** — enforces the "guidance is data" commitment from §17 at registration time rather than letting filters ship without docs.

4. **No Torch backend** — followed ADR-016 strictly. If a filter needs Torch it goes in an isolated worker per that ADR, not through this contract.