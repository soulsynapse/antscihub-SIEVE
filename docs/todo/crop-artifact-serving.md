---
title: Serving the crop artifact
status: open
opened: 2026-07-28
gated_on: >
  docs/todo/crop-artifact-writer.md landing first — same trigger, back half;
  take the three crop items in order
reads:
  - docs/todo/crop-artifact-writer.md
  - docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md
  - src/sieve/pipeline/executor.py
  - src/sieve/pipeline/plan.py
  - src/sieve/gui/preview_runner.py
---

# Serving the crop artifact

Once a replicate is backed by an artifact, every render of that replicate
decodes the artifact instead of the parent. On the reference clip that is
9.93 → 0.093 ms/frame of decode, and the bandwidth-wall contention
(docs/findings/2026.07.27-decode-is-a-bandwidth-wall-shared-by-two-consumers.md)
stops applying to any consumer the artifact serves.

## The shape of the change

Under the child-source model (settled in the writer item) the executor,
`plan.py`, and `cache_key.py` are **untouched**. The artifact is a source
video: runs against it use `source_identity(artifact_path)` for the root,
`roi=None` (the crop already happened), and the ordinary decode-format flag.
All work lives in the *callers* that pair a source path with an ROI today —
one resolution step, used by every front end:

- **`src/sieve/pipeline/resolve_source.py`** (new; name free): given the
  project, its directory, and a replicate, return which file to open and
  which ROI to pass — `(parent_path, replicate.roi)` or
  `(artifact_path, None)` plus the span offset. The matching rules are
  stated once, in the writer item's record section: `cut_from` equals the
  parent's current identity, `roi` equals the replicate's current ROI,
  format matches what the graph decodes, the file exists, **and the project
  clip lies within the record's span** (a widened clip un-backs the
  replicate rather than half-serving it — rule 6, refuse over approximate).
- Frame indexing: artifact frame 0 is source frame `span.start`. Keep
  `Frame.index` in *source* numbering at the seam the caller owns (a thin
  offsetting `FrameSource` wrapper over `VideoReader`), so clip arithmetic,
  the timeline, and the series collector never learn two numbering schemes.

## What this must not do

- **A record whose match fails must change nothing.** Same paths, same keys,
  same output as before the record existed — the fallback is the status quo,
  not an error. The GUI surfaces staleness (gesture item), the pipeline just
  declines.
- **Presence must never be consulted per frame.** Resolution happens where a
  render is planned, once; mixing artifact and parent frames inside one run
  would put two decoders' pixels under one root key.
- **`RunOutputs.source` honesty:** its docstring promises the frame *before*
  the replicate crop, and render-fed playback shows it as the whole frame.
  Serving from the artifact, the whole frame does not exist — the field
  carries the crop and must say so (a flag on `RunOutputs`, and the ring /
  viewport consumers render the crop as a crop, not letterboxed as if it
  were the source). Rule 6's mirror: never pretend to a frame nobody decoded.
- **Re-key once, visibly.** The first render after backing recomputes (new
  root identity). That is the accepted cost from the writer item; nothing
  here may try to migrate or alias old cache entries across the identity
  line to avoid it.

## Checklist

1. `src/sieve/pipeline/resolve_source.py` — the resolution step + offsetting
   `FrameSource` wrapper; docstring carries the per-frame prohibition above.
2. `src/sieve/cli/run_cmd.py` and `cli/preview_cmd.py` — route source
   opening through it (both front ends, or O3 is broken on day one).
3. `src/sieve/gui/preview_runner.py` (and whatever `document.py` hands it) —
   the GUI render path resolves the same way; luma/bgr choice feeds the
   format-match rule.
4. `RunOutputs` flag + ring/viewport honesty (small, but it is the rule-6
   edge of this item).
5. Tests: unit — matching (each clause flips independently: moved ROI,
   re-exported parent, missing file, widened clip, wrong format); integration
   over `synthetic_video` — materialize, re-render, assert the artifact file
   was what got decoded (e.g. delete the parent and render anyway), and that
   a failed match reproduces byte-identical pre-artifact output with
   unchanged keys.
6. `docs/SCAFFOLD.md` line for the new module.
