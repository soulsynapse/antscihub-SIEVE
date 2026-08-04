---
title: temporal_baseline.py's docstring argues four other files' decisions
status: open
opened: 2026-08-04
priority: normal
gated_on: nothing
reads: [src/sieve/filters/temporal_baseline.py, src/sieve/filters/background_ema.py, src/sieve/core/filter_base.py]
---

# temporal_baseline.py's docstring argues four other files' decisions

Docstring-convention pass (`tools/docstring_audit.py`) flagged this file
instead of bringing it to the convention. Its module docstring is 683 words
against the 250-word cap (not a contract module) — nearly 3x over — and the
excess is not restatable filler. It is four separate arguments, each about a
decision some other file owns:

1. **Ring-sampling cost/staleness tradeoff** ("The window is sampled, not
   held") — an implementation-performance argument for this filter's own
   ring buffer. Arguably belongs here, but is the single largest paragraph
   and could move to a code comment beside `sample_stride`/`ring_capacity`
   instead of the module docstring.
2. **"One node rather than two ports"** — an argument about the DAG's
   node/port model (`emits` being one stream per node), not about what
   `temporal_baseline` itself hides. This is the spec's shape, argued from
   inside a filter that happens to have run into it first.
3. **Why `ParamsBase.warmup_frames` exists** — the docstring says outright
   "`ParamsBase.warmup_frames` exists because of that number; see
   `core/filter_base.py`." That is a decision about `core/filter_base.py`'s
   contract, stated in the file that motivated it rather than the file that
   owns it.
4. **The stateful/uncacheable exclusion** — stated as `background_ema`'s
   reason "verbatim" and pointing at
   `docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`.
   Already duplicated in `background_ema.py`; this file only needs a
   one-line pointer, not the restated argument.

The filter's actual secret is one sentence: per-cell trailing median/MAD
baseline, emitting the input in units of deviation from it, because the
events being measured are in the sample and would inflate a mean/std
baseline against itself. Paragraphs 2–4 are not that secret; paragraph 1 is
adjacent to it but is implementation detail, not the conceptual decision a
reader needs before touching the file.

No split of the file itself is proposed — one filter, one class, one kernel,
no seam to check co-change on. The recommendation is prose relocation, not a
module split:

- Move paragraph 2 to whatever doc/docstring owns the DAG's node/port model
  (the `emits`-is-one-stream-per-node contract — likely
  `core/pipeline_model.py` or a `docs/` architecture note, not yet
  identified precisely).
- Move paragraph 3 into `core/filter_base.py`'s own docstring, where
  `warmup_frames` is defined, and leave a one-line pointer here instead.
- Collapse paragraph 4 to a one-line pointer at `background_ema.py` and the
  finding, as the docstring already gestures at doing ("verbatim") but then
  restates anyway.
- Paragraph 1 can likely fold into inline comments near
  `sample_stride`/`ring_capacity`/`MAX_SAMPLES`, since it is about how
  *this* file works rather than what it hides.

After relocation the module docstring should hold: the deviation-from-robust-
baseline secret, the `window_seconds`-has-no-correct-value argument (genuinely
this file's, ties directly to the primary param), and a one-line pointer for
each of the three relocated arguments. That should land under the 250-word
cap without deleting any underivable content — it moves to the file that owns
it, or shrinks to a pointer where it's already stated elsewhere.
