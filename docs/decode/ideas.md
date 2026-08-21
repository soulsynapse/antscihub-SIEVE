# Decode — ideas and possible failure modes

Not findings. Nothing here is settled, nothing here is measured in this tree,
and the order is not a ranking. It is the residue of one session's reasoning,
kept so the next one argues with it instead of rederiving it. An item that gets
measured leaves this file for `docs/findings/`; an item that gets decided leaves
for `docs/adr/`. Numbers appear only with the build and footage that produced
them, and are cited to where they live rather than restated as true.

## Good ideas

- Measure PyAV against OpenCV on the same file before anything else. Most of the
  v2/v3 decode corpus is OpenCV 4.13, and several of its findings are plausibly
  properties of that binding rather than of video.

- Take the Y plane and never convert what is not displayed. `grab()` is the
  decode and `retrieve()` is a single-threaded colour conversion; in libav the
  plane is simply there. v3's `decode/reader.py` already has the `luma=True` path.

- Run the whole display path at display size, not just the decode. v1's
  `DISPLAY_MAX_W` covers the copy, the mask upscale, the blend and the convert,
  and the pixels it saves were being computed and then thrown away.

- One decode serving every consumer, rather than a decoder per panel. v1
  centralised this in `AppState`; v2 and v3 did not, and v2 then measured the
  contention as a finding it left open.

- Discard rather than queue when requests outrun the decoder. Worth keeping even
  if the seek gets cheap, since the discarded frames were never going to be seen.

- Grab forward instead of seeking for short jumps. Cheaper, and it lands on the
  exact frame rather than wherever the container index rounds to.

- Cut the source once into a small intermediate. Decode cost tracks pixels, not
  bytes, so a lossy cut buys almost nothing a lossless one does not.

- Make that intermediate intra-only and the seek problem stops existing. FFV1 has
  no inter-frame prediction, so a random frame costs an index lookup and one
  decode. This is why NLEs cut ProRes and DNxHR proxies. Note that v1's default
  quality is CRF-based and therefore does *not* have this property.

- GoPro's own CineForm is an intra-only wavelet codec built for this workflow,
  which is worth a look given both the footage and the signal ops.

- Build the keyframe index by demuxing only — read packets, check the keyframe
  flag, decode nothing. Seconds on a 60 Mbps file, and it retires "the GOP is
  variable so we cannot know" entirely.

- Let a frame request carry a *set* of indices, not one. Sorting a batch by
  keyframe and decoding it together is decord's whole technique, and a
  one-at-a-time protocol cannot express it.

- Price the hardware-decode download rather than assuming it erases the win. A
  full-resolution luma plane is on the order of sixteen megabytes; that copy is
  small next to a CPU colour convert.

- Pool buffers before concluding anything about thread scaling. The measured
  ceiling past a handful of workers was diagnosed as allocator page faults from a
  fresh full-resolution array per read, which is what `AVBufferPool` exists to
  remove.

- Reduce as early in the chain as the question allows. What is being conserved is
  passes over hot memory, and the span over which full frames are live is the
  thing to shorten.

- The reduction and the layout transposition are the same event. Everything
  upstream of it streams in presentation order, which codecs are good at;
  everything downstream reads time-columnar, which they are terrible at. A
  reduced per-frame series is already time-major.

- Chunked array storage for the time-columnar half. v3 already named Zarr for
  this in `pipeline/cache.py`.

- Motion vectors come out of the stream for free, and per-frame packet size comes
  out without decoding at all. Both are motion signals the encoder already paid
  for.

- A keyframe-only pre-pass into a filmstrip, for scrubbing before any cut exists.
  This is what the streaming services do with storyboard sprites, and the gesture
  at that stage is "roughly where," not "which frame."

- The viewer reports intent and never policy. A drag is a guess, a release is a
  commitment, a playback tick is neither; every adaptive behaviour downstream
  reads that, and none of them need the viewer changed.

- Keep the frame protocol Qt-free, so the bench and the canvas are two consumers
  of one thing rather than the bench inheriting a GUI.

- Compose policy rather than configure it: a caching source wrapping a decoding
  source, a coalescing source wrapping that. The bench's matrix becomes which
  stack of wrappers, and no backend reimplements caching.

- Derive the protocol from two backends at once, one synthetic and one real. A
  protocol written from a single implementation is that implementation wearing an
  interface's clothes.

- The synthetic backend earns its place twice: it is also how the canvas gets
  tested against injected latency, drops and out-of-order arrival, with no codec
  involved.

- Measure end to end, request to pixels on screen. Source-only numbers reward a
  backend that pushes its conversion into the canvas.

- Run the bench factorial rather than one factor at a time, and make contention a
  first-class workload. The known failure is a toggle that wins alone and loses
  while another consumer runs.

- Emit per-run time series rather than summary statistics. A run that averaged
  forty because it ran at sixty and then stalled is a different thing, and the
  stall is usually the finding.

- An invisible view is not a consumer. v1 found a hidden tab's panel still doing
  full decode-scale-repaint cycles on every frame step.

- Playback should not fill the scrub cache. It walks the whole timeline and
  evicts exactly the frames someone returned to.

- Source frame indices are authoritative everywhere — marks, coverage, keys, the
  scrub bar. A clip's frame zero is the source's frame N, and that mapping is the
  source's business rather than anybody else's.

- Keep the cut reversible. Crop and luma forecloses only colour and the region
  dropped; a threshold baked into the stored file forecloses every question but
  one.

## Possible failure modes

- Measuring a binding and concluding about a codec. Every decode number currently
  in this tree's ancestry is OpenCV 4.13.

- Designing a subsystem to defend a budget that turns out to be an artifact. The
  scrub policy, the coalescer, the request intents and the proxy cache all exist
  to survive a seek cost that may not survive a library change.

- Concluding hardware decode does not help because it did not engage in one
  build. That is a fact about the build, not about decode.

- Trusting any single-consumer measurement. v2 measured a pipeline made 1.88x
  faster making playback worse, and left that finding open.

- One-factor-at-a-time sweeps. The known failure is an interaction, and OFAT
  reports the main effect and ships it.

- A protocol shaped by whichever backend was written first. Watch for three
  things it then cannot express: a batch of indices, a GPU frame handle, and a
  backend that can only go forward.

- Normalising format and size inside the protocol, which hides exactly the
  differences the bench exists to expose.

- Zero-copy GPU display and arbitrary numpy script steps are in tension. The
  moment a user's step wants an array, the download erases what zero-copy bought.

- Intra-only costs storage, and the saving is not free. Lossless must encode
  inherited compression noise verbatim, and noise does not compress.

- Baking a task parameter into the stored file. It is what makes TRex's format
  two orders of magnitude smaller and what makes it answer exactly one question.

- Coverage inferred from a zero. An unwritten frame and a frame measured as empty
  read identically, and every consumer added later is one that does not know to
  check.

- Writing a filter's response at a window's edge and masking it at display. The
  value still exists for anything that does not mask, and a later overlapping
  window supplies the honest one, so there are then two answers for one frame.

- A cache key taken over the whole enabled graph. A display or a sibling branch
  pulling a requirement into the join then invalidates work whose own inputs
  never changed.

- Excluding a parameter from a key on the grounds that its own step retains
  nothing. Keys fold ancestry, so the exclusion propagates to descendants that do
  cache; the property holds at the leaves and is easy to state as general.

- There is no conservative default for temporal extent. Retention defaults safely
  to none and requirements to maximal, but unbounded extent is unschedulable
  rather than slow, and zero is a guess rather than a bound.

- Clip-local frame numbering. v1 hit the corresponding bug class when two
  replicates wrote to one sidecar and the second destroyed the first, silently.

- Rebuilding what exists. Proxy workflows, filter graphs with format negotiation,
  and frame-accurate seeking against an index are all solved; being able to say
  in one sentence why each is not being used is the test.

- Treating decode as the goal rather than the substrate. The part with nothing to
  buy is the memoisation and scheduling layer, not the decoder.

- Abandoning the findings corpus at each rewrite. v2 and v3 hold roughly a
  hundred notes between them and this tree started with none, which is the
  mechanism by which the same measurements keep being rediscovered.

- Adding decode threads past the measured peak, which was worse than a single
  thread on a thirty-two core machine, and can be actively harmful under
  contention.

- Expecting spatial downscale inside the decoder. `lowres` never worked for H.264
  or HEVC, because approximate reconstruction drifts through the prediction loop.
  Anything advertised as downscale-during-decode is almost certainly post-decode
  subsampling.

- Treating a codec's residual pyramid as a wavelet decomposition. The partition
  is chosen by rate-distortion optimisation and the quantisation follows the
  bitrate, so the scales are not a stable basis and coefficients do not compare
  across frames. Motion vectors are the part of that idea which is real.

- Snapping scrub targets to keyframes when the GOP is variable. The spacing goes
  irregular and the landing becomes unpredictable; a fixed time grid is stable,
  and stable is what makes it cache.

- A forbidden-import test for a module that does not exist yet. It passes for the
  wrong reason and goes on passing.

- Carrying numbers across files. The footage in play now is not the one the v2
  and v3 measurements were taken on, and shares only its geometry.
