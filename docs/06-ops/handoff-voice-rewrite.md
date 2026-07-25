# Handoff: rewrite the documentation corpus into SIEVE's voice

[INTENT] A self-contained brief for an agent that has not read this repository.
The standard is decided and a tool checks it — this is transcription against a
fixed target, not a judgement call about what the documents should say.

**Prerequisite:** `tools/doc_voice.py` must exist. If it does not, stop and do
`handoff-voice-checker.md` first. This task is driven by that tool's output;
without it there is no way to tell whether a file is done.

---

## The loop you are running

For each file in the work list below, in order:

1. `python tools/doc_voice.py --path <file>`
2. Fix what it reports, following the rules below.
3. Re-run the same command.
4. Move on when the main body of the report is clean for that file.

That loop is the whole task. Do not rewrite from your own sense of the voice —
the tool decides what is done, one file at a time. Working file by file is what
keeps this from needing the whole corpus in context at once.

## The voice you are rewriting into

Descriptive, not imperative. The prose says what is true and why, not what the
reader must do. Confidence is marked explicitly.

The five tags, spelled exactly like this:

```
[STABLE]         a settled property of the system
[ASSUMPTION]     believed, not verified; name what would test it
[INTENT]         a plan or a reason for a choice, not yet a fact
[STALE WHEN]     the condition that invalidates the statement
[OPEN QUESTION]  undecided; say what the alternatives are
```

## How to fix each finding

### Absolutes (`must`, `never`, `always`, `guarantee`, `ensure`, …)

Ask what the sentence is really claiming, then pick one:

- **It is enforced by a tool.** Say so and name the tool. "The layer contract
  in `.importlinter` fails on a Qt import reaching `pipeline/`" beats
  "`pipeline/` must never import Qt."
- **It is an intent, not an enforcement.** Tag it `[INTENT]` and say the
  intent. "Filters must not spawn threads" → "[INTENT] Filters do not spawn
  threads; concurrency belongs to the executor."
- **It is a belief.** Tag it `[ASSUMPTION]` and name what would test it.
- **It is a settled fact.** Tag `[STABLE]` and state it descriptively.

Do not simply swap `must` for `should`. That changes the wording and leaves the
epistemic status exactly as unmarked as it was, which is the actual defect.

### Imperative openers

Rewrite the sentence to describe rather than instruct.

- "Use PySide6 for the UI." → "The UI is built on PySide6."
- "Ensure the cache key includes upstream hashes." → "Cache keys include
  upstream content hashes, so siblings on a shared parent do not invalidate
  each other."
- "Do not construct the store directly." → "Callers reach the store through its
  owning module rather than constructing one."

### Untagged runtime claims

Add the tag that fits. If you cannot tell which one fits, the correct answer is
`[ASSUMPTION]` with a note on what would settle it — never a confident
`[STABLE]` on something you had to guess about.

## Work list, in order

Do them in this order. It goes cheapest-and-most-recent first, so you build
calibration on documents already written to the standard before touching the
hardest ones.

1. `docs/06-ops/architecture-digest.md` and `docs/06-ops/adr-digest.md` —
   already written to the standard. Expect few findings. Use these to calibrate
   what "done" reads like.
2. `docs/05-adr/ADR-018-*.md` — also written to the standard, and the worked
   example of an ADR in this voice. **Read this one before rewriting any other
   ADR.** It shows how a `Decision` section carries tags.
3. The remaining ADRs, `ADR-001` through `ADR-017`, in numerical order.
4. `docs/04-architecture/ARCHITECTURE.md` — the largest and the one that most
   needs it. See the two specific items below.
5. `docs/01-vision/*.md` and `docs/02-requirements/*.md`.

## Two specific content fixes in `ARCHITECTURE.md`

These are not wording changes and are the reason a human wrote this list. Both
are already-decided corrections that the rewrite pass is the occasion to make.

**§12 illustrates deterministic GPU mode with Torch-only API calls.** ADR-016
selects CuPy as the only v1 GPU backend and states that this Torch language is
not operative. Replace the Torch API calls with the CuPy-specific
reproducibility contract that ADR-016 describes. Read ADR-016 before touching
this section.

**§1 calls its latency numbers "hard targets" and asserts "four commitments the
architecture never violates."** These are the load-bearing absolutes in the
whole corpus, and they are not all the same kind of claim. Tag them
individually rather than softening them as a block: some are enforced, some are
intent. The budget table itself is transcribed into `src/sieve/bench/budgets.py`
and checked by `tests/bench/test_budget_table.py`, so §1's numbers are enforced
and can say so.

**Do not change any number in the §1 budget table, and do not change the
wording of the interaction descriptions in it.** A test parses that table and
compares it against the transcription in code. Editing a row breaks the test.
If you believe a row needs changing, leave it and say so in your final report.

## ADR sections you leave alone

The checker reports ADR `## Decision` and `## Consequences` findings in a
separate section headed *"genre question unresolved."*

**Do not rewrite anything in that separate section.** Whether the voice rule
reaches ADR Decision sections is an open question the maintainer has not
settled, and rewriting them would answer it by default. Fix the main body of
each report only.

`ADR-018` is the exception you may learn from but not copy wholesale: it was
written with tags inside its `Decision` section already, which is one possible
answer to the open question rather than the settled one.

## Rules

- **Do not change what a document claims.** You are changing how a claim is
  worded and how its confidence is marked. If a rewrite would change the
  meaning, leave the text alone and note it in your final report.
- **Do not change any ADR's `Status` line.**
- **Do not renumber ADRs or rename files.**
- **Do not edit anything under `src/`, `tests/`, `tools/`, or `noxfile.py`.**
  This task is prose only. A test parses `ARCHITECTURE.md`; nothing else in the
  code reads these documents.
- **Do not edit `docs/06-ops/LLM-wiki/`** — it is a vendored copy of another
  tree.
- **Do not edit `NOTES.md`** — the maintainer owns it.
- **Do not run `git commit` or `git push`.**

## Verify before you finish

```
.venv/Scripts/python.exe -m pytest -m "not slow and not qt" -q
python tools/doc_voice.py
```

The test run must pass — `tests/bench/test_budget_table.py` is what catches an
accidental edit to the §1 table. The checker's main-body findings should be
substantially reduced; the ADR-genre section will still be full, and that is
correct.

## Your final report

Write it to `docs/06-ops/voice-rewrite-report.md`:

- files rewritten, with the finding count before and after each;
- every place you left text alone because rewriting it would have changed the
  meaning, quoted with the file and line;
- anything the checker flagged that you judged a false positive, quoted, so the
  word lists can be tuned;
- the §12 and §1 fixes, described in a sentence each.

That last section is what the maintainer reads first. The checker's word lists
are a first guess and are expected to be wrong in places — telling us where is
part of the deliverable, not a complaint.
