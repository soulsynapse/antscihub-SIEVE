# decode-experiments

Where SIEVE finds out what decode actually costs, on its own footage, on this
machine. Every result lives in `results/` as JSON, and every result carries the
build, the machine and the probed footage that produced it.

## Why this exists

SIEVE's product constraint is an interactive tuning loop — drag a slider, watch
the graphs refill faster than the video plays — and most of what this tree
believes about decode was inherited rather than measured here. The numbers it
inherited (a seek costing tens of milliseconds with no tunable knob, a colour
conversion costing more than the decode, thread scaling that peaks at a handful
of workers, hardware acceleration not engaging at all) were all taken through
**OpenCV 4.13**. Several of them are plausibly properties of that binding rather
than of video, and subsystems in v2 and v3 were built to defend budgets they
set.

So the first job here is not optimisation. It is finding out which of those
numbers survive a library change, because that decides which of those subsystems
SIEVE needs at all.

`docs/decode/ideas.md` holds the candidate wins and the suspected traps this is
meant to test. Nothing there is measured; the point of this folder is to move
items out of it.

## The rule for a result

A result names what was measured, on what footage, on what build, on what
machine — `harness.py` attaches all four, so no experiment has to remember. It
keeps every per-iteration sample rather than a summary, because a run that
stalled halfway and a run that was uniformly slow have the same mean and are not
the same finding. Quantiles are computed when a result is read.

A case that could not run says so in the result's notes. A silently absent case
reads as a case that came out equal.

Results are committed. They are small, and a measurement whose predecessor was
deleted cannot supersede anything.

## What to measure, and roughly in what order

Ranked by how much each would change the architecture rather than by how
interesting it is:

1. **PyAV against OpenCV**, same file, sequential decode, with the grab/retrieve
   split and luma against BGR. This one comparison retires or confirms most of
   the inherited corpus.
2. **Random access**: seek-to-target against grab-forward, as a function of jump
   distance, per backend. Produces a crossover threshold instead of a guess.
3. **The cut**: the same region as an intra-only clip (FFV1), an inter-coded clip
   (CRF), and cropped-after-decode from the original — measured both sequentially
   *and* at random frames, since the intra-only claim is that random access stops
   costing anything.
4. **Pushdown**: crop, scale and gray through a libavfilter graph against the same
   thing in numpy afterwards. Compare wall time *and* output difference; do not
   assume they are bit-identical.
5. **Contention**: a second consumer decoding while the first is timed. Every
   single-consumer number is suspect until this runs, because v2 measured a
   pipeline made faster making playback worse.

Run them factorial where they interact rather than one factor at a time. The
known failure is a toggle that wins alone and loses while another consumer runs.

## Footage

`video-tests/` at the repo root, gitignored by size. Probe it, never trust a
figure written down here — but as of writing, the two files are **not the same
source**, which matters for any experiment comparing a cut against its original:

- `GX010047c2_02_17_26.MP4` — HEVC Main, 5312x2988, 23.976 fps, 11328 frames
- `rep3_intermittent_crop.MP4` — H.264 High, 462x456, 59.94 fps, 30579 frames

An experiment that wants a cut of the 5.3K source has to make one.

## Running

Decode libraries are not SIEVE runtime dependencies and should not become them.
They live in a dependency group:

    uv run --group experiments python experiments/decode-experiments/<name>.py

## The other decode-experiments

There is a **separate repository** of the same name, and it is not this one:

    ~/Documents/Code/decode-experiments

That one is a survey — an Obsidian vault of what other tools do to get frames
out of a file, with the upstream source already checked out. It holds findings,
problems and questions as front-mattered notes, a linter, and roughly forty
vendor checkouts under `vendor-code/`: FFmpeg, torchcodec, decord, DALI, dav1d,
mpv, libplacebo, GStreamer, FFCV, TASM, LightDB, NoScope, BlazeIt, PySceneDetect,
mv-extractor, pytorch-coviar, suite2p, SLEAP, TRex and others. Its test footage is
the same 5.3K HEVC file.

The division is that one reads and this one runs. That repo answers *what does
some tool do and what does it assume*; this folder answers *what does it cost
here*. Its own conventions distinguish a fact read off source from one observed
at runtime, and at the time of writing every claim it holds about a decode path
is `code-read` — which is the gap this folder exists to close from the other
side.

Read it before designing an experiment. Several of the mechanisms worth measuring
are already characterised there in detail, and re-deriving one from the source is
the expensive way to start.
