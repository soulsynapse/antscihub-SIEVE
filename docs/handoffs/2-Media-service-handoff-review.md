# Review — 2 Media-service performance hints

Status: architectural and benchmarking review of
`2-Media-service-handoff.md`.

## Verdict

The media-service handoff is fundamentally safe and captures the right oracle
lessons:

- Treat oracle mechanisms as hypotheses rather than instructions.
- Establish correctness before optimizing.
- Measure service-level decode separately from end-to-end viewer latency.
- Preserve the rational frame/time model, asset identity, cancellation, and
  declared decoder behavior.
- Distinguish sequential reads from random seeks.
- Coalesce obsolete scrub and repaint requests.
- Avoid doing full-source-resolution work for a much smaller display.
- Test one change at a time and retain only measured improvements.
- Do not assume that visible player lag is necessarily decoder lag.

Those principles are compatible with the rewrite's existing `MediaSession`,
asset, derivation, and player boundaries, and with the intended future
separation between display and scientific processing. The rewrite does not yet
have a channel-processing worker or an established scientific frame-consumption
contract, so this review must not imply that one already exists.

The handoff should be clarified before implementation so that a performance pass
does not accidentally create a new product subsystem or make the headless media
service UI-shaped.

## Repository requirement: every retained performance change needs a finding

The repository's `AGENTS.md` makes the benchmark and reporting workflow
mandatory:

1. Benchmark the relevant behavior before changing it.
2. Make the smallest change that addresses the measured behavior.
3. Run the same benchmark afterward.
4. Report the before/after comparison under `findings/`.
5. Add the report to `findings/.index.md`.

Every report must begin with a BLUF, include the detailed setup, measurements,
comparison, and interpretation, and contain a section titled:

```text
Potential ways this finding could be invalid now or later
```

The handoff's general instruction to record results is therefore not sufficient
for this checkout. Creating `findings/` and `findings/.index.md`, if still
absent, is part of the first benchmark-report change rather than a reason to
invent another reporting location.

## Important correction 1: reusable benchmarks are product diagnostics

The handoff suggests:

```powershell
sieve media benchmark ASSET --mode service --json
sieve media benchmark ASSET --mode viewer --offscreen --json
```

The project has deliberately decided that a reusable benchmark which helps a
user estimate responsiveness, runtime, throughput, or feasibility is a product
diagnostic. Its measurement logic belongs in an importable package module and
should be reported through a supported CLI or UI surface.

Use `scripts/` only for disposable hypothesis tests, one-time investigations,
fixture construction, or thin development launchers around package-owned
measurement logic.

For this milestone:

- Expose the reusable headless estimate through `sieve media benchmark`.
- Provide useful human output and versioned JSON output.
- State whether the native or capped display representation was measured.
- Report estimated frame capacity and realtime factor without claiming that a
  short benchmark predicts every future workload.
- Keep Qt viewer instrumentation in an importable GUI module until a deliberate
  UI diagnostics surface exists; do not import Qt into the headless CLI.

Do not run an expensive benchmark automatically during application startup.
Explicit user invocation is appropriate. Cheap, cached results may be shown in
the UI later if their provenance and age remain visible.

## Important correction 2: do not make the media-service API display-specific

The handoff correctly recommends separating:

```text
seek/decode
display resize
color conversion
Qt image construction
paint
```

One hint then suggests requesting a display-ready plane from the media service.
That is safe only if “display-ready” means a declared media plane such as RGB
with explicit color semantics.

Do not make the headless `MediaSession` return:

- `QImage`.
- `QPixmap`.
- A widget-sized raster.
- A Qt-owned buffer.
- An image whose resolution depends implicitly on the current GUI size.

That would couple the headless media contract to one client and could later force
scientific decoding, CLI frame extraction, and GUI display through the same
UI-specific representation.

A safe boundary is:

```text
MediaSession
  returns a declared native/RGB/luma plane with timing and source coordinates

GUI display layer
  chooses display resolution
  performs any GUI-only color/layout conversion
  owns Qt image lifetime

FrameView
  paints the prepared display frame
```

The current checkout performs Qt image ownership directly in `FrameView` and
`IsolatePlayer`; it has no `DisplayAdapter` abstraction. Do not create that
abstraction merely to satisfy this diagram. Extract a shared adapter only if a
measured implementation needs one for reuse, ownership, or testability.

If the backend can efficiently emit RGB or a lower-resolution preview plane, the
request must be explicit and recorded. The full-resolution scientific path must
remain independently requestable and must not inherit a GUI cap.

## Current-checkout correction: persistent sequential decoding already exists

The current `MediaSession` is not reopen-per-frame for adjacent playback. It
keeps one FFmpeg subprocess alive while requests are sequential. When a request
is not the decoder's next expected frame, it terminates the subprocess and starts
a new FFmpeg process with an input-side `-ss` seek.

The baseline should therefore measure the implementation that exists:

- Adjacent frame read through the retained subprocess.
- Random seek including subprocess termination and creation.
- Backward step and loop restart, which take the random-seek path.
- Repeated asset switches, including process and thread cleanup.

Do not schedule "add a persistent sequential decoder" as the first change unless
the baseline shows that the existing mechanism is not actually being retained
through the relevant viewer path.

The existing test proves subprocess identity is retained for frames 0 and 1. It
does not prove random-seek frame accuracy, seek latency on long-GOP footage, or
cleanup under concurrent cancellation.

Both GUI decode-thread owners currently request interruption and then wait up to
three seconds, but they do not assert that the wait succeeded before continuing
session cleanup. The asset-switch benchmark must therefore check the thread-wait
result, FFmpeg process exit, handle count, and absence of a late signal/frame;
elapsed switch time alone is not sufficient evidence of clean cancellation.

## Current-checkout correction: rational calculation does not prove exact seek

`MediaSession.timestamp_for_frame()` calculates timestamps with `Fraction`, but
`read_frame_rgb()` converts the result to a float-formatted decimal before
passing it to FFmpeg's input-side `-ss`.

Preserve the rational application model, but treat the concrete mapping from
requested frame to decoded FFmpeg output as a correctness hypothesis. Verify it
with numbered temporal fixtures and representative variable/long-GOP media. Do
not describe the current random-seek path as frame-accurate solely because its
timestamp was calculated rationally.

## Important correction 3: frame-count verification must not contaminate the
## latency benchmark

The benchmark metadata list currently asks for a verified decoded-frame count.
That count may be unknown in a valid asset sidecar, and obtaining it can require
decoding the entire video.

An open-to-first-frame benchmark that first performs a whole-video frame count
does not measure interactive open latency.

Record:

```text
container/probed extent
decoded-frame extent, when already known
extent status: estimated | measured | verified
source of each value
```

Do not require a full count before:

- Opening the media session.
- Displaying frame zero.
- Measuring ordinary seeks.
- Running the interactive viewer benchmark.

Use a separately prepared verified count when a scenario needs a known final
frame. The cost of producing that count should be reported as its own operation,
not silently included in every viewer open.

Authoritative whole-asset processing may still require verified decodable
coverage later.

## Important correction 4: exact frame hashes are backend-sensitive

The numbered synthetic fixture is an excellent temporal correctness tool, but
exact pixel hashes need a narrower contract.

Different correct decoders can produce slightly different pixels from lossy
video because of:

- Color conversion.
- Range interpretation.
- Chroma upsampling.
- Rounding.
- Backend implementation details.

Use:

- A lossless, deterministic fixture for exact pixel hashes.
- Visible or machine-readable frame numbers for temporal identity.
- Explicit tolerances and declared color semantics for lossy cross-backend
  comparisons.
- Exact equality when comparing before/after implementations that claim
  pixel-identical output through the same backend.

Do not reject a faster backend merely because its lossy RGB result differs by a
small, declared tolerance. Conversely, do not use a tolerant image comparison
when the question is whether seek `N` returned frame `N-1`.

Temporal correctness and pixel equivalence are separate assertions.

## Important correction 5: offscreen viewer timing is not a complete paint
## benchmark

Offscreen Qt is appropriate for:

- Construction and lifecycle tests.
- Seek/supersession correctness.
- Counting decode and paint requests.
- Deterministic interaction tests.
- Catching gross CPU regressions in conversion code.

It is not necessarily representative of:

- Native window-system presentation.
- GPU/compositor behavior.
- High-DPI device pixel ratios.
- Real `QPixmap` upload and blit cost.
- Vsync and timer interaction.

Keep the offscreen benchmark for automation, but add a real-window benchmark or
instrumented manual run for final performance conclusions. Record the platform,
Qt platform plugin, device pixel ratio, window size, and whether the window was
visible, obscured, or minimized.

Do not compare an oracle visible-window measurement with a rewrite offscreen
measurement as though only the code changed.

## Scope correction: distinguish the minimum benchmark from the extended matrix

The full benchmark matrix is valuable, but implementing every scenario, corpus
fixture, latency distribution, resource counter, and public report could become
larger than the player optimization itself.

Define a minimum diagnostic set:

1. One lossless numbered fixture.
2. One representative long-GOP/high-resolution project asset.
3. Open-to-first-frame.
4. Adjacent sequential playback.
5. Fixed-position random seeks.
6. Rapid latest-only scrub.
7. End-to-end request-to-paint timing.
8. Asset-switch supersession and resource cleanup.

Run that set before and after every candidate.

The checkout already contains a representative source MP4 and isolated
replicate child under `test_videos/`. Reuse those in place for the project-media
cases unless inspection shows that their codec or GOP structure does not cover
the hypothesis. Add a small deterministic numbered lossless fixture separately;
do not create another large transcoded corpus merely to satisfy the matrix.

Use the extended set when relevant:

- 120 fps fixture.
- Multiple codec and bit-depth combinations.
- Several loop/keyframe alignments.
- Resize and repaint profiling.
- Hidden-widget overhead.
- Prefetch memory and cancellation.
- Cold/warm cache investigations.

This preserves the handoff's diagnostic quality without turning the benchmark
harness into the milestone's main deliverable.

## Clarification: “cold” must be defined operationally

“Cold asset” can mean:

- A new media-service instance.
- A new application process.
- No decoder state.
- No application cache.
- No operating-system filesystem cache.

Those conditions are not equivalent. Reliably flushing the operating-system
cache may require privileges, platform-specific operations, or disruptive test
setup.

Every result should say which cold conditions were actually established. Do not
label a new decoder over OS-cached media as a fully cold storage benchmark.

For ordinary optimization work, new-process and warm-process measurements are
usually sufficient if described honestly.

## Clarification: latest-only display does not authorize scientific frame drops

The handoff already distinguishes display refresh from scientific coverage. Keep
that distinction structural.

For player playback:

- An obsolete frame may be decoded but not painted.
- A queued, superseded random seek may be cancelled or ignored.
- The displayed cursor must identify the frame actually painted.

For scientific processing:

- Every required frame must be processed or recorded as missing.
- A display optimization must not alter analysis coverage.
- The GUI preview cache must not silently become the scientific decoder source.

Use separate request types or execution paths if necessary. Do not rely only on
a caller remembering whether dropping is allowed.

## Clarification: benchmark request, decode, delivery, and paint counters by
## generation

Simple global counters can become misleading during:

- Rapid scrubbing.
- Loop restarts.
- Asset switches.
- Cancellation.
- Decoder replacement.

Associate measurements with:

```text
asset identity
media-session generation
request id
requested frame
returned frame
request timestamp
decode start/stop
delivery timestamp
paint timestamp
outcome: painted | superseded | cancelled | failed
```

This makes “the final scrub request won” provable and prevents a late result from
being counted as successful merely because some frame eventually painted.

Start with these diagnostics in the benchmark wrapper. Move only the minimum
required timestamps or identifiers into production code when the wrapper cannot
observe a stage accurately. They do not need to become permanent production
logging at full verbosity.

## Clarification: one decode per displayed-frame request is a diagnostic, not a
## universal cache law

The handoff correctly warns against two GUI consumers accidentally decoding the
same frame.

Do not turn that into a universal assertion that every frame index may be decoded
only once:

- Different declared output planes may require different decode/conversion
  work.
- A decoder may legitimately revisit a frame after a backward seek.
- Independent media sessions and scientific jobs are separate consumers.
- A failed or cancelled request may be retried explicitly.

The narrower invariant is:

> Within one media-session generation and one resolved display request, adding
> passive GUI consumers must not cause an unintended duplicate decode of the
> same requested representation.

## Current-checkout decision: the two workflow tabs intentionally own separate
## media sessions

The current main window constructs both Replicates and Isolate immediately. Both
listen to the shared active-asset controller, both open their own
`MediaSession`, and both request frame zero when the active asset changes. The
existing GUI test explicitly waits for both images.

That is not the same failure mode as two passive consumers accidentally decoding
twice inside one media-session generation. It is the current independent-tab
lifecycle, and changing it could alter tab responsiveness and state isolation.

Before treating the second first-frame decode as waste, decide which lifecycle
is intended:

- Both tabs eagerly retain independent sessions and initial frames.
- The inactive tab opens its session but defers decode until activation.
- The inactive tab opens both session and first frame lazily on activation.
- An inactive tab closes its session and restores only independent UI state when
  reactivated.

Benchmark the selected lifecycle end to end. Do not share a mutable decoder
between the tabs merely to remove the duplicate, and do not silently make tab
activation expensive without measuring that tradeoff.

The hidden-view benchmark should report the two sessions separately. Within each
session, hidden widgets should not schedule repaint work. Across sessions, any
decode performed by the inactive workflow should be classified as intentional
eager initialization or as avoidable hidden-view overhead according to the
chosen lifecycle.

## Clarification: display-resolution reduction needs an explicit cache key

If the rewrite retains a downscaled display frame, its identity should include:

```text
asset/content identity
absolute frame index
requested media plane and color interpretation
source crop, normally full frame
display resolution policy
device pixel ratio where applicable
conversion implementation/version if persistent beyond the session
```

For an in-memory one-frame cache, not every field needs to be serialized, but the
implementation must invalidate on the corresponding changes.

Do not reuse:

- A frame from the previous asset.
- A parent frame for a child asset.
- A differently interpreted color plane.
- A low-resolution overview as native-detail pixels.

## Clarification: prefetch evidence belongs to scientific extraction, not the
## player baseline

The handoff already warns that the oracle's prefetch result came from a
scientific extraction benchmark. Strengthen the implementation priority:

1. Baseline the existing persistent sequential decoder.
2. Optimize that path only if its measured behavior warrants a change.
3. Latest-only scrubbing.
4. Duplicate decode/repaint removal.
5. Display-resolution and conversion profiling.
6. Only then test viewer prefetch.

Do not introduce a producer thread merely because it improved a different
workload. If viewer prefetch is tested, include shutdown, queue invalidation,
memory, and loop-seek behavior in the before/after comparison.

## Decisions that are safe as written

### The oracle is explicitly non-authoritative

The repeated requirement to benchmark before and after is appropriate. It
prevents historical measurements from becoming universal thresholds.

### Persistent session and sequential-read hints

These are already present in the existing `MediaSession`: adjacent reads retain
one FFmpeg subprocess, while non-adjacent requests replace it. The hints remain
safe as benchmark hypotheses and do not require copying the oracle's OpenCV
wrapper.

### Scrub coalescing and generation checks

These are durable interaction requirements independent of decoder choice.

### Separating service and viewer timings

This is essential. It protects the media service from absorbing overlay, plot,
Qt conversion, or paint responsibilities merely because the combined viewer is
slow.

### Display-resolution work remains display-only

The handoff explicitly forbids feeding reduced display pixels into scientific
computation. Preserve that language.

### Frame conversion outside `paintEvent`

Caching a prepared frame representation under an explicit identity is a safe
display concern. The warning about Qt buffer lifetime is important.

### Hidden visuals skip display work only

The handoff correctly says that visibility must not control authoritative model
or scientific state.

### Oracle shortcuts are called out

The warnings against copying float fps, a silent 30 fps fallback, container count
as truth, quick hashes, and implicit backend behavior align with the rewrite's
stronger contracts.

## Risk classification

### Potentially expensive if left ambiguous

1. Leaving a reusable user-facing estimate stranded in a developer script with
   no supported human or machine-readable product surface.
2. Returning Qt/widget-sized representations from the headless media-service
   contract.
3. Requiring a full decoded-frame count before measuring or displaying the
   first frame.
4. Treating exact pixel hashes as portable across lossy decoder backends.
5. Drawing final conclusions about visible playback solely from offscreen Qt
   timings.
6. Treating the two tabs' independent media sessions as an accidental duplicate
   without first choosing the intended inactive-tab lifecycle.

### Scope risks rather than architecture failures

1. Building the entire extended benchmark matrix before diagnosing the obvious
   slow path.
2. Adding prefetch before proving the simpler sequential path.
3. Adding a large frame cache before measuring revisit behavior.
4. Instrumenting permanent production code more heavily than the benchmark
   requires.
5. Creating a `DisplayAdapter` class solely because this review used it in a
   boundary diagram.
6. Running expensive diagnostics automatically during ordinary application
   startup instead of requiring explicit user action.

### Correctly deferred

1. Scientific channel decoding and requested-plane planning.
2. Processing-worker throughput.
3. Overlay and channel-panel optimization beyond isolated diagnostic timing.
4. Persistent frame caches.
5. Hardware decode.
6. Cross-platform numeric performance thresholds.

## Recommended disposition

Keep the media-service handoff's overall structure and oracle hints.

Before giving it to an implementation agent:

1. Require every retained performance change to produce the mandated BLUF-first
   report under `findings/` and an entry in `findings/.index.md`.
2. Put reusable measurement logic in package modules, expose the headless media
   estimate through `sieve media benchmark`, and reserve scripts for disposable
   work or fixture construction.
3. Keep Qt and widget-dependent display work in the GUI layer rather than
   `MediaSession`; do not require a new adapter abstraction.
4. Benchmark the existing retained FFmpeg subprocess for adjacent reads and its
   subprocess-replacement path for random seeks before proposing decoder work.
5. Preserve rational application timing while independently verifying the
   concrete FFmpeg frame returned by random seeks.
6. Record frame-count status without requiring a full count for viewer startup.
7. Restrict exact hashes to deterministic lossless fixtures or same-backend
   equality claims.
8. Require a visible-window measurement before final viewer conclusions.
9. Separate the minimum diagnostic benchmark from the extended matrix and reuse
   the existing project footage where appropriate.
10. Decide whether inactive workflow tabs should eagerly open and decode before
    classifying the current second session as redundant.

No broader redesign is justified before baseline measurement.
