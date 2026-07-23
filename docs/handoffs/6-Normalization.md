# 6 — Add per-frame normalization

Reviewed and corrected against rewrite commit `f6af6fe` on
`2026-07-23 16:22:38 -07:00`. The oracle review was folded into this handoff
rather than delivered as a separate review file.

Status: handoff only. Implementation is not authorized until milestone 5 has
been implemented, visibly validated, and accepted, and the rewrite-side
divergence refresh in section 1.1 has been completed.

Rewrite review disposition:

- Milestone 5 is implemented and has automated evidence, but manual acceptance
  remains outstanding. Nothing in this review closes that gate.
- The rewrite's accepted result-memory defaults are 16 GiB for CPU and 6 GiB
  for GPU through `ExecutionResourcePolicy`; milestone 6 must not replace them
  with the oracle's proposed 512 MiB default. Execution is currently CPU-only.
- The current rewrite has no independent scientific result-key type.
  Publication uses `IntensityRequest` equality plus the GUI `_job_token`, even
  though request equality currently also includes execution policy, execution
  target, and batch size. Milestone 6 must introduce or expose a scientific-key
  comparison without treating those execution fields as scientific identity.
- The current `off` identity exists only as
  `IntensityResult.normalization_id == "off"`; it is not captured by
  `IntensityRequest`.
- The current `reduce_rgb_frame(...)` owns conversion, area reduction, and
  block reduction in one function. There is no existing pre-block extension
  hook. Split out only the smallest pure working-frame normalization seam.
- Current asset, window, and grid changes invalidate and cancel without
  automatic recomputation. Automatic replacement after a committed
  normalization change is new milestone-6 behavior, not accepted milestone-5
  behavior.

This milestone adds one upstream scientific choice to the accepted Isolate
intensity path:

```text
normalization = off | per_frame_zscore
```

It deliberately does not add change energy, value filtering, CLAHE, motion,
spectral processing, or detection. The purpose is to settle normalization
identity, numerical behavior, invalidation, and presentation before a temporal
channel depends on it.

The required pipeline is:

```text
native-resolution decoded rgb24
    -> fixed milestone-5 RGB intensity conversion
    -> accepted area downsample to working resolution
    -> selected per-frame normalization
    -> accepted block reduction
    -> immutable normalized-intensity result
    -> existing intensity panel with an honest fixed presentation mapping
```

Normalization operates on scientific working-resolution pixels. It is not a
contrast adjustment applied to the panel raster.

## 1. Precedence and implementation gate

This handoff follows the accepted implementations of:

- `1-Build-the-player.md`.
- `2-Media-service-handoff.md`.
- `3-Working-window.md`.
- `4-Working-grid.md`.
- `5-First-channel.md`.

The user has visibly accepted milestone 4; there is no remaining milestone-4
gate. Milestone 5 is implemented at `f6af6fe`, with 135 automated tests
reported passing, but its visible/manual acceptance remains the only feature
prerequisite for this handoff.

Milestone 5 acceptance is a hard prerequisite. Its concrete rewrite seams are
`IntensityRequest`, `IntensityResult`, `ChannelStageOutcome`,
`compute_intensity(...)`, `reduce_rgb_frame(...)`, `IntensityWorker`,
`IsolateTab`, and `IntensityRaster`. Extend those seams rather than restoring
illustrative oracle types or adding parallel owners.

In particular, milestone 6 must reuse rather than replace:

- The accepted scientific request snapshot.
- The worker-owned request-local source lifecycle.
- The exact source outcome and channel-stage outcome composition.
- The result-resource policy and pre-source admission boundary.
- The one-active-worker/one-newest-pending-request supersession handshake.
- The accepted intensity panel and its single player clock.
- The milestone-5 post-decoder RGB intensity representation,
  `sieve.channel.rgb601_intensity.v1`.

Completing this document does not authorize starting milestone 6. Completing
milestone 6 does not authorize starting change energy.

### 1.1 Completed rewrite-side divergence refresh

This review updates `.isolate-state-divergence.md` with the current milestone-5
facts:

- The concrete headless intensity request, result, settings, and outcome types.
- The exact order of RGB conversion, area downsampling, and block reduction.
- The scientific value dtype and interval before block reduction.
- Where the current normalization identity is stored.
- The absence of an independent scientific result key, the current
  request-equality publication check, and every upstream event that invalidates
  it.
- The current result-memory estimate and resource-policy input.
- The GUI owner of the scientific settings, current result, active worker,
  cancellation object, publication token, and pending replacement.
- How a compute request is started, superseded, closed, and published.
- The panel's scientific legend, presentation mapping, cursor, hover, and seek
  seams.
- The milestone-5 automated and manual acceptance evidence.
- Any implementation detail that conflicts with this handoff's fixed
  population-z-score, degenerate-frame, or publication rules.

The divergence entry reports actual code and tests rather than commit subjects
or planned class names. Implementation still requires milestone-5 manual
acceptance and must adapt this handoff to its smallest accepted seam; it must
not introduce a parallel normalization pipeline, result owner, worker, or
panel.

## 2. Outcome

At completion:

1. Isolate exposes one normalization selector with exactly **Off** and
   **Per-frame z-score**.
2. A headless caller can apply either mode using the same request and
   computation path as the GUI.
3. Normalization occurs after accepted area downsampling and before block
   reduction.
4. Z-score statistics are computed independently for every frame over all
   `work_width * work_height` working-resolution pixels after requiring the
   complete frame to be finite.
5. The result records the exact normalization specification and a per-frame
   degenerate flag.
6. A committed normalization change immediately invalidates the old result and,
   when a result or job already exists, supersedes it with a computation of the
   current selected window.
7. The intensity panel labels scientific units and its fixed
   presentation-only mapping for both modes.
8. The milestone-5 `off` result remains numerically and behaviorally unchanged.
9. CLAHE remains absent.

## 3. Scope boundary

Implement:

- One small immutable normalization specification.
- `off`.
- Per-frame population z-score.
- One reusable Qt-free pre-block working-frame normalization operation.
- An explicit epsilon in scientific identity.
- Exact degenerate-frame behavior.
- Normalization selection in Isolate.
- Result-key invalidation and safe recomputation on a committed mode change.
- Mode-aware fixed presentation in the existing intensity panel.
- Headless numerical fixtures and offscreen GUI lifecycle tests.

Do not implement:

- CLAHE.
- A generic preprocessing graph or node registry.
- User-editable epsilon.
- Window-wide, video-wide, dataset-wide, running, rolling, or baseline
  normalization.
- Per-block normalization.
- Normalization after block reduction.
- Histogram matching, min/max scaling, percentile scaling, whitening, gamma,
  color correction, background subtraction, registration, masking, or
  denoising.
- Change energy, `J_tt`, frame pairing, temporal context, or another channel.
- Value bands, selected blocks, counts, overlays, Morlet transforms, or
  detection.
- Persistence in a sidecar, `QSettings`, project file, cache, or artifact.
- Whole-asset execution, recipes, a CLI, or a Resources UI.
- Reuse of display-preview pixels.

Do not add CLAHE as a disabled or hidden choice. It has known per-replicate
boundary and tile-grid artifacts and requires its own evidence, parameters,
backend identity, and acceptance contract.

## 4. Required distinctions

Keep these concepts separate:

- Normalization mode from presentation contrast.
- A scientific z-score from the oracle's historical `128 ± 32` display-like
  encoding.
- Per-frame statistics from statistics fitted over the selected window.
- Retaining a mode selection across assets from sharing fitted statistics
  across assets.
- A constant/near-constant frame from a failed or missing frame.
- A degenerate normalized frame from invalid scientific coverage.
- Normalization identity from GUI publication tokens.
- Scientific invalidation from cursor or panel repaint.
- Recomputing a current window from persisting a computed result.

The normalized scientific z-score is dimensionless, centered at zero, and has
population standard deviation one for a nondegenerate frame within numerical
tolerance. Do not store it as `128 + 32*z`.

## 5. Normalization specification

Use a Qt-independent immutable value equivalent to:

```text
mode: off | per_frame_zscore
epsilon: float
implementation_id: string
```

For this milestone:

```text
off epsilon: not applicable
per_frame_zscore epsilon: 1e-6
```

The epsilon is fixed in the GUI but explicit in the scientific request and
result. Changing it later changes scientific identity and requires a new
implementation id or version.

Stable ids should distinguish at least:

```text
sieve.normalization.off.v1
sieve.normalization.per_frame_population_zscore.v1
```

Equivalent names are acceptable if their meaning is equally explicit.

### 5.1 Ownership and session behavior

The normalization selection is a plain Qt-independent scientific setting owned
by the same Isolate GUI owner that captures the milestone-5 computation
request. Do not add it to the display-media lifecycle merely because
`IsolateSession` owns playback.

Session behavior is:

- Application/Isolate startup begins at `off`.
- The selected mode remains session-local.
- The requested mode survives active-asset switches.
- Each asset and each frame computes fresh statistics; no fitted mean,
  variance, histogram, or other state survives a frame or asset switch.
- Application restart returns to `off`.
- No sidecar or `QSettings` entry is written.

Retaining the mode is only retaining intent. It does not share normalization
state between assets.

## 6. Fixed scientific order

For each delivered source frame:

```text
decoded rgb24
    -> I_raw at native source resolution using milestone-5 conversion
    -> I_work at accepted working dimensions using milestone-5 area reduction
    -> I_normalized using this handoff
    -> block means using the accepted resolved grid
```

This order is scientific identity.

Do not:

- Normalize RGB channels independently.
- Normalize native pixels and then area-downsample them.
- Block-reduce and then normalize the block vector.
- Derive normalization statistics from the displayed raster.
- Derive statistics from partial-block weights.
- Change the downsampler or block reducer as part of this milestone.

First require every pixel in `I_work` to be finite. The statistics population is
then exactly all `N = work_height * work_width` pixels for that frame. Do not
filter non-finite pixels and normalize the remainder; any non-finite input fails
the frame. There is no mask in this milestone.

## 7. `off` contract

For mode `off`:

```text
I_normalized = I_work
normalization_degenerate = false
```

Requirements:

- Preserve milestone-5 values exactly, not merely within a relaxed new
  tolerance.
- Preserve `float32` storage and the `[0,1]` interval.
- Do not allocate or traverse a frame solely to implement an identity copy when
  safe aliasing or the existing buffer lifecycle avoids it.
- Do not compute mean or variance.
- Do not change result coverage, outcome, memory admission, cursor behavior, or
  source lifecycle.

The accepted milestone-5 `off` fixtures become regression fixtures for this
milestone.

In the current rewrite, conversion is accumulated in `float64`,
`area_downsample(...)` returns the scientific working plane as finite
`float32` in `[0,1]`, each block mean is accumulated in `float64`, and the
retained block plane is immutable `float32`. Insert normalization between that
`float32` working plane and the existing block-mean loop. Do not change the
conversion or area reducer while creating the seam.

## 8. Per-frame population z-score contract

For one working-resolution frame with `N = work_height * work_width` pixels,
the conformance reference evaluates:

```text
mu = sum(I_work) / N
variance = sum((I_work - mu)^2) / N
sigma = sqrt(variance)
```

Use population variance, dividing by `N`, not sample variance dividing by
`N-1`.

If:

```text
sigma < epsilon
```

then:

```text
I_normalized = exact float32 zeros
normalization_degenerate = true
```

Otherwise:

```text
I_normalized = (I_work - mu) / sigma
normalization_degenerate = false
```

Requirements:

- Accumulate the conformance reference in `float64`.
- Store normalized working pixels and block values as `float32`.
- Require finite input and finite `mu`, variance, sigma, and output.
- Treat a small negative variance caused solely by floating-point roundoff as
  zero only under a pinned, tested numerical rule. A materially negative or
  non-finite variance is a computation failure.
- Do not clamp or quantize z-scores.
- Do not add an offset or scale such as `128 ± 32`.
- Do not replace a non-finite computation with a degenerate zero frame.
- A one-pixel working frame is valid and necessarily degenerate.

An implementation may use a numerically stable one-pass or backend statistics
routine only if it conforms to the independent fixtures and records enough
implementation/backend provenance to reproduce the accepted tolerance.

### 8.1 Degenerate frames are valid data

A degenerate frame:

- Was successfully decoded.
- Passed the accepted RGB conversion and working-resolution reduction.
- Was scientifically processed.
- Produces a valid all-zero block plane.
- Remains part of processed coverage.
- Is not truncation, cancellation, failure, missing data, quiet behavior, or a
  negative detection.

The result must preserve one degenerate flag per processed frame. Use a compact
immutable representation with an exact retained-byte size, for example one
byte per frame containing only `0` or `1`. Do not infer degeneracy later from
the reduced block plane; block reduction loses the evidence needed to do that
reliably.

## 9. Block result and units

Block reduction remains the milestone-5 owned-pixel mean:

```text
value[t,r,c] = mean(
    I_normalized_t[y0:y1, x0:x1]
)
```

For `off`:

```text
channel id: sieve.channel.rgb601_intensity.v1
scientific quantity: post-decoder RGB intensity
units: normalized RGB-code intensity fraction
nominal interval: [0,1]
```

For `per_frame_zscore`:

```text
scientific quantity: per-frame standardized post-decoder intensity
units: frame population standard deviations
nominal interval: unbounded
```

The weighted mean of all z-score block values, weighted by their real owned
pixel counts, should reconstruct the working frame's near-zero mean within the
declared floating tolerance. Unweighted averaging of partial edge cells is not
an equivalent check.

Do not multiply block values by partial-cell weights. The weights remain
separate geometry for later spatial counts and occupancy.

## 10. Request, result, and scientific identity

Extend the accepted milestone-5 `IntensityRequest` with the immutable
normalization specification. Do not add a second request type merely for
normalization. Remove the result-only `normalization_id = "off"` shortcut once
the result can retain the captured specification without duplicating
conflicting identity.

The rewrite does not currently have a separate scientific result key:
`IsolateTab._intensity_finished(...)` publishes only when `_job_token` and a
freshly captured `IntensityRequest` equality both match. Because that request
also contains resource policy, execution target, and batch size, raw request
equality is not yet the scientific key described here.

Add the smallest Qt-free scientific-key value or property shared by headless
results and GUI publication. It must distinguish:

```text
asset recorded/content-verification identity
absolute requested frame span
source plane and RGB conversion identity
working dimensions/downsample identity
resolved grid identity
normalization mode
normalization epsilon when applicable
normalization implementation identity
channel implementation identity
```

The following remain outside scientific identity:

```text
GUI job token
worker object
cancellation object
execution batch size, if conformance proves it result-neutral
execution resource policy and memory limits
panel dimensions
panel color map
cursor position
tab selection
grid overlay visibility
```

Extend the immutable result with:

```text
normalization specification
normalization implementation/backend provenance
degenerate flags aligned one-to-one with processed absolute frames
scientific units
```

The result continues to retain the exact milestone-5 source outcome,
channel-stage outcome, processed span, geometry, conversion provenance, values,
and resource-policy evidence.

Do not label a z-scored result simply `intensity [0,1]`. Use
`sieve.channel.rgb601_intensity.v1` consistently and do not imply that its
weighted values were delivered directly by the source.

The panel's presentation mapping id, palette, fixed display interval, and
clipping rule are view state, not fields in the headless scientific result.
Changing presentation state must not alter result equality, scientific
identity, admission, or computation. Changing execution policy or batch size
may alter scheduling/admission and request equality, but must not alter the
scientific key or accepted values.

### 10.1 Forward compatibility

The required pure normalizer accepts one working-resolution frame and returns
normalized pixels plus degeneracy evidence before block reduction. It must not
depend on `IntensityPanel`, block geometry, the final result allocation, or the
requested output span.

This lets a later temporal channel normalize a lookback frame such as `a-1`
with the same specification without falsely adding that context frame to
requested output coverage. Milestone 6 does not decode or compute temporal
context itself.

Future absolute value bands must be keyed by compatible scientific identity and
units, including channel, normalization, grid, and implementation identity. A
numeric band must not silently survive `off <-> per_frame_zscore`. Do not add
value-band state or controls in this milestone.

## 11. Resource admission and bounded execution

Normalization does not justify opening scientific media before admission.

Update the exact retained-result estimate to include every newly retained byte.
For the recommended one-byte-per-frame degenerate representation:

```text
T = stop_frame - start_frame
value_bytes = T * rows * columns * 4
degenerate_bytes = T
result_bytes = value_bytes + degenerate_bytes
```

Reuse the accepted Qt-free policy:

```text
ExecutionResourcePolicy
    cpu_result_memory_bytes = 17_179_869_184  # 16 GiB default
    gpu_result_memory_bytes = 6_442_450_944    # 6 GiB default
```

The selected target's limit is explicitly overridable by a headless caller,
belongs to execution policy rather than scientific identity, and is retained
through the existing request/provenance seam. The current intensity executor
accepts CPU only; the GPU budget remains a product-policy value and does not
imply a GPU implementation.

The policy budgets declared retained scientific payload bytes: primary values
and aligned fixed-width validity/degeneracy payloads. Compose their checked
byte estimates rather than letting each channel reinterpret the policy.
Language/runtime object overhead, tuple metadata, backend workspaces, decoder
memory, panel textures, and allocator behavior are not claimed to be exactly
counted by this portable admission value. Neither accepted budget claims a
matching total peak process-memory bound; peak live memory remains a separate
bounded or measured property.

Requirements:

- Use overflow-safe integer arithmetic.
- Reject over-budget work before `open_working_window(...)`.
- Admit exactly-at-budget work.
- Report requested and allowed bytes.
- Keep decoded RGB, raw intensity, working intensity, normalized intensity,
  reduced block, retained result, and panel copies within the accepted
  deterministic or measured peak-memory bound.
- Reuse a working buffer when safe, but never mutate immutable source bytes or
  already-published results.
- Cancellation checks and source closure remain those of the accepted
  milestone-5 computation.

Changing normalization must not permit two scientific source owners to overlap.

## 12. GUI control and recomputation

Add one compact selector near the existing intensity compute/status controls:

```text
Normalize: Off | Per-frame z-score
```

The control tooltip or nearby help must state:

- Normalization is applied independently to every scientific
  working-resolution frame.
- Z-score changes the channel's units and can change temporal amplitude.
- It is not a display-only contrast control.

Do not offer CLAHE.

### 12.1 Committed selection behavior

A mode change is committed when the selector changes; there is no Apply button.

If Isolate has never computed intensity for the current ready input:

- Capture the new setting.
- Do not silently launch the first scientific job.
- Leave **Compute intensity** as the explicit first action.

If a complete current result or an active/pending intensity job exists:

1. Capture one new immutable request using the current asset, window, grid, and
   committed normalization.
2. Immediately detach or visibly invalidate the old result.
3. Supersede the old job through the accepted worker handshake.
4. Keep only the newest pending request.
5. Start it only after verified exit of the old source-owning worker.
6. Publish only if both the GUI token and the newly explicit complete
   scientific result key still match. Do not use raw `IntensityRequest`
   equality as a substitute once execution-only fields are separated.

Rapid toggling may coalesce obsolete pending requests, but it must never publish
an intermediate mode as current or leave concurrent scientific decoders.

If automatic recomputation is refused by the resource policy or fails, keep the
new setting selected, show the structured failure, and show no old result as
current under the new setting.

### 12.2 Other invalidation

The milestone-5 invalidation set remains. Asset, temporal window, working
dimensions, block intent/resolution, RGB conversion identity, or normalization
changes invalidate the current result immediately.

Cursor motion, player playback, panel resize, tooltip/hover, tab selection,
grid-overlay visibility, and presentation-only color mapping do not invalidate
scientific values.

## 13. Panel presentation

The panel continues to display the stored block values. It must never
per-frame, per-window, or per-result autoscale the scientific array.

Use fixed mode-specific presentation mappings:

### `off`

```text
scientific interval: [0,1]
presentation interval: [0,1]
out-of-range behavior: structured scientific failure
```

This is exactly the accepted milestone-5 mapping.

### `per_frame_zscore`

Use one fixed signed presentation interval:

```text
presentation interval: [-3,3] standard deviations
center: 0
values below -3: presentation-clipped to the low endpoint
values above +3: presentation-clipped to the high endpoint
stored scientific values: unchanged and unbounded
```

Use a diverging presentation with a visually identifiable zero. Record a stable
presentation mapping id. The hover/readout must show the real stored value even
when its color is clipped.

The panel labels:

- Channel id/name.
- Normalization mode.
- Scientific units.
- Fixed presentation interval and clipping behavior.
- Absolute frame/time axis.
- Row-major block mapping.
- Degenerate status for the hovered/current frame.

A degenerate frame should remain visibly representable as exact zero and be
identified in text. Do not use a special color that can be confused with
missing or failed data unless the legend makes the distinction explicit.

## 14. Coverage, outcomes, and errors

Normalization does not create a second source or channel outcome enum.

A frame enters processed channel coverage only after:

```text
RGB validation and conversion
-> area downsampling
-> normalization or accepted off identity
-> block reduction
```

The result continues to compose:

```text
exact WorkingWindowOutcome
channel-stage outcome
processed channel span
per-frame normalization-degenerate evidence
```

Surface errors at the narrowest owner:

- Invalid normalization specification: request admission.
- Geometry/source mismatch: existing channel admission.
- Non-finite input: existing RGB/working-intensity boundary.
- Non-finite statistics or materially invalid variance: normalization stage.
- Non-finite normalized or reduced value: normalization/channel stage.
- Resource refusal: before source construction.
- Source truncation/failure: exact working-window outcome.
- Worker shutdown failure: GUI lifecycle, not scientific degeneracy.

An error must identify the captured asset, requested span, frame when known,
normalization mode, and failed stage. Do not convert failure into zeros or mark
unprocessed frames degenerate.

## 15. Oracle-derived guidance

The oracle currently offers `off`, z-score, and CLAHE and historically encodes
z-score output near `128 ± 32`. That implementation is evidence about useful
behavior and performance, not the rewrite's scientific contract.

Keep rewrite-native contract fixtures separate from current-oracle comparison
fixtures. For a nondegenerate oracle z-score frame, compare after:

```text
rewrite_z = (oracle_value - 128) / 32
```

For `off`, convert any oracle `0..255` comparison into the rewrite's `0..1`
post-decoder RGB-intensity units as applicable. Degenerate frames follow this
handoff's exact-zero plus flag contract rather than inheriting the oracle's
near-degenerate branch.

Carry these unit differences into milestone 7: squared temporal energy differs
by `32^2 = 1024` between the oracle's nondegenerate z-score encoding and true
z-score units, and by `255^2 = 65,025` between historical `0..255` and rewrite
`0..1` off-mode intensity. Those are explicit unit conversions, not raw
conformance failures.

Carry forward these lessons:

- Downsample precedes normalization.
- Normalization is independent per active replicate/asset and frame.
- A global per-frame z-score is boundary-safer than tiled CLAHE.
- Z-score can counter slow global illumination/contrast drift.
- Z-score is not harmless: when the animal occupies much of the isolated frame,
  its motion can change frame statistics and reshape temporal amplitude.
- `off` must remain available.
- CLAHE has known hard-crop/tile-boundary artifacts and must not be restored
  casually.

Do not inherit:

- The `128 ± 32` scientific value encoding.
- OpenCV as an undeclared dependency.
- Implicit OpenCV epsilon, variance, dtype, threading, or version behavior.
- The oracle's default mode merely because it currently defaults to z-score.
- Any claim that normalization has already been biologically validated across
  assets and conditions.

The rewrite starts at `off` to preserve accepted milestone-5 behavior. Whether a
later validated product profile defaults to z-score is a separate decision.

## 16. Required implementation shape

Use the smallest extension of the accepted milestone-5 path:

```text
Qt-independent normalization value + pure operation
    NormalizationSpec
    normalize_working_frame(frame, spec)

accepted intensity computation
    RGB conversion
    area downsample
    normalize_working_frame
    block reduction
    existing result/outcome publication

Isolate owner
    session-local selected NormalizationSpec
    existing request/result/worker lifecycle

existing intensity panel
    mode-aware fixed presentation
    no scientific reinterpretation
```

Names are illustrative, but the reusable Qt-free operation at the pre-block
working-frame boundary is required. The current rewrite has no such hook:
`reduce_rgb_frame(...)` performs conversion, area reduction, and block
reduction together. Extract the minimum pre-block seam from that function and
reuse the existing block reducer. Do not introduce `PreprocessingPipeline`,
`ChannelRegistry`, `ScientificGraph`, a cache, or a new worker for one
operation.

## 17. Automated tests

Use tiny independent fixtures. The reference implementation must not call the
optimized production implementation.

### 17.1 `off`

Test:

- Every accepted milestone-5 reference result remains exact.
- No statistics backend is called.
- Input source bytes and published values are not mutated.
- Scientific units and `[0,1]` presentation remain unchanged.
- Degenerate flags are false.

### 17.2 Z-score mathematics

Test:

- A hand-computed four-pixel population z-score.
- Population variance is used, with a fixture that differs from sample
  variance.
- A nonzero constant frame returns exact float32 zeros and a true degenerate
  flag.
- A zero frame does the same.
- A one-pixel frame does the same.
- A frame just below epsilon is degenerate.
- A pinned boundary case at epsilon follows one declared comparison rule.
- Positive affine rescaling of a nondegenerate frame gives the same result
  within the declared tolerance.
- Output has near-zero pixel mean and near-one population standard deviation.
- Negative and greater-than-one z-scores are retained, not clipped.
- Any non-finite input pixel fails the complete frame rather than being filtered
  out; non-finite statistics/output also fail rather than becoming zeros.
- Non-finite failure does not set the degenerate flag or publish a partial
  finite-pixel result.
- Input is not mutated.
- Batch size does not change accepted results beyond one declared tolerance.

### 17.3 Ordering and geometry

Pin cases proving:

- Area downsample then z-score differs from z-score then area downsample, and
  the former is selected.
- Z-score then block mean differs from block mean then z-score, and the former
  is selected.
- Statistics include pixels in partial right/bottom cells exactly once.
- Weighted block reconstruction agrees with the working-frame mean.
- A one-frame temporal window is valid.
- Overlapping absolute frames computed in different selected windows agree for
  the same asset, grid, and mode because normalization is per frame, not fitted
  over the window.
- The pure normalizer operates before block geometry, can normalize a future
  context frame, and does not add that frame to requested output coverage.

### 17.4 Request, result, and resource policy

Test:

- Result keys differ between `off` and z-score.
- Result keys differ when scientific epsilon or implementation identity differs.
- Resource limits, execution target, and batch size remain request/execution
  inputs but do not change the scientific key.
- GUI tokens and presentation ids do not alter scientific values, result
  equality, or scientific keys; presentation ids are absent from the headless
  scientific result.
- Result normalization identity, units, provenance, and flags align with
  absolute processed frames.
- Degenerate flags have the promised exact byte representation.
- Retained-byte estimation includes the flags, is overflow-safe, and rejects
  over-budget work before source construction.
- The estimate reports compositional retained scientific payload bytes
  separately from peak live/process memory.
- Exact-budget work is admitted.
- Source and channel outcomes remain distinct and unchanged.
- No PyQt import enters the headless normalization/science module.

### 17.5 Oracle/conformance

Test:

- Rewrite-native reference fixtures are authoritative.
- Nondegenerate current-oracle z-score fixtures compare after
  `(oracle_value - 128) / 32`.
- Applicable `off` fixtures compare after `0..255 -> 0..1` conversion.
- Degenerate fixtures follow exact-zero plus explicit-flag behavior.
- Reports label contract conformance separately from unit-converted
  current-oracle comparison.
- Forward fixtures record the `32^2` and `255^2` scaling that milestone 7 must
  apply when comparing squared change energy.

### 17.6 GUI invalidation and supersession

Run Qt tests offscreen using the repository's established environment.

Test:

- A mode choice before the first computation does not auto-start work.
- **Compute intensity** captures the selected immutable normalization.
- Changing mode with a current result detaches it immediately and starts the
  replacement through the accepted handshake.
- Changing mode during source construction, processing, close, and publication
  cannot publish the obsolete mode.
- Rapid `off -> z-score -> off` retains only the newest pending request and
  never overlaps source-owning workers.
- Old progress, failure, cancellation, and success cannot clear or repaint the
  newer request.
- A resource-refused or failed replacement leaves no old result labelled
  current under the new mode.
- Asset switching retains mode intent but shares no computed statistics or
  result.
- Application restart returns to `off`.
- Closing Isolate during recomputation verifies source/worker shutdown.

### 17.7 Panel

Test:

- `off` uses the accepted fixed `[0,1]` mapping.
- Z-score uses fixed `[-3,3]` presentation clipping without mutating values.
- Zero maps to the diverging presentation center.
- Hover displays the real value outside `[-3,3]`.
- Mode, units, mapping, clipping, and degenerate state are labelled.
- Cursor and click-to-seek behavior remain on the existing player clock.
- Cursor motion and panel resize do not recompute.
- No value-band, selected-block overlay, count, Morlet, or detector control
  appears.

### 17.8 Existing regressions

The complete accepted media, active-asset, player, working-window, working-grid,
intensity, worker-lifecycle, resource-policy, and cleanup suites continue to
pass. Do not weaken milestone-5 provenance, memory, outcome, or stale-publication
assertions to add normalization.

## 18. Manual acceptance

After automated tests pass, stop and return the milestone for user validation.
Do not begin change energy.

Manual path:

1. Open a registered isolated asset and choose a short window and visible grid.
2. Leave normalization **Off**, compute intensity, and confirm the result agrees
   with the accepted milestone-5 behavior and `[0,1]` legend.
3. Change to **Per-frame z-score**. Confirm the old result disappears
   immediately and one replacement computation starts without freezing the
   player.
4. Confirm the completed panel reports z-score units and a fixed `[-3,3]`
   presentation mapping rather than `[0,1]` or an autoscaled range.
5. Hover values at both presentation extremes and confirm the readout preserves
   real stored values outside the displayed range.
6. Use a constant or near-constant lossless fixture. Confirm exact-zero output
   is labelled degenerate, not failed or missing.
7. Play, step, scrub, and click panel columns. Confirm the one absolute player
   clock remains synchronized and no cursor action recomputes.
8. Toggle modes rapidly during processing. Confirm only the newest mode can
   become current and no overlapping source workers or late repaint occurs.
9. Change the window, grid, and active asset during z-score work. Confirm stale
   data disappears immediately, mode intent survives the asset switch, and no
   fitted statistics cross the boundary.
10. Cancel and close during normalization work. Confirm verified worker/source
    shutdown and no late result.
11. Confirm there is no CLAHE, change-energy, value-band, block-highlight,
    Morlet, or detector control.
12. Inspect representative real footage with both modes and record qualitative
    differences without treating that inspection as biological validation.

## 19. Definition of done

Milestone 6 is complete only when:

- Milestone 5 is implemented, manually accepted, and reflected in the
  rewrite-side divergence refresh.
- The only modes are `off` and per-frame population z-score.
- One reusable Qt-independent working-frame operation performs normalization
  after area downsampling and before block reduction without depending on the
  panel, block geometry, final result allocation, or requested output span.
- `off` preserves milestone-5 science and presentation.
- Z-score uses fixed epsilon `1e-6`, float64 reference accumulation, population
  variance, float32 storage, and exact-zero degenerate output.
- Scientific z-scores are dimensionless and are not encoded as `128 ± 32`.
- Every processed frame has aligned, explicit degenerate evidence.
- Every input pixel is required finite; the implementation never silently
  normalizes a filtered finite subset.
- Requests, results, keys, units, provenance, and exact memory admission include
  normalization correctly.
- The accepted 16 GiB CPU and 6 GiB GPU policy defaults remain unchanged;
  compositional retained scientific payload includes the new flags while peak
  live/process memory remains separately bounded or measured. CPU remains the
  only implemented execution target.
- Normalization changes immediately invalidate old data and safely recompute an
  already-established intensity result using the accepted supersession
  handshake.
- No two scientific source owners overlap and no obsolete signal can publish.
- The panel uses fixed mode-specific presentation and never autoscale-mutates
  scientific values; presentation state is absent from the headless scientific
  result and key.
- Mode intent is session-local, begins at `off`, survives asset switches without
  sharing fitted state, and is not persisted.
- Headless numerical, bounded-resource, lifecycle, offscreen GUI, and existing
  regression tests pass.
- Oracle comparisons use explicit rewrite-native unit adapters, and the future
  temporal-energy scale consequences are recorded.
- Future context frames can use the same pure normalizer without entering
  requested output coverage, and future value bands cannot silently cross
  incompatible normalization units.
- The user has visibly validated and accepted the milestone.
- CLAHE and milestones 7 onward remain absent.

Stop here. Change energy and static value filtering require their own accepted
handoff and are not authorized by completion of normalization.
