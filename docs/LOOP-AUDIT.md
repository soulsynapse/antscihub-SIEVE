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

Evidence for this section includes a pass over the raw orchestrator
transcripts (`~/.agent-orchestrator/logs/`, 762 runs, 2026.08.04–08.10; grep
commands inline below). Four blind spots, each structural rather than an
oversight:

**3.1 One oracle shape, held at both ends.** The worker satisfies a pytest
selector; the reviewer re-runs the same selector, re-proves red at the parent,
and sweeps mutants over the changed lines. Both ends of the loop share one
oracle, so anything the selector does not name is invisible to both — and the
selector is written *before the work exists*, by specify, under a rule that
forbids breadth (§4.1). The loop recorded this exact mechanism about itself at
least six times in `docs/findings/loop/` (the `-k`-disjunction finding and its
siblings) and each time minted a better selector, never a second kind of
oracle. A loop whose only remedy for a blind selector is a sharper selector
can refine forever without gaining altitude.

**3.2 `--next` is the world model, and absence has no item.** Selection is
stateless: `scripts/doc_index.py` orders every `status: open` item and hands
over the head. Work not carried by an item does not exist — not deprioritized,
*unrepresentable*. There was never an item whose subject was "the
application," so the application was never selected, worked, or reviewed.
The confession in `67d9c9a` (§1) names the consequence precisely.

**3.3 No instrument above the module — measured, not asserted.** Across all
762 run transcripts, exactly **3** contain a command that launches the app
(`grep -lE 'uv run sieve-gui|sieve-gui\.exe|python SIEVE\.py' *.log` over
non-err logs), and **zero** of those are loop-labeled runs — the same grep
over `*sieve-v3-*.log` returns nothing. Two are 08-05 ad-hoc sessions
predating the loop; the third is the 08-09 ad-hoc item that created
`SIEVE.py`, whose own transcript states the entire runtime verification the
project ever received: the process "came up and stayed up until I killed
them." Liveness, once; scenario, never. Everything else the loop could see is
below the process: GUI tests run offscreen with fabricated events handed to
handlers (`tests/gui/driving.py`), fixtures are 160×120 synthetic clips
generated in-process, real footage is `.gitignore`d by written decision
(`video-tests/` — defensible for review hygiene, and it places the only
realistic input outside everything the loop can observe), and the reviewer's
view of the work run itself is a tail — `read_run_log` returns at most the
last 1000 lines, 150 by default, and its own docstring says so: "readings
come back as the tail, so a long run is its ending"
(`agent-orchestrator/src/agent_orchestrator/mcp_server.py`).

**3.4 The rigor turned inward.** §2's ratios (114/207 findings about the loop;
more doc-machinery tests than integration tests), plus the head of the commit
log: the final day is largely the loop auditing its mutation harness. This is
not idleness — it is the apparatus doing exactly what it was built to do,
optimizing the consistency of its own verdicts. Consistency is the property
that says nothing about whether the assembled thing runs.

## 4. Rules that composed into the failure

Each of these is defensible alone; the miss is their composition.

**4.1 Specify's narrowness rule.** `sieve-v3-specify.md:42`: a criterion is
"Not a description of a passing state, not a whole-suite run that would pass
today." Written to prevent self-certification — and it works — but it makes a
criterion that spans components structurally impossible. Every criterion is
narrow *by construction*, so §3.1's shared oracle is always a narrow one.

**4.2 Scope prohibitions at both ends.** The work prompt forbids landing
anything the criterion does not need and forbids minting when an open item
could carry the observation; the review prompt forbids fixing anything and
rules on one item. A worker who noticed the app doesn't start was
out-of-jurisdiction fixing it; a reviewer who noticed was permitted only to
mint — into the same pool where phase-9 asides sat unselected. Noticing was
legal; *acting* was not, and the noticing had nowhere load-bearing to land.

**4.3 Removals paid by the user.** ADR 35 removed the `Path.cwd()` shelf scan
and ADR 34 removed `Project.source`, each deliberately deferring the
replacement (`pinning-a-project-is-state-the-library-has-nowhere-to-put.md`,
open; `SCHEMA_VERSION` held at 1, no migration). Both removals were correct by
their ADRs' own reasoning and both left the running application worse than
before — the empty shelf and the refused project files are these two decisions
— because nothing prices an ADR against the user's next launch. Meanwhile
`README.md:14` and `SIEVE.py`'s docstring still describe the removed cwd scan:
the only user-facing instructions tell the user to do something the code no
longer supports.

**4.4 A named failure mode with no instrument.** `docs/PLAN.md` states
"Wrong-but-green is the one outcome the loop cannot detect" and demands each
phase land "something runnable and gated" — then writes every phase gate as a
pytest/lint line. The constraint that would have caught this was in the
binding doc from the start, as prose. A constraint without an instrument is a
hope; the loop itself proved that its documents' other constraints held
exactly when a gate or a criterion enforced them and drifted when they didn't.

## 5. Timeline and review-grounds taxonomy

Commits per day (`git log --format=%ad --date=short | sort | uniq -c`):
39 / 251 / 125 / 157 / 70 across 08-06 → 08-10. Loop-labeled runs per day
(log filenames): 73 / 92 / 80 / 55 across 08-07 → 08-10.

Every does-the-assembled-thing-run defect was minted in the last two days,
each from a human hand-launching the app, while the numbered plan was already
`done` through phase 11:

| Commit | Date | Item |
|---|---|---|
| `64a774a` | 08-09 | `a-mint-lands-wherever-the-app-was-launched.md` — NEW PROJECT writes into the source tree |
| `67d9c9a` | 08-09 | `only-run-writes-the-document.md` — closing the window discards every edit |
| `8836652` | 08-09 | `a-dropped-player-takes-the-process-down-and-its-net-is-a-comment.md` |
| `b8ad052` | 08-10 | `the-chosen-file-never-reaches-the-player.md` — the central user path, still open |

Review behavior, classified by the `+status:` lines each of the 196
review-subject commits wrote into `docs/todo/` (script: `git show <h>
--unified=0 -- docs/todo/ | grep '^+status:'`): 79 closed `done` only;
58 wrote `done` and at least one `open` (closed the item and minted or
reopened another); 33 wrote `open` without closing anything; 12 touched no
item status (findings/gardening); 14 involved `deferred`. So roughly half of
all reviews produced at least one open item — the reviewer's teeth were real.
The grounds, in every sampled reopen (§2), are one of four shapes: the
criterion doesn't discriminate; a clause of the item's body is unbuilt; the
proof-of-red was too weak; the criterion is a disjunction green on its empty
side. All four are selector-shaped. No review's grounds were "I ran the
application and it did not do the thing" — consistent with §3.3's zero
launches in loop-labeled transcripts.

## 6. Prescriptions

Each cites the blind spot it answers. The theme is one addition — a second
kind of oracle — plus routing rules so evidence of the app's state can reach
`--next`.

**6.1 Give PLAN's "runnable" constraint an instrument (3.3, 4.4).** Every
phase gate gains one clause that executes the real entry point: launch
`sieve-gui` (the console script, not an imported widget), drive the phase's
lead scenario, assert its observable outcome. Even the weakest version —
process starts, opens a project passed on argv, renders a first frame, exits
0 — would have caught all three current breaks. This is the single highest-
leverage change; everything the loop already does well (proof-of-red,
independent re-run, mutation) applies to this oracle unchanged.

**6.2 A standing hand-session item, early and recurring (3.2, §5).** The
day-4/5 pattern — Kendrick uses the app, defects become items — was the only
mechanism that ever found this class. Make it deliberate: a recurring item per
phase whose `done_when` is the existence of a dated hand-session finding, and
whose body says the session is Kendrick's, not an agent's (an agent cannot
author this completion without the finding becoming fiction). This is also
the routing fix for §1's converted evidence: a hand-session finding names the
*path* that failed, not the local default that happened to be wrong.

**6.3 Phase-boundary criteria may span components (3.1, 4.1).** Keep specify's
narrowness rule for ordinary items; carve out the phase-gate item class, whose
criterion is *required* to cross at least the seam the phase claims to close.
The rule that prevents self-certification and the rule that prevents breadth
are the same sentence today; they need to be two sentences.

**6.4 An ADR that removes behavior carries its replacement at priority
(4.3).** Not a pool aside: if the removal degrades a user path, the
replacement item is minted in the same commit with a priority that outranks
the pool, or the ADR waits. ADR 34/35 are both cases where the reasoning was
right and the sequencing produced a regression nothing owned.

**6.5 Entry-point coverage in CI (3.3).** One test that runs the installed
`sieve-gui` as a subprocess (offscreen platform is fine — the point is
`main()`, argv handling, and the wiring between them, all currently at zero
coverage). Cheap, permanent, and it makes `README.md`-style drift (§4.3)
fail red instead of lying quietly.

**6.6 Minor: let the reviewer read beginnings (3.3).** `read_run_log`'s
tail-only reading means a long work run is its ending. Either front-load the
work prompt's claims summary (it already pastes `done_when` output early) or
add a head/offset parameter. Low weight next to 6.1–6.3.

## 7. Appendix: shortest path to deployable, 2026-08-10

Recorded for actionability; repair is outside this audit. Three breaks
compose into the current symptom, two already minted:

1. **The shelf is empty on relaunch** — no open-project gesture, no remembered
   locations, argv ignored. `pinning-a-project-is-state-the-library-has-
   nowhere-to-put.md` (open). Accepting a project path on `sieve-gui` argv is
   the smallest cut.
2. **The chosen file never reaches the player** —
   `the-chosen-file-never-reaches-the-player.md` (open, high). `_player.open`
   has one caller (`app.MainWindow.open_project`); the chooser path ends
   before decode.
3. **Pre-08-10 project files are refused** — ADR 34's `extra='forbid'` with
   `SCHEMA_VERSION` still 1 and no migration. Either strip `source:` from the
   dead files by hand or build the one-key migration the ADR declined.

Plus the documentation lie: `README.md` and `SIEVE.py`'s docstring describe
the cwd scan ADR 35 removed — the likeliest reason the first launch reads as
broken rather than unfinished. Residue on disk as of this audit: untracked
empty mints at `projects/untitled_1.sieve.yaml` and
`video-tests/untitled_1.sieve.yaml`, left in place as evidence.
