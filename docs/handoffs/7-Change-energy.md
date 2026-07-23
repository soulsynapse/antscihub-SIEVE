# 7 — Add temporal change energy

Status: handoff only. Implementation is not authorized until milestones 5 and
6 have been implemented, visibly validated, and accepted, and the rewrite-side
divergence refresh in section 1.1 has been completed.

This milestone adds the first temporal scientific channel to Isolate:

```text
sieve.channel.rgb601_change_energy.v1
```

It ports the oracle's `change` / `J_tt` meaning without porting the oracle's
multi-replicate atlas, broad tensor planner, detector, or GUI architecture.
For output frame `t`, the channel measures the spatially integrated squared
difference between normalized working frames `t-1` and `t`, then reduces that
field over the accepted block grid.

The required pipeline is:

```text
native rgb24 frames t-1 and t
    -> milestone-5 post-decoder RGB intensity
    -> accepted area downsample to working resolution
    -> milestone-6 normalization, independently per frame
    -> temporal difference I[t] - I[t-1]
    -> pointwise square
    -> fixed spatial Gaussian integration
    -> accepted owned-pixel block reduction
    -> immutable change-energy result aligned to absolute frame t
    -> selected channel panel and current-frame block overlay
```

This is `J_tt` only. It does not compute `I_x`, `I_y`, `J_xx`, `J_yy`,
`J_xy`, `J_xt`, `J_yt`, optical flow, appearance residual, texture, or speed.

## 1. Precedence and implementation gate

This handoff follows the accepted implementations of:

- `1-Build-the-player.md`.
- `2-Media-service-handoff.md`.
- `3-Working-window.md`.
- `4-Working-grid.md`.
- `5-First-channel.md`.
- `6-Normalization.md`.

Milestones 5 and 6 are hard prerequisites. Do not implement this document
against their illustrative request, result, worker, panel, or normalization
types. First return those milestones for visible validation, then adapt this
handoff to their real accepted seams.

Milestone 7 must reuse rather than replace:

- The registered one-asset processing world.
- The accepted absolute half-open working-window request.
- The media service and request-local source ownership.
- The resolved working grid and exact partial-cell geometry.
- The post-decoder RGB intensity conversion
  `sieve.channel.rgb601_intensity.v1`.
- The selected normalization operation and its degenerate-frame evidence.
- The source/channel outcome composition.
- The Qt-free execution-resource policy and pre-source admission boundary.
- The one-active-worker/one-newest-pending-request supersession handshake.
- The existing channel panel's absolute player clock.

Completing this handoff does not authorize starting milestone 7. Completing
milestone 7 does not authorize static value filtering, Morlet processing, or
detection.

### 1.1 Required rewrite-side divergence refresh

Before implementation, update `.isolate-state-divergence.md` with current facts
from the accepted milestone-6 source and tests:

- Concrete request, result, normalization, outcome, resource-policy, and worker
  types.
- Exact frame delivery, RGB conversion, area-downsample, normalization, and
  block-reduction seams.
- Whether the working-frame operation can be called for a context frame without
  publishing that frame as requested output.
- How normalization's per-frame degenerate evidence is represented.
- Current result keys and invalidation events.
- Exact retained-result memory accounting.
- GUI ownership of channel selection, settings, current result, worker,
  cancellation, publication token, and pending replacement.
- Panel raster, cursor, hover, seek, legend, and presentation-mapping seams.
- The exact `IsolatePlayer` presentation inputs. In particular, report whether
  it still has only the grid-specific `set_working_grid(...)` seam.
- How an accepted decoded frame's absolute identity reaches the player. A
  requested/session frame is not enough if display decode may land later.
- Player overlay ownership and its mapping from working-grid cells to the
  displayed source frame.
- Current media/viewer benchmark evidence relevant to overlay preparation,
  image scaling, and paint.
- Worker/source cancellation and verified-close behavior.
- Automated and manual acceptance evidence for milestones 5 and 6.
- Any real implementation detail conflicting with this handoff's temporal
  alignment, context, spatial integration, validity, or selected-channel-only
  requirements.

Report code and test facts, not commit subjects or planned class names. Adapt
this handoff to the smallest accepted seam. Do not create a parallel media
session, normalizer, grid, worker, player clock, or result owner.

### 1.2 Review corrections already incorporated

This handoff was reviewed against the SIEVE checkout based on commit `6c09ac6`,
with the in-progress milestone-6 implementation visible in the working tree.
The following corrections control later sections:

1. The rewrite's accepted `ExecutionResourcePolicy` defaults are 16 GiB CPU and
   6 GiB GPU, with execution still CPU-only for the current channel. The stale
   512 MiB proposal is not part of this milestone.
2. `IsolatePlayer` currently has one grid-specific presentation input and no
   channel-value overlay input. Milestone 7 should make the smallest coherent
   extension of that player; it must not pretend a general overlay framework
   already exists or introduce one speculatively.
3. The player currently receives image bytes without an authoritative absolute
   displayed-frame identity. A value overlay requires that identity so a
   requested frame cannot be painted over a different frame whose decode is
   still on screen.
4. The milestone-5 row-major time-by-block raster is a useful implementation
   scaffold but a poor permanent scientific view at dense grids. With a
   `93 x 94` grid it creates 8,742 arbitrary horizontal rows and aliases them
   into a few hundred display pixels. Milestone 7 replaces that presentation
   contract with a time-by-value density while retaining the immutable
   `T x R x C` scientific result and exact spatial inspection through the
   player overlay.
5. Current GUI orchestration is intensity-specific
   (`_intensity_worker`, `_pending_intensity`, `_intensity_result`). Adding a
   second independent worker/mailbox family would violate the accepted single
   active scientific owner. Milestone 7 must generalize only the orchestration
   envelope required to select one of the two concrete channels.
6. The accepted grid retains partial-cell area weights specifically for later
   density and occupancy semantics. A narrow edge sliver must not contribute the
   same density mass as a full block. The panel therefore accumulates
   area-weighted block mass while leaving every stored scientific block value
   unchanged.

## 2. Outcome

At completion:

1. Isolate can select exactly one of the two implemented channels:
   **Intensity** or **Change energy**.
2. Selecting Change energy computes only its real prerequisites.
3. A Qt-independent caller can compute the same result as the GUI.
4. Every output sample is aligned to the later absolute frame of an explicit
   `(t-1,t)` pair.
5. A mid-asset window obtains one preceding context frame without widening
   requested or processed output coverage.
6. Asset frame zero is explicitly temporally invalid, not a scientific zero.
7. The result retains normalization mode, pair validity, degenerate-frame
   evidence, spatial-integration identity, grid identity, and source outcome.
8. The selected channel panel uses absolute frame/time and a binned
   time-by-value density with honest fixed value mapping.
9. One selected-channel overlay seam displays the current retained Intensity or
   Change energy block field without decoding or recomputing.
10. Intensity science remains unchanged. Its milestone-5 row-major raster is
    replaced by the selected-channel density panel, and its spatial values
    become inspectable through the shared overlay seam.

## 3. Scope boundary

Implement:

- One concrete immutable change-energy request and result, or the smallest
  extension of the accepted channel contract.
- A two-frame temporal operation over normalized working pixels.
- One-frame lookback for windows starting after asset frame zero.
- Explicit pair alignment and temporal-validity evidence.
- The oracle-compatible `J_tt` pointwise and spatial-integration rule.
- Owned-pixel block means on the accepted grid.
- Selected-channel-only planning for Intensity versus Change energy.
- Exact retained-result admission before scientific media opens.
- One selected-channel time-by-value density panel with channel-specific fixed
  value mapping, hover, cursor, and seek.
- One selected-channel current-frame overlay seam used by both the accepted
  Intensity result and the new Change energy result.
- Authoritative displayed-frame identity sufficient to pair an overlay slice
  atomically with the video frame actually on screen.
- Explicit player compositing and invalidation rules for the channel overlay,
  existing grid overlay, and base video.
- Headless numerical, boundary, lifecycle, resource, and offscreen GUI tests.

Do not implement:

- A general channel registry, plugin system, typed DAG executor, or add/remove
  channel framework.
- Simultaneous computation of every known channel.
- Intensity as an automatically retained result when only Change energy is
  selected.
- Spatial derivatives, flow, speed, texture, appearance residual, or any tensor
  component other than the `tt` meaning defined here.
- Temporal denoising, registration, background subtraction, CLAHE, masking, or
  color predicates.
- A value band, threshold, selected-block classification, per-frame count,
  clump, gate, or detection.
- Morlet/scalogram computation.
- Whole-asset execution, persistence, recipe/CLI exposure, checkpointing, or
  processing plans.
- Result caching across channel changes.
- Reuse of player/display pixels as scientific input.
- A retained row-major time-by-block image as the permanent user-facing channel
  visualization.

The overlay is a continuous visualization of the selected channel's retained
block values. It is not a thresholded selection and must not anticipate
milestone 8's selected-block semantics.

## 4. Required distinctions

Keep these concepts separate:

- Requested output frames from source frames read as temporal context.
- A decoded context frame from processed output coverage.
- Pair alignment to frame `t` from an interval between unnamed array positions.
- An invalid no-predecessor sample from a valid zero-change sample.
- A normalization-degenerate frame from an invalid temporal pair.
- Pointwise temporal energy from its spatially integrated field.
- Spatial Gaussian integration from block reduction.
- A `J_tt`-only computation from a full structure tensor.
- Scientific values from their presentation mapping.
- Scientific `T x R x C` block values from a binned density presentation.
- Requested/session frame position from the absolute frame actually displayed.
- A continuous selected-channel value overlay from future thresholded block
  highlighting.
- Channel selection from worker publication generation.
- A stale result from a current result whose player cursor is out of range.

In particular:

```text
valid value 0.0 != invalid because frame t-1 does not exist
```

Consumers must consult temporal validity. They may not infer validity from the
numeric payload.

## 5. Fixed scientific definition

Let `N_t(y,x)` be the milestone-6 normalized working-resolution intensity at
absolute frame `t`.

For every `t > 0`:

```text
D_t(y,x) = N_t(y,x) - N_(t-1)(y,x)
P_t(y,x) = D_t(y,x) * D_t(y,x)
S_t      = gaussian_integrate(P_t)
E_t(r,c) = mean(S_t[y0:y1, x0:x1])
```

`E_t` is aligned to absolute frame `t`.

Requirements:

- Subtract in the order current minus previous. Squaring makes the final energy
  unsigned, but the order remains fixed for future composition and fixtures.
- Compute the difference and square in `float32` after each input frame has
  completed the accepted intensity, downsample, and normalization operations.
- All input working pixels must be finite.
- Non-finite difference, product, integrated field, or block result is a
  structured computation failure. Never replace it with zero.
- Store final block values as `float32`.
- Values are nonnegative. Small negative backend roundoff is not clamped
  silently; a conforming implementation must not produce it.

The channel id is:

```text
sieve.channel.rgb601_change_energy.v1
```

Its identity includes the exact upstream intensity id, normalization
specification, temporal-difference rule, Gaussian-integration specification,
block-reduction rule, and implementation/backend provenance.

### 5.1 Units

With normalization `off`:

```text
N is post-decoder intensity in [0,1]
E units are post-decoder-intensity squared
E is in [0,1]
```

With `per_frame_zscore`:

```text
N is dimensionless z-score
E units are squared z-score
E is finite and nonnegative, with no fixed scientific upper bound
```

Do not label either mode as motion, speed, probability, likelihood, or detected
behavior. `J_tt` responds to any frame-to-frame intensity change, including
animal behavior, illumination changes, compression perturbations, camera
motion, and decoder/color-conversion differences.

## 6. Temporal alignment and context

The captured output request remains:

```text
[start_frame, stop_frame)
```

The source span needed by Change energy is:

```text
context_start = max(0, start_frame - 1)
source_span = [context_start, stop_frame)
```

The requested output span does not change.

For each requested absolute frame:

```text
t == 0  -> no predecessor; temporal_valid[t] = false
t > 0   -> pair (t-1,t); temporal_valid[t] = true if both frames completed
```

Examples:

```text
request [17,20)
source reads [16,20)
outputs are aligned to 17,18,19
pairs are (16,17), (17,18), (18,19)
processed output coverage is [17,20)
frame 16 is context only
```

```text
request [0,3)
source reads [0,3)
output frame 0 is invalid
output frames 1 and 2 use pairs (0,1) and (1,2)
valid processed output coverage is [1,3)
```

Do not:

- Treat the first requested frame as zero merely because the request begins
  there.
- Difference the first requested frame from itself.
- Pair it with the next frame and still label the result with the earlier frame.
- Wrap to the end of the asset.
- Ask the display player for the predecessor.
- Expand the GUI's selected window to expose the hidden context frame.
- Report the context frame as requested, displayed, or processed output.

The working-window/source contract may need the smallest bounded extension that
permits a captured scientific request to read the derived context span. Do not
weaken its existing rule that the request itself is absolute, explicit, and
validated.

### 6.1 Truncation and incomplete pairs

The implementation processes frames in absolute contiguous order.

- If a required predecessor cannot be delivered, its dependent output is
  unproduced/invalid.
- If frame `t` cannot be delivered, output `t` and every later undelivered frame
  remain unprocessed.
- A short read is propagated through the exact accepted source outcome.
- A partial result cannot be published as a complete quiet result.
- Completed valid prefix values may be described in the outcome, but milestone
  7 does not publish an interactive partial raster after cancellation or
  failure unless the accepted milestone-6 contract already does so safely.

Use explicit spans and validity, not fabricated zero tails.

## 7. Normalization and pair evidence

Apply the accepted normalization independently to both frames before
differencing:

```text
N_(t-1) = normalize(I_working_(t-1))
N_t     = normalize(I_working_t)
```

For per-frame z-score, no statistic crosses the frame boundary. Do not fit one
mean or variance over the pair or over the selected window.

A degenerate normalized frame is still valid scientific input under milestone
6. Therefore:

- A pair containing a degenerate frame remains temporally valid if both frames
  were delivered and normalized successfully.
- The result records, for every aligned output, whether the previous input,
  current input, or either input was normalization-degenerate.
- Degenerate evidence must not be collapsed into temporal invalidity.
- Two constant frames can validly produce zero change.
- A constant frame followed by a nonconstant frame can validly produce
  nonzero change under per-frame z-score.

For output frame zero, previous-frame degenerate evidence is absent/not
applicable, not `false` by invention.

## 8. Spatial Gaussian integration

The oracle's `change` channel is not merely a block mean of raw squared
differences. Before block reduction it spatially integrates `P_t` with one
fixed Gaussian:

```text
sigma_x = 2.0 working pixels
sigma_y = 2.0 working pixels
kernel size = 17 x 17
separable kernel = normalized discrete Gaussian
border mode = reflect-101
```

The one-dimensional reference weights are equivalent to:

```text
k[i] = exp(-0.5 * ((i-8)/2.0)^2), i = 0..16
k = k / sum(k)
```

Apply the horizontal and vertical kernels separably. The conformance reference
accumulates in `float64` and casts the integrated field to `float32`.
A measured float32 backend is allowed when it agrees with that reference within
the declared tolerance.

`reflect-101` excludes the edge pixel from its immediate reflected copy. For a
one-pixel axis, repeat the only sample. Small dimensions must remain defined;
do not crop away an eight-pixel border or mark it invalid.

The Gaussian is in working-pixel units:

- Changing downsample changes its source-pixel footprint.
- Changing block size does not change it.
- Do not reinterpret sigma in source pixels or blocks.
- Do not blur across an enclosing atlas or replicate seam. The active isolated
  asset is the complete spatial world.

Record a stable integration id equivalent to:

```text
sieve.spatial.gaussian_sigma2_reflect101.v1
```

Do not expose sigma as a GUI control in this milestone. A future configurable
tensor profile would be a new resolved setting and scientific identity.

### 8.1 Why this is still `J_tt`

Pointwise `P_t = I_t^2` is the raw `tt` product. Gaussian integration supplies
the local spatial window that the oracle applies before reading `J_tt`.
Computing only this plane preserves the meaning without constructing a six-plane
tensor object or paying for unused gradients.

If the rewrite already has a small scalar-field Gaussian operation, reuse it
only after its kernel, border, dtype, and identity conform. Do not add a general
tensor abstraction solely to hold one scalar plane.

## 9. Block reduction and partial cells

Reduce the integrated field over the exact accepted grid:

```text
R = grid.rows
C = grid.columns
b = grid.resolved_block_size

y0 = r*b
y1 = min((r+1)*b, work_height)
x0 = c*b
x1 = min((c+1)*b, work_width)

E[t,r,c] = mean(S_t[y0:y1, x0:x1])
```

Requirements:

- Use only pixels owned by the cell.
- No padding enters the mean.
- Accumulate the conformance mean in `float64`.
- Store `float32`.
- Preserve the accepted `owned_area/(b*b)` partial-cell weight.
- Partial-cell weight does not multiply the energy mean.
- Retain explicit `(row,column)` axes. Any internal flat traversal is row-major
  and reversible, but flattened block identity is not a user-facing value axis.
- Geometry mismatch is a structured stale-input failure, never a crop/pad
  fallback.

Gaussian integration occurs over the complete working frame before block
reduction. It therefore allows evidence near a block boundary to contribute to
both neighboring blocks through the fixed spatial kernel. Do not blur each
block independently.

## 10. Headless request, result, and identity

Keep the contract concrete. A request contains or resolves the equivalent of:

```text
working_window_request
resolved_grid
channel_id = sieve.channel.rgb601_change_energy.v1
intensity_conversion_id = sieve.channel.rgb601_intensity.v1
normalization_spec
spatial_integration_spec
implementation_id
bounded source/execution settings
optional cancellation token/callback
```

The scientific result contains at least:

```text
asset id and recorded content identity
content-verification status
requested absolute half-open output span
required source/context span
valid processed output span or explicit coverage
exact rational fps
source and working dimensions
effective scale and resolved grid
partial-cell geometry/weights
channel, intensity, normalization, and integration ids
implementation/backend provenance
absolute output frame span
values shaped T x R x C, float32
temporal_valid shaped T
previous_normalization_degenerate shaped T, nullable/not-applicable at frame 0
current_normalization_degenerate shaped T
exact WorkingWindowOutcome
channel-stage outcome
```

For a fully delivered request:

```text
T == stop_frame - start_frame
values.shape == (T,R,C)
output indices are start_frame .. stop_frame-1
temporal_valid is true exactly where t > 0
all valid values are finite and nonnegative
```

The numeric storage at an invalid output position may be zero-initialized for a
compact dense array only if:

- `temporal_valid` is mandatory and retained.
- Every scientific consumer masks invalid positions.
- The panel and overlay never render the placeholder as valid zero change.
- Tests prove invalid frame zero cannot enter later counts or transforms.

Using `NaN` instead is allowed only if it remains compatible with the accepted
finite-result and presentation contracts. Do not let sentinel choice become
scientific identity; validity is authoritative.

### 10.1 Result key

The result key includes at least:

- Resolved asset/content identity and verification status.
- Requested output span.
- Source plane and media conversion identity.
- RGB intensity conversion id.
- Resolved working dimensions and area-downsample implementation identity.
- Normalization mode, epsilon, and implementation id.
- Temporal alignment/difference implementation id.
- Gaussian kernel, sigma, border rule, and implementation id.
- Grid dimensions, block size, bounds/weight contract.
- Change-energy channel implementation version.

It excludes:

- GUI publication token.
- Worker id or thread id.
- Panel dimensions.
- Color map and overlay opacity.
- Player position.
- Source batch size when conformance proves batch invariance.
- Effective resource limit.

The resource limit belongs in execution provenance, not scientific identity,
unless it changes valid numerical results, which this milestone forbids.

## 11. Resource admission and bounded execution

Perform exact retained-result admission through the accepted
`ExecutionResourcePolicy` before opening a scientific source. Use its existing
target-specific result-memory query; do not add a channel-local limit or assume
an illustrative field name such as `max_retained_result_bytes`.

Account for every retained scientific array in the accepted concrete
representation:

```text
values bytes = T * R * C * 4
temporal-validity bytes
previous/current degenerate-evidence bytes
materialized frame-index bytes, if indices are not represented by a span
other retained per-frame scientific arrays, if any
```

Use overflow-safe arithmetic. Admit exactly at the effective target-specific
limit and reject one byte over with requested and allowed byte counts.

Do not count the lookback context frame as a retained output frame. Do include
any additional retained validity/evidence arrays. Fixed small metadata need not
be approximated as array payload, but the accounting rule must be explicit and
tested.

Peak live/process memory remains separately bounded:

- Retain at most the preceding normalized working frame needed for the next
  pair, plus the bounded current-frame work.
- Release decoded RGB and replaceable intermediates promptly.
- Do not retain full-resolution differences or integrated fields across time.
- Do not materialize both complete Intensity and Change energy results.
- Panel and overlay should reference or rasterize the current retained result
  without an uncontrolled duplicate `T*R*C` scientific array.

The accepted defaults remain 16 GiB for CPU retained results and 6 GiB for GPU
retained results. Current channel execution remains CPU-only unless a separately
validated backend is added. These limits are retained-result policy, not
total-process-memory claims, and this milestone does not add or change the
Resources UI.

## 12. Selected-channel-only execution

Add the smallest explicit channel choice:

```text
intensity | change_energy
```

This is not a registry.

When Intensity is selected, preserve milestone 6 exactly and do not compute:

- A predecessor/context frame solely for channel work.
- Temporal difference or square.
- Gaussian integration.
- Change-energy output.

When Change energy is selected, compute:

- The working normalized intensity frames needed as ephemeral prerequisites.
- `tt` pointwise energy.
- Its one Gaussian integration.
- Its block result.

Do not block-reduce or retain an Intensity channel result when Change energy is
selected. Milestone 7 has no multi-select UI, so one GUI job requests one
channel.

The concrete execution path may share ephemeral
conversion/downsample/normalization work inside the selected job. It must not
compute unused spatial gradients, tensor components, flow, residual, texture,
or future channels. Do not introduce a graph planner merely to make that
statement.

Generalize the existing intensity-specific GUI orchestration only far enough to
own:

```text
one active selected-channel request
one active scientific worker
one newest pending selected-channel request
one current selected-channel result
one publication generation/token
```

Do not retain parallel intensity and change workers, pending mailboxes, result
owners, or cancellation handshakes. Concrete headless `IntensityRequest` and
`ChangeEnergyRequest` types may remain distinct; the GUI envelope needs only the
small tagged union/protocol required to drive exactly one of them safely.

The explicit compute action must match the selection. Either relabel it as
**Compute selected channel** or update its accessible text to
**Compute intensity** / **Compute change energy**. Do not leave a button labelled
**Compute intensity** that launches Change energy.

### 12.1 Channel-selection behavior

Channel intent is Isolate-session-local:

- Initial selection remains Intensity so accepted behavior does not change on
  upgrade.
- Selection survives active-asset switches, then resolves against the new
  asset/window like other retained intent.
- It is not persisted in this milestone.

Committing a new channel selection:

1. Immediately removes or clearly disables the old result, panel raster, and
   overlay.
2. Captures one immutable replacement request if a result or job already
   existed.
3. Supersedes through the accepted one-active/one-newest-pending handshake.
4. Allows only the newest matching result key and publication token to become
   current.

Merely opening the selector without committing a different value does nothing.
If no result or job has ever existed, changing selection updates intent and
controls but does not start computation implicitly. If a current result or job
exists, preserve the accepted milestone-6 replacement behavior and compute the
newly selected channel through the single supersession handshake.

## 13. Coverage, outcomes, and errors

Change energy processes temporal pairs, not isolated frames.

Record separately:

```text
requested output span
source-delivered span, including context
temporally valid output coverage
normalization-degenerate evidence
channel-stage produced coverage
```

A valid produced change value means the pair was scientifically examined for
this channel. It does not mean quiet, selected, detected, or behavior-negative.

The result composes the exact accepted `WorkingWindowOutcome` with a small
channel-stage outcome. Do not duplicate source lifecycle states into another
competing enum.

Surface structured failures for:

- Invalid requested/context span.
- Missing or failed predecessor delivery.
- Noncontiguous or mislabeled absolute source indices.
- Source/grid extent mismatch.
- Invalid or non-finite working frames.
- Normalization failure.
- Non-finite/negative temporal energy.
- Gaussian backend mismatch or failure.
- Block geometry mismatch.
- Retained-result resource rejection.
- Cancellation or verified source/worker shutdown failure.

Messages identify the asset, requested span, failed pair/frame when applicable,
and stage. They do not dump arrays or imply invalid samples were zeros.

## 14. GUI panel

Reuse the existing channel area and absolute-frame cursor/seek behavior. Add a
compact channel selector rather than a card registry or multiple simultaneous
panels.

The milestone-5 row-major raster must not become the permanent visualization.
It assigns arbitrary spatial block identity to the y axis, so a dense grid
becomes thousands of horizontal stripes compressed into a few hundred screen
pixels. That is difficult to interpret and does not prepare the panel for
milestone 8's value-band selection.

Replace its presentation with one selected-channel time-by-value density:

```text
x axis: absolute output frame/time
y axis: selected channel's scientific value through its fixed mapping
pixel brightness: area-weighted block mass in that frame/value bin
invalid/uncovered frame: visibly absent or hatched, never counted as zero
```

The immutable scientific result remains `T x R x C`. Density binning is a
presentation derivation owned by the panel, not a replacement result, channel
transform, or new coverage claim.

Requirements:

- Derive density only from the current selected immutable result.
- Bin finite values without spatial averaging. A full valid block contributes
  mass `1`; a partial valid block contributes its accepted
  `owned_area/(b*b)` weight to its frame/value bin.
- Partial weight changes density mass only. It never multiplies or changes the
  scientific channel value used to choose the bin.
- Keep the y-value mapping fixed by channel and normalization as section 14.1
  defines. Never derive y-axis limits from the current window.
- Log-scaling or normalization of bin **mass** is allowed as a labelled
  presentation choice; it must not move the scientific value axis or enter a
  result key.
- If multiple source frames land in one display column, aggregate their counts
  into that column without shifting their absolute covered span.
- Cache a rendered density by result identity, mapping id, and widget size.
  Cursor movement must not rebuild it.
- Panel resize may rerasterize the density from retained values but must not
  start scientific work.
- Do not allocate one widget/item per block, value bin, or frame.

Visible context includes:

- Selected channel name and id.
- Absolute output window and valid pair coverage.
- For Change energy, alignment text equivalent to
  `value at t compares t-1 -> t`.
- Source/working dimensions.
- Grid rows, columns, and block size.
- Normalization mode and scientific units.
- Fixed value mapping and density-mass brightness rule.
- Cursor tied to the player's absolute frame.

Cursor and click-to-seek behavior remain the milestone-5 single-clock behavior.
No cursor movement recomputes.

Panel hover reports at least:

```text
absolute frame t and exact time
scientific value-bin interval
raw block count and area-weighted block mass in the bin
frame/channel validity
for Change energy: pair (t-1,t), or no predecessor
```

The density panel cannot honestly identify one spatial block from an aggregated
bin. Exact block `(r,c)`, value, bounds, weight, and degenerate/temporal evidence
belong in the current-frame player-overlay hover/readout described in section
15.2.

### 14.1 Fixed presentation mapping

Presentation never mutates stored values and never autoscales to the current
window.

For normalization `off`, use:

```text
display = clamp(E, 0, 1)
legend = 0 .. 1 post-decoder-intensity squared
```

For `per_frame_zscore`, use one fixed monotone saturating mapping:

```text
display = E / (E + 1)
legend/readout states that display 0.5 corresponds to E = 1 z-score squared
```

The z-score mapping preserves ordering over `[0,+infinity)` without inventing a
scientific maximum. Hover/readout always reports real `E`, including values far
into the presentation saturation region.

For Intensity, retain milestone 6's fixed mappings:

```text
off                 -> sequential [0,1] intensity mapping
per_frame_zscore    -> diverging [-3,+3] mapping centered at zero
```

For either selected channel, its panel and player overlay use the same mapping
id and value color map. The density panel additionally maps weighted bin mass
to brightness; that brightness mapping does not change the value axis.
Presentation mapping, color map, density brightness, opacity, and rasterization
are not scientific identity.

## 15. Selected-channel current-frame overlay

Establish one presentation-only player seam for the current retained block field
of the selected channel. Milestone 7 must use that same seam for both:

```text
Intensity
Change energy
```

Do not implement separate `IntensityOverlay` and `ChangeEnergyOverlay` player
paths. The player needs presentation-ready block values and geometry, not
channel-specific scientific logic.

### 15.1 Ownership and wiring

Ownership is:

```text
Isolate scientific/controller state
    owns selected channel and current immutable result
    resolves the accepted displayed absolute frame to one retained result slice
    applies channel-specific validity
    supplies presentation mapping identity
        |
        v
selected-channel overlay presentation input
        |
        v
player paints through its existing image transform
```

The player does not:

- Select a channel.
- Look up a scientific result from another tab or global registry.
- Interpret normalization or temporal validity independently.
- Decode, normalize, difference, smooth, reduce, or threshold.
- Own scientific result lifetime or invalidation.

The accepted Isolate position remains the only navigation/playback clock, but it
is not sufficient proof of what pixels are currently on screen. Display decode
can complete after the requested position has advanced. Extend the accepted
display-frame delivery by the smallest explicit absolute-frame identity needed
to gate presentation.

On an accepted displayed-frame change, the Isolate owner derives at most one
matching overlay slice from the already-retained selected result and requests a
repaint. No scientific worker starts.

A small immutable presentation input may be equivalent to:

```text
publication/result token
absolute displayed frame
resolved grid or exact cell bounds
R x C retained block-value view
presentation mapping id
channel label/units for optional readout
valid for presentation
```

This is illustrative and is not a general scientific channel interface. It may
hold a read-only view into the retained result; it must not copy the whole
`T x R x C` array on every seek.

Frame and overlay acceptance must be atomic or independently identity-gated:

```text
paint channel values for t only when displayed_video_frame == t
otherwise paint the video without a channel overlay
```

A newly requested frame clears or suppresses the previous channel layer until a
matching displayed frame and retained slice are both available. Never preserve
the old overlay merely because the new decode is late.

### 15.2 Channel-specific source and validity

For Intensity:

- Read the retained Intensity value slice for the player's absolute frame.
- Every successfully processed frame in the current result is presentable,
  including a valid normalization-degenerate zero frame.
- Use the exact milestone-6 mapping for the result's normalization mode.

For Change energy:

- Read the retained `E[t,:,:]` slice.
- Present it only when the absolute frame is in the current result and
  `temporal_valid[t] == true`.
- Frame zero or any other temporally invalid output is absent, not dark zero.
- Use section 14.1's fixed mapping for the result's normalization mode.

For both channels:

- The overlay appears only for a current result whose scientific key and
  publication token match the selected channel and current Isolate inputs.
- The overlay's absolute frame must equal the authoritative identity of the
  video frame actually held by the player, not merely the requested session
  position.
- Each cell covers its exact source/working-grid footprint, including partial
  right and bottom cells.
- It transforms through the player's existing image-to-widget mapping and stays
  aligned during resize, fit, seek, and any later zoom behavior. Milestone 7
  does not add zoom if the current player still lacks it.
- It uses the selected panel's exact fixed presentation mapping and color map.
- It does not hide the underlying video completely; use one modest fixed
  default opacity and one presentation-only **Show channel overlay** toggle.
- Out-of-window frames, stale results, channel switches, and channel-specific
  invalid samples clear the channel overlay immediately.
- Playback may omit the overlay for an expensive frame to remain responsive,
  but omission means clearing that frame's channel layer. It may never carry
  the preceding overlay forward over new video pixels.

Use one raster/layer or another bounded drawing strategy. Do not create one
long-lived widget or graphics item per block.

The overlay is continuous channel value. It has no threshold,
selected/unselected state, count, outline, or biological label.

Player-overlay hover or an adjacent readout reports:

```text
absolute displayed frame
selected channel and scientific units
block (r,c)
exact retained value
owned working bounds and partial-cell weight
normalization-degenerate evidence
for Change energy: temporal validity and pair (t-1,t)
```

### 15.3 Compositing with the accepted grid overlay

The player already has a geometry-only grid overlay from milestone 4. Paint
layers in this order:

```text
base video frame
-> selected-channel value overlay
-> grid boundary/lines, when Show grid is enabled and legible
-> any existing player chrome that must remain readable
```

This keeps block boundaries visible over channel color without baking either
layer into the video raster. **Show grid** and **Show channel overlay** are
independent presentation controls:

- Hiding the grid does not hide channel values.
- Hiding channel values does not hide the grid.
- Neither control invalidates science, changes coverage, or starts computation.
- Dense-grid suppression may omit internal grid lines under milestone 4's
  legibility policy; it must not suppress the channel-value raster.

Clearing or replacing a scientific result clears only its channel layer. Asset
or player-source replacement must clear both stale grid and channel layers
before or atomically with painting the new asset.

### 15.4 Bounded rendering and measurement

Do not construct a full-source-resolution color overlay merely because the
scientific asset is high resolution. The media handoff already showed that
full-resolution overlay preparation and blending can dominate playback.

Build a presentation raster no larger than the displayed image rectangle, or
use another measured representation with the same bounded pixel traffic.
Preserve partial-cell geometry by mapping display pixels through resolved
working coordinates; a uniform `R x C` stretch is insufficient when the right
or bottom cell owns fewer working pixels.

Cache geometry-to-display lookup state by resolved grid and display rectangle.
Per-frame work should primarily map the current `R x C` values through the fixed
color rule. Resize may rebuild presentation geometry; ordinary cursor movement
must not re-derive scientific data.

Before acceptance, measure on the same representative asset and viewer
conditions:

```text
video only
video + grid
video + selected-channel overlay
video + selected-channel overlay + grid
```

Record overlay preparation, paint, and end-to-end frame time separately. This
milestone makes no inherited performance claim from the oracle. A severe
playback regression is a failed implementation even when numerical tests pass.

## 16. State, invalidation, and lifecycle

The accepted scientific state machine remains:

```text
no active input
ready, no result
processing
stopping/superseding
complete current result
cancelled
failed
```

Change energy invalidates on:

- Active asset/content identity or verification-status change.
- Requested window change.
- Working dimensions/downsample change.
- Grid/block-size change.
- Intensity conversion or media-plane identity change.
- Normalization mode/epsilon/implementation change.
- Change-energy or Gaussian-integration identity change.
- Selected channel change.

It does not invalidate on:

- Player seek, step, scrub, or playback.
- Panel resize.
- Overlay visibility or opacity.
- Tab switch.
- Cursor or hover.

On invalidation, clear/disable the old raster and overlay immediately. A
captured worker request remains immutable; late completion cannot publish when
its key/token is stale.

The context frame does not justify a second source owner. The scientific worker
owns one request-local stream for context and output and closes it through the
accepted handshake. Cancellation is checked at bounded intervals, including
between frame pairs and spatial operations.

## 17. Oracle-derived guidance

The oracle currently implements Change energy in
`core.tensor_channels.stream_channel_planes`:

```text
I_t = current preprocessed working frame - previous working frame
J_tt = GaussianBlur(I_t * I_t, sigma=2)
change = owned-pixel block mean of J_tt
```

Useful behavior to preserve:

- A window starting after frame zero reads one preceding frame.
- Output aligns to the current/later frame.
- Change-only selection computes tensor component `tt` and none of the other
  five tensor products.
- It skips the flow solve, appearance residual, and texture read.
- Gaussian integration precedes block reduction.
- Partial blocks use their owned-pixel mean.

Oracle behavior not to inherit:

- Packing many replicate tiles when one selected isolated asset is the complete
  processing world.
- Filling the no-predecessor first frame with a plausible zero without explicit
  validity.
- Crop/pad fallback when computed grid shape drifts.
- A cache-shaped metadata contract.
- Broad string-based channel planning where a concrete two-choice seam is
  sufficient.
- Implicit OpenCV defaults without recorded kernel/border semantics.
- Any assumption that decoded frames alone constitute examined channel
  coverage.

Oracle comparisons require explicit unit adaptation:

- Historical oracle `off` preprocessing may use a different grayscale scale.
- Rewrite `off` intensity is `[0,1]`; squared-energy scale changes by the square
  of any amplitude conversion.
- Rewrite per-frame z-scores are true dimensionless z-scores, not historical
  `128 + 32*z`; energy comparisons must undo that encoding before squaring.
- Lossy clip/source comparisons are expected to affect squared differencing
  more strongly than block-mean intensity and must retain provenance.

Use oracle fixtures as conformance evidence, not as permission to copy its
architecture.

## 18. Suggested implementation shape

Fit this work into the accepted rewrite packages. The smallest conceptual
shape is:

```text
Qt-independent science/application layer
    ChangeEnergyRequest or concrete channel extension
    ChangeEnergyResult
    temporal_change_product(previous, current)
    gaussian_integrate_change(field)
    compute_change_energy(request, resource_policy)

Isolate-local GUI layer
    channel selector
    one selected-channel job/publication envelope
    one time-by-value density panel
    one selected-channel overlay presenter
    smallest extension of the existing grid-specific player presentation seam
    explicit accepted displayed-frame identity
```

Names are illustrative. Reuse small accepted types where they already preserve
the fixed contracts. Do not build a registry or general graph executor.

The headless compute shape should be testable without importing Qt:

```text
validate and admit retained result
open one context-aware working-window stream
for each delivered frame in absolute order:
    intensity -> area downsample -> selected normalization
    retain only previous normalized working frame
    if predecessor exists:
        difference -> square -> Gaussian integrate -> block mean
    record alignment, validity, and degenerate evidence
finalize exact source and channel outcomes
```

Optimization rules:

1. Pin the reference result first.
2. Measure the same asset/window before and after.
3. Preserve requested-channel-only work.
4. Bound peak buffers.
5. Keep an optimization only when it improves the measured bottleneck without
   violating numerical tolerance or lifecycle behavior.

Do not add GPU, multiprocessing, result spill, integral images, or parallel
frame-pair execution without evidence that this milestone needs them.

## 19. Automated tests

Use small deterministic lossless fixtures and the accepted rewrite test
environment.

### 19.1 Temporal mathematics

- Identical consecutive frames produce exact zero pointwise and block energy.
- A known scalar step produces the expected squared difference.
- Reversing the step produces the same energy but the fixture still verifies
  the fixed signed intermediate order.
- RGB conversion precedes differencing.
- Area downsample precedes normalization and differencing.
- Normalization occurs independently per frame.
- The result is finite, nonnegative `float32`.
- Inputs are not mutated.

### 19.2 Alignment and context

- Request `[17,20)` reads `[16,20)` and returns values aligned to 17, 18, 19.
- Pair identities are `(16,17)`, `(17,18)`, `(18,19)`.
- Context frame 16 is absent from requested and processed output coverage.
- Request `[0,3)` marks frame 0 invalid and frames 1–2 valid.
- A true zero at frame 1 is distinguishable from invalid frame 0.
- A one-frame request at frame zero succeeds with one invalid sample.
- A one-frame mid-asset request reads exactly one predecessor and produces one
  valid sample.
- Noncontiguous, duplicated, or mislabeled source indices fail.
- Missing predecessor and mid-request truncation preserve honest coverage.

### 19.3 Normalization and degeneracy

- `off` values and units are correct.
- Per-frame z-score values and squared units are correct.
- No statistics cross a pair or window boundary.
- Both previous/current degenerate flags align to the later output frame.
- A valid pair containing one or two degenerate frames remains temporally valid.
- Output frame zero has not-applicable previous-degenerate evidence.
- Changing normalization changes the result key and supersedes old work.
- Historical `128 ± 32` oracle fixtures are adapted before energy comparison.

### 19.4 Gaussian integration

- An impulse squared-difference matches an independent float64 17-tap,
  sigma-2, reflect-101 separable reference.
- Constant fields remain constant, including at boundaries.
- Edge and corner impulses pin reflect-101 rather than replicate/constant border.
- Width or height one remains defined.
- Small frames smaller than the kernel remain defined.
- Gaussian integration happens before block reduction.
- Sigma is in working-pixel units.
- Only the `tt` product is computed; spatial gradients and other tensor
  components are absent.

### 19.5 Grid and partial cells

- Exact-divisible and ragged right/bottom grids match an independent float64
  owned-pixel mean.
- No padding enters a partial mean.
- Partial-cell weights remain the accepted geometry values and do not multiply
  the mean.
- Gaussian evidence crosses internal block boundaries because integration
  precedes reduction.
- Geometry mismatch fails rather than cropping or padding.
- `(row,column)` axes and any reversible internal row-major traversal remain
  correct without making block identity the panel's y axis.

### 19.6 Identity, resource, and outcomes

- Every scientific setting listed in section 10.1 changes the result key.
- Presentation and execution-only settings do not.
- Retained bytes include values, validity, degenerate evidence, and any
  materialized indices.
- Exactly-at-budget admits; one byte over rejects before opening media.
- Context adds live bounded work but not a retained output plane.
- Peak live state retains only bounded current work and one previous normalized
  frame.
- Source and channel outcomes remain distinct and composed.
- Cancellation/failure cannot publish a complete result or fabricated zero tail.

### 19.7 Selected-channel-only planning

- Intensity selection performs no context read, temporal product, or Gaussian.
- Change selection does not retain/block-reduce an Intensity result.
- Change selection computes no spatial gradients, flow, residual, texture, or
  unrequested tensor plane.
- Initial selection is Intensity.
- Selection intent survives an asset switch but no result crosses the switch.
- Rapid toggles leave at most one active worker and one newest pending request.
- No parallel intensity/change worker, pending, result-owner, or cancellation
  families exist.
- The explicit compute action names the selected channel honestly.

### 19.8 Panel and overlay

- Panel cursor and click seek use absolute frame identity.
- Invalid frame zero is not rendered as quiet zero.
- Off and z-score presentation functions match section 14.1.
- Known small `T x R x C` fixtures produce the expected time/value-bin raw
  counts and area-weighted masses.
- Full cells contribute density mass one; ragged right, bottom, and
  bottom-right cells contribute their accepted partial weights.
- Invalid/uncovered values do not enter the zero-value density bin.
- Density-mass brightness does not move the fixed scientific value axis or
  mutate retained values.
- Multiple frames per display column retain correct absolute covered placement.
- Panel hover reports frame/time, scientific bin interval, raw count, weighted
  mass, and channel validity without claiming one aggregated block identity.
- Player-overlay hover reports exact block value, pair identity where
  applicable, validity, degenerate evidence, bounds, and weight.
- Intensity and Change energy use the same player overlay seam; no
  channel-specific player implementation exists.
- Each overlay reads the same retained block slice represented by its selected
  panel at the current absolute frame.
- Intensity uses milestone 6's fixed normalization-specific mapping.
- Change energy uses section 14.1's fixed normalization-specific mapping.
- A valid degenerate Intensity frame is presentable; an invalid Change energy
  frame is absent.
- Overlay clears outside coverage, on channel-specific invalidity, stale data,
  and channel change.
- Resize and fit preserve block alignment; any existing/future zoom path does
  too, but milestone 7 does not add zoom.
- A requested position advance clears/suppresses the old overlay until the
  matching decoded frame is actually accepted by the player.
- Late display decode and rapid-seek fixtures prove overlay frame `t` is never
  painted over video frame `u != t`.
- Omitting an overlay paint clears that frame's old channel layer.
- Show grid and Show channel overlay are independent.
- Grid lines composite above channel color when both are shown.
- Overlay controls do not invalidate science or start work.
- Seeking supplies at most one retained `R x C` view and does not copy the
  complete result.
- The presentation raster is bounded by displayed dimensions and preserves
  partial-cell widths/heights.
- Overlay-on/off benchmark output separates preparation, paint, and end-to-end
  frame time.

### 19.9 Existing regressions

The accepted active-asset, media, player, working-window, working-grid,
intensity, normalization, resource, lifecycle, and cleanup suites continue to
pass. Do not weaken earlier identity, provenance, finite-value, memory,
supersession, or shutdown assertions.

## 20. Manual acceptance

After automated tests pass, stop and return the milestone for user validation.
Do not begin static value filtering.

Manual path:

1. Open a registered isolated asset and choose a short window and visible grid.
2. Confirm Intensity scientific values remain as accepted. Confirm the old
   row-major stripe raster has been replaced by a time-by-value density, then
   enable **Show channel overlay** and verify the current retained Intensity
   slice spatially against the video.
3. Toggle **Show grid** and **Show channel overlay** independently. Confirm grid
   lines paint over channel color when both are enabled and neither toggle
   computes or invalidates anything.
4. Select Change energy. Confirm old intensity data and overlay disappear
   immediately and one replacement computation starts without freezing
   playback.
5. Use a mid-asset window. Confirm the first displayed output frame has a real
   change value derived from its hidden predecessor.
6. Move the window to frame zero. Confirm frame zero is visibly invalid/no
   predecessor, not dark zero, while frame one can show valid zero or nonzero
   energy.
7. Confirm the density panel states `t-1 -> t`, normalization mode, units,
   fixed value axis, weighted-density brightness rule, and absolute time.
8. Hover the density and confirm it reports a value bin, raw block count, and
   area-weighted mass without inventing spatial identity. Hover the player
   overlay and confirm exact real energy, block, pair identity, validity,
   degenerate evidence, bounds, and weight.
9. Seek, step, scrub, and play. Confirm the cursor and overlay follow accepted
   displayed-frame identity and never recompute. Seek rapidly and confirm a
   late frame never receives another frame's overlay.
10. Resize and fit the player. Confirm overlay cells remain aligned with their
    image regions, including partial edges. Do not require zoom if the player
    still has none.
11. Switch Off versus Per-frame z-score. Confirm the result and units change,
    stale data clears immediately, and the z-score display uses the fixed
    saturating mapping without hiding real hover values.
12. Switch back to Intensity and confirm the same player overlay seam now uses
    the milestone-6 sequential/diverging mapping without retaining the Change
    result.
13. Use constant and single-change lossless fixtures. Confirm valid exact-zero
    pairs and localized nonzero response.
14. Toggle Intensity/Change and normalization rapidly during work. Confirm only
    the newest request publishes and no source owners overlap.
15. Change window, grid, and active asset during work. Confirm immediate
    invalidation, retained selection intent, and no cross-asset context.
16. Cancel and close during context decode and during spatial integration.
    Confirm verified worker/source shutdown and no late panel or overlay update.
17. Confirm no value band, selected-block count, Morlet view, detector,
    whole-asset command, registry, or additional channel exists.
18. Inspect representative real footage and record whether Change energy makes
    behavior visually locatable, without treating that as biological
    validation.
19. Compare playback with video only, grid only, channel overlay only, and both
    overlays. Record preparation, paint, and end-to-end timing and reject a
    severe overlay-induced regression.

## 21. Definition of done

Milestone 7 is complete only when:

- Milestones 5 and 6 are implemented, visibly accepted, and reflected in the
  rewrite-side divergence refresh.
- One concrete selected channel choice exposes only Intensity and Change energy.
- Change energy uses
  `sieve.channel.rgb601_change_energy.v1`.
- Each valid value is `(t-1,t)` squared normalized-intensity difference,
  sigma-2 reflect-101 Gaussian integration, then owned-pixel block mean.
- Results align to the later absolute frame `t`.
- Mid-asset windows read exactly one bounded predecessor as context without
  widening output coverage.
- Frame zero is explicitly invalid, never fabricated quiet zero.
- Valid zero change remains distinguishable from invalidity.
- Normalization is applied independently to both frames before differencing and
  degenerate evidence remains separate from temporal validity.
- Only `J_tt` work is computed; no unused tensor plane, spatial gradient, flow,
  residual, texture, or intensity result is materialized.
- Requests, results, keys, units, provenance, validity, and outcomes carry all
  fixed scientific identity.
- Exact compositional retained-result admission occurs before source opening,
  and peak pair-processing memory is bounded.
- Channel changes and all upstream changes invalidate immediately and use the
  accepted race-safe supersession/close handshake.
- The selected panel is a binned time-by-value density with absolute alignment,
  fixed scientific value mapping, honest validity, area-weighted density mass,
  labelled brightness, and no retained row-major stripe raster as its permanent
  view.
- One selected-channel overlay seam presents both Intensity and Change energy;
  it reads the current retained slice, uses the selected panel's exact mapping,
  is identity-gated to the video frame actually displayed, remains spatially
  aligned, clears on channel-specific invalidity or stale/late state, and
  contains no threshold semantics.
- Channel color composites below the independent accepted grid overlay, and
  neither presentation toggle invalidates or computes science.
- Overlay rendering is display-bounded, preserves partial-cell geometry, and
  has measured preparation/paint/end-to-end cost without a severe playback
  regression.
- Headless numerical, context, Gaussian, partial-grid, resource, lifecycle,
  offscreen GUI, and existing regression tests pass.
- The user has visibly validated and accepted the milestone.
- Static filtering, Morlet processing, detection, whole-asset execution,
  persistence, and milestones 8 onward remain absent.

Stop here. Static value filtering requires its own accepted handoff and is not
authorized by completion of Change energy.
