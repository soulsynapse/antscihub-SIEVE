---
title: Surrogate calibration for the detection threshold
status: deferred
serves: [A3]
gated_on: >
  the temporal chain settling — concretely, the first parameter set somebody
  wants to run over a whole video and report
reads:
  - src/sieve/core/detection.py
  - docs/REFINED-VISION.md
---

# Surrogate calibration for the detection threshold

**Why not now.** It calibrates a chain whose final shape is still being decided —
`docs/REFINED-VISION.md`'s temporal section produced four items that each
change what is being
thresholded, and a null distribution computed for a chain that then grows a node
is a number that quietly stops meaning anything. It is also genuinely useless
before the accuracy question — the deferred **Annotation spans** item,
docs/todo/annotation-spans.md — has *any* answer: a calibrated
threshold that nobody can check against a labelled event is rigour pointed at an
unknown.

**What would make it the right time.** The temporal chain settling — concretely,
the first parameter set somebody wants to run over a whole video and report.
That is the moment the threshold stops being a slider position and becomes a
claim.

**The problem it solves**, which is easy to not notice because it looks like a
result. Thresholding a few hundred blocks across a few thousand frames is on the
order of a million tests, so the expected false-positive count is proportional to
blocks × frames: **the same settings on a longer clip, or on a finer grid,
produce more detections for no biological reason.** A user comparing a 10-minute
recording against a 30-minute one under identical settings sees more behaviour in
the longer one and has no way to tell how much of that is arithmetic. This is the
same class of failure the deferred **Coverage and detection lanes** item,
docs/todo/coverage-and-detection-lanes.md, exists to prevent, arriving through
the threshold instead of through the palette.

**The remedy is already half-built.** The size-and-duration filter REFINED-VISION
describes is cluster-extent inference — the instrument fMRI settled on (Worsley
and Friston's random field theory; Benjamini–Hochberg FDR is the other branch).
What is missing is its null distribution, without which "size threshold 12" is
tuned until the output looks right, which is exactly the circularity the method
exists to avoid.

**Why it is cheap here, which is the argument for eventually doing it.**
Circularly shift each block's time series by an independent random offset (or
phase-randomize it): real spatiotemporal events are destroyed while each block's
marginal distribution and the spatial correlation structure survive. Run the
*existing* gate and attribute filter on the surrogate, take the largest cluster,
repeat a few hundred times, read the threshold off the 95th percentile. The
surrogate is just a different input array, so this reuses the entire detection
chain — the implementation is a loop and a percentile, not new mathematics.

This is the single item in the doc tree most likely to make SIEVE's output
defensible in review, which is why it is written down now rather than when
somebody asks for it.

Read: `src/sieve/core/detection.py`, `docs/REFINED-VISION.md` **D**.
