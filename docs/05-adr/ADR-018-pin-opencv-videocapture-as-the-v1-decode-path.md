# ADR-018: Pin OpenCV VideoCapture as the v1 decode path

Reference for Architecture Decisions Record: https://docs.arc42.org/section-9/

## Context

`ARCHITECTURE.md` §12 places the decode library and its version inside the
code-version hash that contributes to cache keys, which means the decoder is a
pinned identity rather than an implementation detail. §14 describes
`io/video_read.py` as "dtype-preserving decode". §5.5 makes index-based
scrubbing — nearest keyframe plus a short forward decode — the mechanism behind
the sub-50 ms scrub budget. [STABLE] Those three statements were written before
a decoder had been measured.

[STABLE] The measurement now exists. `src/sieve/bench/decoder_benchmark.py`
compared PyAV, decord, imageio-ffmpeg, and OpenCV VideoCapture over H.264
8-bit, H.264 10-bit, H.265, VP9, and ProRes 422 HQ, with results at
`tests/results/decoder-benchmark-final/`. It applied a hard gate: a failed or
pixel-mismatched random seek on a codec disqualifies a backend for preview
extraction, on the reasoning that a scrub landing on the wrong frame is a
correctness failure the user does not see and does not work around.

[STABLE] The corpus separates the candidates cleanly, and not along the axis
the architecture assumed. PyAV, decord, and imageio-ffmpeg each failed seek
accuracy on H.265 — roughly one request in ten landed on a mismatched frame.
OpenCV VideoCapture was the only backend with no mismatches across the corpus.
OpenCV is also the only candidate that does not preserve source bit depth: it
delivers uint8 BGR, so 10-bit H.264 and ProRes 422 HQ lose depth at the decode
boundary. Backends that preserve depth fail the seek gate, and the backend
that passes the seek gate discards depth.

[STABLE] No single decoder therefore satisfies both halves of what the
architecture describes. The two properties are not equally load-bearing, and
the decision turns on which one the product's stated value actually rests on.

## Decision

[STABLE] `io/video_read.py` uses OpenCV VideoCapture as the single decode path
for v1, serving both display and executor frame input. It is the sole decode
boundary; other layers do not open video files directly.

Reasoning against the architecture's own priorities, in the order the
architecture ranks them:

Seek accuracy is load-bearing and bit depth currently is not. The tuning loop
is the product, and index-based scrubbing is the mechanism that makes it feel
like a video editor. A decoder that lands on the wrong frame corrupts the
representative clip, the replicate range, and every downstream measurement,
silently. Bit-depth loss, by contrast, is a bounded and visible reduction in
input precision that costs nothing on the 8-bit footage the tool's user stories
centre on — recordings poor enough that other programs reject them.

Determinism and dtype honesty are aspirational at this stage rather than
load-bearing. [ASSUMPTION] No accepted filter yet depends on more than 8 bits
of input precision, and no user footage in scope has been shown to lose
recoverable signal at uint8. This assumption is the decision's load-bearing
weakness and is the thing to re-test, not the throughput numbers.

A second decode path would be a second decoder before there is a second caller.
The dtype-honest path only becomes meaningful when the executor pulls frames
for filter input, which does not yet happen. Building both now would pay the
cost of two pinned identities, two cache-key contributions, two seek
behaviours, and two sets of codec edge cases in exchange for a capability
nothing consumes.

[STABLE] Decoder identity — library, version, and the backend VideoCapture
resolves to — participates in the code-version hash that contributes to cache
keys, as §12 requires. Recording it while there is one decoder is what makes
adding a second one later a clean invalidation rather than a silent one.

[STABLE] The bit-depth reduction is reported rather than hidden. The decode
boundary exposes both the source's native bit depth and the dtype it delivers,
and those values can differ. Provenance for a run records both. A user opening
10-bit or ProRes footage is told that decode is delivering 8-bit, at the point
of opening rather than in a document.

[INTENT] `ARCHITECTURE.md` §14's description of `io/video_read.py` as
"dtype-preserving decode" no longer describes the implementation and is amended
to describe a seek-accurate decode boundary that reports its dtype reduction.

## Reopening conditions

[STALE WHEN] Any of the following holds, at which point this ADR is superseded
rather than amended:

- an accepted filter's signal demonstrably depends on more than 8 bits of input
  precision;
- user footage appears where the uint8 reduction costs measurable detection,
  tested rather than assumed;
- a seek-then-decode-forward strategy is shown to make a depth-preserving
  backend pass the seek gate — this is the most likely path to reopening, since
  the disqualified backends failed on raw seeks rather than on decode, and the
  mitigation was not attempted before the gate was applied; or
- the seek gate itself is found to be corpus-specific rather than a property of
  the backends.

[OPEN QUESTION] Whether the H.265 seek failures reflect the backends or the
generated corpus. The corpus is synthetic and deterministic, which makes the
comparison fair between backends but does not establish that real-world H.265
behaves the same way.

## Alternatives considered

### PyAV as the pinned decoder

PyAV preserves native dtype and format on every codec in the corpus, has the
smallest install closure and lowest memory use, and gives direct access to
frame-level metadata. It failed the seek-accuracy gate on H.265. Its
sequential throughput is also the lowest of the four, which matters for the
background replicate materialization described in §5.5.

### decord as the pinned decoder

decord had the highest sequential throughput by a wide margin and is designed
for the random-access pattern scrubbing needs. It failed the seek gate on
H.265, loses depth on 10-bit and ProRes anyway, and carries the highest memory
use of the four. It offers no property that survives its disqualification.

### imageio-ffmpeg as the pinned decoder

Small closure and no transitive dependencies, but it failed the seek gate on
H.265 and delivers uint8 rgb24 regardless of source depth. It is disqualified
on accuracy while offering none of the depth preservation that would justify
the risk.

### Two decode paths, split by role

A seek-accurate path for display and a dtype-honest path for executor input is
the shape this decision would take if bit depth were load-bearing. It is the
expected outcome of the reopening conditions above. Adopting it now would
require the filter-input path to exist before any filter does, and would pin
two decoders whose disagreement on frame identity is itself a determinism
problem — the display and the executor could be looking at different frames.

### Deferring the decision

Leaving the decoder unpinned would let the pre-pipeline loop be built against
whatever is convenient. §12 makes decoder identity part of cache identity, so
an unpinned decoder means unpinned cache keys, and the deferral would have to
be undone before the first cached result rather than at leisure.

## Status

Accepted.

## Consequences

- SIEVE v1 carries one decoder, one pinned identity, one set of codec
  behaviours, and one seek implementation to test.
- OpenCV is already required by the processing layer under ADR-001, so decode
  adds no new top-level dependency.
- Sources with more than 8 bits of depth are reduced at the decode boundary.
  The reduction is reported at open time and recorded in run provenance rather
  than being discovered later in a document.
- Frame identity is consistent between display and executor input, because both
  read through the same decoder.
- The decoder's version participates in cache keys, so a decoder upgrade
  invalidates cached results. This is intended and is the cost of §12's
  determinism commitment.
- Adding a depth-preserving path later is a superseding ADR plus a second cache
  identity, not a rewrite of the decode boundary, provided callers continue to
  go through `io/video_read.py`.
- The seek-then-decode-forward mitigation remains untested. Until it is tried,
  the disqualification of three backends rests on their raw-seek behaviour
  rather than on their best achievable behaviour.
- `ARCHITECTURE.md` §14 requires amendment; its current wording describes a
  property the implementation does not have.

## References

- [SIEVE decoder benchmark harness](../../src/sieve/bench/decoder_benchmark.py)
- [Decoder benchmark results](../../tests/results/decoder-benchmark-final/README.md)
- [SIEVE architecture: the pre-pipeline loop](../04-architecture/ARCHITECTURE.md#55-the-pre-pipeline-loop)
- [SIEVE architecture: determinism policy](../04-architecture/ARCHITECTURE.md#12-determinism-policy--criteria)
- [SIEVE architecture: component decomposition](../04-architecture/ARCHITECTURE.md#14-component-decomposition)
- [OpenCV VideoCapture documentation](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html)
- [ADR-001: Use PySide6 for the user interface](ADR-001-use-pyside6-for-the-ui.md)
