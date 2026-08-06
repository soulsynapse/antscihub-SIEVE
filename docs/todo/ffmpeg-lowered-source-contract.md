---
title: FFmpeg lowered source contract
status: open
opened: 2026-08-06T04:43:32-07:00
priority: high
gated_on: nothing structurally
reads:
  - docs/findings/2026.08.06-working-frame-before-python-buys-the-cold-fill.md
  - src/sieve/decode/reader.py
  - src/sieve/decode/prefetch.py
  - src/sieve/decode/identity.py
  - src/sieve/pipeline/cache_key.py
  - src/sieve/pipeline/dag.py
  - src/sieve/pipeline/executor.py
  - src/sieve/pipeline/plan.py
  - src/sieve/filters/crop.py
  - src/sieve/filters/downsample.py
  - src/sieve/filters/rescale.py
  - src/sieve/gui/concurrency.py
  - src/sieve/mutual/shares.py
  - ../antscihub-optical-flow-detector/core/video.py
# Optional, both machine-read. Uncomment what applies:
after: [frame-shrinks-before-bgr]
# serves: [A1]    # the docs/ASPIRATIONS.md capability this walks toward
---

The measurement says the route is worth building: the reference full-window
fill falls from about 6.9 s to about 1.6 s when FFmpeg crops, area-scales, and
emits gray working frames before Python sees them. What is missing is the
source contract that makes that fast path honest.

Done means SIEVE has a source path that can feed the executor with frames that
were never materialized in Python at source resolution, and every semantic
change is visible in identity. This must not be a hidden replacement for
`VideoReader`: the lowered route changes pixels, maybe dtype, and certainly
the work already represented today by the root crop/downsample or rescale
prefix. A cache key for the resulting root must include the lowered route and
the lowered prefix, or refuse to lower.

The safe first implementation is narrower than "FFmpeg can crop anything."
Only a root-side crop whose coordinates are still source pixels can lower into
the decoder. A crop after a scale indexes that scaled frame, and lowering it
against the source would move the box. FFmpeg crops legal odd-origin v2 ROIs
only with `exact=1`; omitting it is a correctness bug even when the reference
ROI happens to be even.

The subprocess is also a new consumer of cores and memory. The implementation
must declare or cap its share under the rule-5 ledger before the GUI can use
it, because FFmpeg's default scaler can consume many cores outside the existing
preview worker count.

Regression checks should fail if:

- a lowered route and the current OpenCV luma route share a source key;
- an odd-origin ROI lowers without `exact=1`;
- a non-root or post-scale crop is silently lowered;
- the GUI can start the FFmpeg route without a declared worker/memory share;
- the reference preview route no longer reaches working-size frames before
  Python.
