# LOOP-AUDIT — why the loop couldn't find the gaps in its own development

Audit of the 2026-08-06 → 2026-08-10 orchestrator build (work/review pairs via
`Code/agent-orchestrator`, prompts `sieve-v3-work.md` / `sieve-v3-review.md` /
`sieve-v3-specify.md`). Dated report, not a durable instruction: every number
in it is a measurement taken 2026-08-10 and named with the command that
produced it, so a later audit can re-take it and disagree. Written
incrementally; each section says what evidence it rests on.

## 1. Verdict

The loop built a working engine and never once asked whether the application
works, because no oracle it possessed could phrase the question.

Every instrument in the loop's sensorium had one shape: *does this named
pytest selector discriminate this named change* — the item's `done_when`
(206 of 238 items carry one; 200 of those are `uv run pytest` invocations;
`grep -l '^done_when' docs/todo/*.md | wc -l`), the reviewer's independent
re-run of that same selector, the revert-to-parent proof-of-red, and the
mutation sweep over the changed lines. "A person can launch SIEVE, open a
project, pick a video, and see frames" is not expressible in that shape, and
nothing in the prompts, the phase gates, CI, or any of the 238 items ever
demanded an oracle of a different kind:

- No test anywhere references the process entry point. `grep -rl
  'sieve-gui\|SIEVE\.py\|app:main' tests/` returns nothing; `sieve.gui.app:main`
  (`src/sieve/gui/app.py`) and `SIEVE.py` are the only unexercised code in the
  repo — and exactly the code a user runs.
- Every phase "Gate:" line in `docs/PLAN.md` is a pytest/lint condition,
  despite PLAN's own governing constraint ("each phase lands something
  runnable and gated") — the constraint was stated and never given an
  instrument.
- CI (`.github/workflows/ci.yml`) is ruff + lint-imports + pytest + actionlint.
  Nothing starts the process.
- All three loop prompts contain no instruction to launch the app, exercise a
  user path, or verify integration between components.

The result, after 642 commits and a suite that passes 1305/1305: the shelf is
empty on every relaunch (no open-project gesture survives ADR 35's removal of
the cwd scan — `docs/todo/pinning-a-project-is-state-the-library-has-nowhere-to-put.md`,
open), the chosen video never reaches the player
(`docs/todo/the-chosen-file-never-reaches-the-player.md`, open, high — `_player.open`
has exactly one caller in `src/`, and it is not the chooser), and every project
file minted before 2026-08-10 is refused by the schema (ADR 34's
`extra='forbid'`, no migration, `SCHEMA_VERSION` still 1). These three compose
into the reported symptom: mint → pick → nothing shows → the documented remedy
is reopen → reopening needs a shelf → the shelf is empty → mint again, leaving
another stray `untitled_N.sieve.yaml`.

The sharpest framing is not "couldn't find" but **couldn't ask**. The loop
*did* find these gaps — they exist as items — but all four does-the-assembled-
thing-run defects were minted on days 4–5 of a five-day build, each one the
residue of a human hand-launching the app. And when the strongest evidence
surfaced early (stray empty `untitled_1.sieve.yaml` mints in the source tree),
the loop's own machinery converted it into
`docs/todo/a-mint-lands-wherever-the-app-was-launched.md` — a
location-of-default bug, closed `done` against a `tests/gui/test_project_cards.py -k`
selector — rather than into "nothing past the mint works."
`scripts/doc_index.py --next` is the loop's entire world model, and only
minted items are in it; nothing in it can select an absence. The loop confessed
this itself, in the commit message of `67d9c9a`: the missing work "was not
unknown work — it was work named in PLAN, in MOCKUP-MAP, in two module
docstrings, and inside a `done` item's body, carried by no item and therefore
invisible to `--next`."

## 2. What worked — and should be kept

The per-item rigor was real, unusually so, and the next loop should not lose
it in reaction to the miss.

**Executable criteria, actually executed twice.** 206/238 items carry a
`done_when`; 200 are pytest invocations, the rest `mutation_sweep.py`,
`lint-imports`, or one-line probes. The worker runs the criterion red before
writing (proof-of-red by reverting the implementation), the reviewer re-runs
it independently and re-proves red at the parent commit. Both halves are
visible in the review commits' recorded transcripts.

**Reviews that reopen.** 194 `docs(review)` commits
(`git log --format=%s | grep -c '^docs(review)'`). Reviews reopened work
repeatedly and on principled grounds — sampled diffs: `4f6f9c5` ("delete
`painter.drawImage(...)` … and `done_when` is still `2 passed`" — criterion
cannot tell the composite from nothing), `a983a17` (criterion named a test key
rather than a clause of the item's body), `2400bf6` (a widened disjunction "is
green for whatever it names and does not have"), `912bc0d` (folded clause
unstarted: a grep of the target file is empty). A grounds taxonomy over the
full 194 is in §5.

**Mutation discipline.** `scripts/mutation_sweep.py` ran against landed lines
as a standing review step, and produced real product findings — e.g.
`docs/findings/2026.08.10-the-un-serving-inverse-survives-the-whole-suite.md`
(half of `crop_serving._uncut` deletable with 1296 tests green). Most
professional teams do not do this at all.

**The apparatus caught its own blind spots — one level down.**
`tests/conftest.py`'s `FATAL_FIXTURE_SKIPS` converts a skipped decoder fixture
into a hard failure, on the explicitly recorded reasoning that "a decoder test
that skips is indistinguishable from one that passes." That is precisely the
class of reasoning that, applied one level up — *an application no test
launches is indistinguishable from one that works* — would have caught the
miss. The loop had the epistemics and pointed them at the wrong altitude.

**Externalized memory held.** 93 findings files plus 114 in
`docs/findings/loop/` (counts: `ls docs/findings/*.md`, `ls docs/findings/loop/*.md`),
in a disciplined verdict/measurements format; 33 settled ADRs. The loop's
self-model was rich enough that this audit could largely be assembled from the
loop's own records — including its records of exactly the failure modes that
produced the miss (`docs/findings/loop/2026.08.09-a-k-disjunction-is-green-for-the-disjunct-that-names-nothing.md`
and at least five siblings). Each time, the remedy minted was a *better
selector*, never a different kind of oracle — which is §3's subject.

**But the rigor turned inward.** 114 of 207 findings are about the loop's own
machinery, not about SIEVE. Test functions by tier (`grep -rho 'def test_'
<tier> | wc -l`, 2026-08-10): unit 600, gui 254, docs 109, integration 101,
bench 43, scripts 37 — the loop wrote more tests of its own documentation
machinery than of cross-component integration, and the final days of the log
are the loop auditing its mutation harness rather than the product. A closed
system optimizing its own consistency; consistency says nothing about whether
the thing runs.

## 3. The blind spots, as structure

*(pending — transcript pass)*

## 4. Rules that composed into the failure

*(pending)*

## 5. Timeline and review-grounds taxonomy

*(pending)*

## 6. Prescriptions

*(pending)*

## 7. Appendix: shortest path to deployable, 2026-08-10

*(pending)*
