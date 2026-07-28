---
title: The crop artifact writer
status: open
opened: 2026-07-28
gated_on: >
  nothing — first of the three-item crop split (writer → serving → gesture);
  the codec is measured and every design decision below is settled
reads:
  - docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md
  - src/sieve/core/pipeline_model.py
  - src/sieve/decode/reader.py
  - src/sieve/pipeline/cache_key.py
---

# The crop artifact writer

The takeable half of the materialization item (docs/todo/materialization.md
holds the history): write one replicate's crop, over the clip span, to a file
that is then a source in its own right. This item is the writer, the record,
and the CLI; serving it and the GUI gesture are the two items after it
(docs/todo/crop-artifact-serving.md, docs/todo/crop-boundary-gesture.md).
This is the first writer, so it is also the commit in which **"filesystem is
truth at rest" returns to the rules table** — see the checklist's last steps.

## The identity model, revised 2026-07-28

The 2026-07-27 settlement in materialization.md read "lossless is not a
preference, it is the identity line": the artifact would serve the *parent's*
`source_key`, which demands byte-identity with decode-then-crop. Revised the
next day (user decision, deliberately): **the artifact is a child source with
its own identity**, exactly the "different source, declared as one" clause
that settlement reserved for lossy proxies — applied to the artifact itself.
Bit-parity with the parent is not load-bearing anywhere. What this buys:

- Runs against the artifact key their roots off the artifact file's own
  identity (`source_identity(artifact_path)` — the same path|size|mtime
  derivation, unchanged) with `roi=None`. `plan`, `executor`, and
  `cache_key.py` need **no edits**; the artifact is just a source video.
- No dependence on cross-codec or cross-decoder-version byte-exactness. A
  decoder upgrade cannot orphan an artifact at rest.
- The cost, accepted knowingly: descending onto the artifact re-keys, so
  downstream cache entries from source-side tuning are recomputed once —
  priced at one render, which the descent triggers anyway (the serving item
  owns that). Two replicates with identical ROIs also stop sharing entries
  once each is backed by its own artifact file.

Rule 7 stays clean: the *record* below is location (where an artifact lives
and what it was cut from); the *identity* that enters keys is computed from
the artifact file itself at run time, as it is for any source. Nothing
straddles — a replaced or truncated file changes identity by construction.

## Settled decisions

- **Codec: FFV1 in Matroska, encoded with PyAV** (`av` is a new dependency;
  the 18.0 wheel carries the encoder — verified). The finding prices lossless
  at zero: smallest files, 0.09 ms/frame sequential, 3.9 ms seeks, and
  byte-identical through the unchanged `VideoReader`, which the qp0 routes
  are not. Decode of the artifact is `VideoReader`, unchanged.
- **Format: the one the current graph decodes** — gray FFV1 fed from a
  `luma=True` reader when `Dag.needs_chroma` is false (the reference
  workload), bgr24 FFV1 otherwise. One artifact per format; a session that
  flips format later falls through to the parent and may write the second.
  Do **not** write one colour artifact to serve both: a luma read of an
  RGB-coded file is the finding's wrong-pixels trap verbatim.
- **Span: the project clip** (frames `[clip.start, clip.end)`), recorded on
  the record. Artifact frame 0 is source frame `clip.start`.
- **The write pass is a sequential `VideoReader` pass** over the span,
  cropped in-process with the same `ROI.clamped_to(...).crop(...)` the
  executor applies — the one existing definition of the crop. Cost is the
  decode it was already going to do (46 s luma / 124 s bgr on the reference
  clip; encode adds under 2 s and under 7 s).
- **Verification is a corruption guard, not a parity gate.** Hold a digest
  and cheap statistics per fed frame; read the finished file back through
  `VideoReader` and compare. Byte-equal passes trivially (FFV1 will be);
  what must *fail* is the qp0-gray class — served pixels that match no fed
  frame — so the tolerance test should be gross (e.g. mean abs diff within a
  few grey levels per frame), stated in the module docstring, and a failure
  deletes the file and raises rather than registering it (rule 6: refuse,
  never a plausible artifact that lies).
- **Atomic:** encode to `<name>.part.mkv`, verify, rename, and only then
  return the record. Cancellation (a poll/callback) deletes the part file.
- **Placement convention:** `<video stem>.crops/` beside the project file,
  file name `<replicate name slug>-<format>-<start>-<end>.mkv`. The path is
  location, carried on the record relative to the project dir exactly as
  `Sink.path` is; the name is convenience, never identity.

## The record

`core/pipeline_model.py` gains a frozen `CropArtifact` model and
`Project.crops: tuple[CropArtifact, ...] = ()` — beside `checkpoints` and
`outputs`, on `Project` and off `Node`/`Replicate`, for rule 7's reason.
Fields: `path` (POSIX, relative to project dir), `roi` (the geometry it was
cut at), `format` (`"luma" | "bgr"`), `span` (start/end, reuse `ClipRange`),
`cut_from` (the parent's `source_identity` string at write time), `decoder`
(`decoder_identity()` at write time — provenance, deliberately *not* matched
at serve time; the artifact outlives decoder upgrades by design). Bump
`SCHEMA_VERSION` to 4 with the usual constant comment; a v3 document loads
unchanged. Matching rules (used by the serving item, stated here once): a
record backs a replicate iff `cut_from` equals the parent's current
`source_identity`, `roi` equals the replicate's current ROI, and the file at
`path` exists — a moved ROI or re-exported source misses by construction.

## Checklist

1. `pyproject.toml` — add `av`.
2. `core/pipeline_model.py` — `CropArtifact`, `Project.crops`, schema v4,
   validators (span nonempty; no two records with equal
   `(cut_from, roi, format, span)`), `relocated()` rebases `path`.
3. `src/sieve/storage/crop_writer.py` — PyAV FFV1/MKV encoder taking an
   iterator of arrays plus fps; owns no identity logic. Drop the
   `(sieve.storage)` parentheses in `.importlinter` in the same commit.
4. `src/sieve/pipeline/materialize.py` — orchestration: open reader in the
   requested format, crop, feed writer, collect per-frame digests/stats,
   read back, verify, rename, return the `CropArtifact` value. Refusals and
   cancellation as above.
5. `src/sieve/cli/materialize_cmd.py` — `sieve materialize <project>
   --replicate <name-or-id>`; writes, registers, saves the project (O3: the
   artifact must be creatable headless).
6. Tests: unit — record round-trip, v3-loads, matching rules; integration —
   materialize over `synthetic_video`, read-back equals fed crop, a
   corrupted/truncated artifact refuses, cancellation leaves no part file.
7. `docs/SCAFFOLD.md` — move `pipeline/materialize.py` up, add
   `storage/crop_writer.py` and `cli/materialize_cmd.py`; `zarr_store.py`
   stays projected (it belongs to general materialization, still deferred).
8. `docs/ARCHITECTURE.md` — move "filesystem is truth at rest" from
   *Commitments not yet in force* into the rules table (rule 8; state its
   objective and falsifier like the others), and update `CLAUDE.md`'s "seven
   rules" section to eight. The commitment's own text says this happens "in
   the commit that lands the first writer"; this is that commit.
