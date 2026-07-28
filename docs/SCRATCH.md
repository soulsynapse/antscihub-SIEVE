# Scratch

Running notes from the fast pass of 2026-07-28. Not a doc — the item files and
`docs/completed-todo/` still own the record, and nothing here has been moved
there yet.

---

## Housekeeping first: a prior session's sweep was uncommitted

The tree had 99 modified files on arrival — the "entries lose their bodies"
sweep (3.8k lines of completed-entry bodies removed, `tools/complete_item.py`
and CLAUDE.md rewritten to say the frontmatter *is* the entry, plus the new
comment/split rules). Committed as `4a11c01` on its own so everything below is
separable from it. Not my work and not attributed as anyone's.

## proxy-retention-policy — the fraction, done

`RENDER_RING_SHARE` was `floor_bytes=256 MB, fraction=0.0`, with the zero
deliberate: how much of a bigger machine the ring deserves was the item's
question and growing it elsewhere would have decided it by side effect. The
finding answered it (capacity beat eviction policy ~60:1), so:

- `gui/concurrency.py` — `fraction=0.01`. Arithmetic for the choice: the
  finding's machine had 68.4 GB available, reserve is 4 GB, so the budget is
  64.4 GB and 1% is ~644 MB — ~700 gray 1280-wide proxies at 921,600 B each,
  against the ~720 where that session's working set saturated. Sized to reach a
  large machine's own knee, not to hardcode 720.
- Below ~26 GB total the fraction falls under the 256 MB floor and the floor
  resolves, so a small machine pays nothing for this. That is also exactly the
  case the finding said it could not settle, left as it was.
- `gui/render_ring.py` docstring updated — it said the bound was fixed "until
  the item replaces the number with policy".

**Still open in that item:** the scrub half. 16 scrub events, 0.00% hit under
every policy, no sample. Reopening the eviction rule is a *stall*-length
argument, not a throughput one, and needs a session that scrubs.

## headless-detection — built, including the two things that fall out

New `src/sieve/detect/` (layers: sibling of decode/storage/backend, above
core, below pipeline; added to the headless no-PySide6 contract).

- `detect/detector.py` — `DetectorUpdate`, `detect`, `settled_for`, `gate_to`.
  Takes a resolved `DetectorSettings`, never a `DetectorState` and never a
  `Project`, as the item required.
- `gui/chain_model.recompute` and `gui/detector_worker.settled_for` are now
  two-line adapters that convert the live state at the boundary; `gate_to`
  moved outright and `filter_tab` imports it from `sieve.detect`.
- `DetectorState.to_settings()` added — the item claimed it already existed; it
  did not, only `as_settings_changes()` returning a dict for partial submits.
- `sieve detect` in `cli/detect_cmd.py`, wired in `cli/app.py`.
- `tests/integration/test_cli_detect.py`, three tests, no `gui` marker.

Two decisions the item did not make, both taken here:

1. **Which node's output is the series.** The sink, and a graph with two sinks
   is refused with `--node` named rather than one being picked. Which series a
   detection was taken over is part of what the answer means.
2. **`Project.detector is None`.** Reported as "this project has no detector,
   so it claims nothing" — not resolved to `DetectorSettings.default_for(fps)`
   and not printed as zero intervals. Two distinct absences (never tuned vs
   tuned-but-disarmed) and neither is "found nothing".

A whole-clip CLI pass is `final` by construction, so none of the partial-record
frontier arithmetic runs — `settled_for(..., final=True)` is the whole record.

**Not done, and it is the next obvious step:** the HPC item
(`docs/todo/hpc-handoff-and-review-mode.md`) rests on a premise this item
falsified — "HPC consumes the same serialized DAG the CLI does", true of the
executor and false of detection. That is now true of detection too, and that
item does not know it yet.
