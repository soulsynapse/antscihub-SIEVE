# Ideas

Stuff written by Kendrick to be assessed. Format: Put a md paragraph below each idea for your feedback.

Ideas are one line each, starting below ---, so any line without a paragraph below it needs a response.

Feedback should be with one line between each.

> Grumpy Sr. Engineer Opinion:
> 
> Mentor Sr. Engineer Opinion:
>
> Assessment:
>
> Bottom line:


---

I think todo.md can be deleted and whatever is pointing at it redirected

> Grumpy Sr. Engineer Opinion: You want to delete the file holding the only index of 27 settled decisions and the five deferred rejections, and a test (`tests/docs/test_todo_hygiene.py`) asserts on its bug list. "Redirect whatever points at it" is the easy 5% of the job.
>
> Mentor Sr. Engineer Opinion: The instinct is right but the diagnosis is wrong. TODO.md is not redundant, it is three unrelated files sharing a name: a bug queue, an anti-rediscovery table, and a rejected-decisions list. Only the first is a to-do, and it is the only one that is actually duplicated.
>
> Assessment: Every one of the 16 bullets already ends in `→ todo/<slug>.md`. The only datum the bullet holds that the item file does not is `(noticed YYYY.MM.DD)`. Move that to `noticed:` in item frontmatter, have `tools/doc_index.py` emit the list, and rewrite `test_todo_hygiene.py` to check the frontmatter key instead of parsing prose — that deletes the bug section mechanically with no information loss and makes the noticed-date sortable for the first time. What is left is the "What already exists" table plus Deferred decisions, which are load-bearing, are not to-dos, and are read at a different moment (before building, not when choosing what to build).
>
> Bottom line: Not a delete — a split and a rename. Bug list becomes generated; the remainder becomes `docs/SETTLED.md`, which is what CLAUDE.md's routing table already calls it ("what already exists"). Two redirects: CLAUDE.md and `docs/todo/_TEMPLATE.md`.

Some way to automatically figure out where the models are spending most of it's time so we can identify ways to speed up the agentic programming loop

> Grumpy Sr. Engineer Opinion: `tools/transcript_stats.py`. It is in SCAFFOLD.md annotated "mines session transcripts: where agent wall-clock went," it has four passing unit tests, and its docstring already documents the accounting model down to the residual-attribution heuristic. This idea is built, and you re-proposing it is itself a data point about the loop.
>
> Mentor Sr. Engineer Opinion: What is missing is not the measurement, it is the series. A hand-run script produces a number with nothing to compare it to — and by your own standing rule, a measurement run by hand is a defect. No baseline means no change can be scored.
>
> Assessment: This is structurally `todo/slow-path-surfacing.md` ("sessions log how the app was used, and changes are scored against a moving baseline") one layer up, applied to the agent instead of the app. Have `nox -s docs` append one dated row per session and put the current split in `.state.md` as one line. Caveat worth stating plainly: transcript timings measure the *harness*, not the model — residual is attributed to the phase of the next tool call, which the docstring correctly labels a heuristic. And two of the largest costs need no instrument at all: gate wall-clock (31 s today, which is cheap) and context spent reading docs the session did not need, which is ideas 3 and 4.
>
> Bottom line: Do not build a second tool. Run the existing one from the `docs` session and emit one line into `.state.md`, so a tooling or docs change has something to be scored against.

A bunch of the items in the docs are stale, having a new folder for items that might be useful historic references could be good.

> Grumpy Sr. Engineer Opinion: You have three history stores already — `completed-todo/`, `findings/`, and the four dated records CLAUDE.md names (VISION, REFINED-VISION, SIEVE-HANDOFF, the parity plan). A fourth is a fourth place not to look, and moving files breaks `git log` continuity for exactly the documents whose value is that they are dated.
>
> Mentor Sr. Engineer Opinion: The problem you are feeling is not location, it is that a reader cannot tell from the top of a file whether it claims current truth. CLAUDE.md holds that list, in prose, unchecked — so the mechanism exists and is invisible at the point of reading.
>
> Assessment: Add `status: current | record` to the frontmatter of every `docs/*.md`, make `tools/doc_index.py` refuse to route a `record` as current, and generate CLAUDE.md's routing table from it. That is the `reviewed:`/`subjects:` stamp applied to the axis the stamp does not cover — is this doc *supposed* to be true now. A record then announces itself in its own first three lines instead of in a doc the reader may not have open.
>
> Bottom line: A frontmatter key, not a folder. If you do move anything, move only what nothing links to — and that set is better served by deletion, since git holds it.

A bunch of the items in the docs main folder are also wrong or basically never read, even if they aren't historic.

> Grumpy Sr. Engineer Opinion: "Wrong" and "never read" are opposite problems and you have bundled them. A wrong doc nobody reads costs nothing, and deleting it also costs nothing. A wrong doc read every session is the only expensive case, and you have not measured which docs those are.
>
> Mentor Sr. Engineer Opinion: You already have half the instrument. `tools/doc_drift.py` reports ARCHITECTURE.md at 47 commits of subject drift and AUTO-GUARDRAILS.md at 7 — that is the "wrong" axis, quantified. The "never read" axis is precisely what the transcript miner from idea 2 can answer, by counting `Read` calls against `docs/*` across sessions. Joined, those two give a triage grid instead of a feeling.
>
> Assessment: Rank by read-count, fix the top, delete the bottom. Do **not** promote `doc_drift` to a gate — it is reporting-only by design, "N commits touched a subject path" does not imply a claim went false, and gating it buys a stamp-bumping ritual plus a green CI that means nothing. Surface its worst line in `.state.md` instead, so drift is seen every session rather than when someone remembers the tool exists. One concrete instance of the class, found while reading for this: AUTO-GUARDRAILS.md §3 says "the strongest of the five" in a file with eight numbered sections.
>
> Bottom line: Measure reads before triaging. The 3,687 lines under `docs/*.md` are not equally expensive, and 646 of them are one parity plan that is already a dated record.

Having a test to specifically see if you wrote something that is likely to 'be wrong'

> Grumpy Sr. Engineer Opinion: If a test could detect wrongness you would run it and fix the wrongness, and you would have written a theorem prover by accident. What is testable is *shape*, and you already do that in four places.
>
> Mentor Sr. Engineer Opinion: This is already the repo's stated policy — AUTO-GUARDRAILS §6, "when a doc asserts something about the code, prefer a form a test can parse," justified by the audit that found five false claims where every one was in prose and every machine-checked claim was correct. So the ask is coverage, not a new mechanism.
>
> Assessment: Two unbuilt checks, by yield. **(a)** Every `src/sieve/...` path and every backticked dotted symbol appearing in `docs/**/*.md` resolves to a real file or attribute. Purely mechanical, an afternoon, and it catches exactly the class you mean — a doc naming a module that moved or a function that was renamed. **(b)** The one AUTO-GUARDRAILS §2 already calls "the most valuable unwritten check in this file": a pipeline saved from the GUI loads and executes identically in the CLI. Its own stated trigger — "the next item that touches serialization" — has already fired, since schema v3 landed `Edge.port`, `Project.detector`, and the pin fields.
>
> Bottom line: Write (a) now; it will fail on real rot the first time it runs. (b) is a real open item and is overdue against its own trigger.

We might need to revisit the auto guardrails

> Grumpy Sr. Engineer Opinion: The file is not stale — its whole design is to state its gaps in the same voice as its coverage, precisely because the previous version wrote unbuilt checks as though they existed and three of them read as done for two weeks. Asking to "revisit" a self-reporting document is asking to read it.
>
> Mentor Sr. Engineer Opinion: The correct revisit is narrow. Every OPEN/PARTIAL entry carries a **Trigger:** line, so the audit is one question — which triggers have fired? — not a redesign.
>
> Assessment: Against today's tree: §2's trigger (next item touching serialization) **fired** with schema v3 and no check was written. §4 already declares itself takeable — `filter_to_first_tick`, `knob_to_graphs`, and `knob_to_first_partial` all have producers now, and 9 of 11 budgets remain untimed in the regime the product is sold on. §7's trigger (a module calling a library that defaults to every core) is worth re-checking against the density surface moving off the GUI thread in `e394636`. §1's trigger has not fired; `workers/` still does not exist, and its stated resolution — settle it in the commit that creates `workers/` — is correct. So: one fired-and-unbuilt, one takeable-and-untaken, one to verify, one correctly dormant.
>
> Bottom line: A twenty-minute trigger audit, not a rewrite. It produces one open item — §2's GUI-versus-CLI parity check — which is the same item idea 5 lands on.

A way to automatically build SCAFFOLD.md, based on some stuff at the top of the file

> Grumpy Sr. Engineer Opinion: The failing test *is* the feature. Today, adding a module and forgetting its line breaks the gate and you notice. Generate the Built half and that becomes a silent auto-append — you would delete the only enforcement to save typing one line per module.
>
> Mentor Sr. Engineer Opinion: The tree is not the value of that file. The one-line annotation of what each module *owns* is, and that is the part no generator can produce and the part that actually decays. Generating paths while hand-maintaining annotations gives the worst split: the checked half automated, the unchecked half still manual.
>
> Assessment: There is a version that works, and it changes the source rather than the target. Make the module docstring's first line the single home for "what this module owns," and generate Built's annotations from it. That satisfies one-home-per-fact, keeps a human writing the sentence, puts the sentence where whoever edits the module will see it, and is consistent with CLAUDE.md already routing interface contracts to docstrings. Projected stays hand-written — it is an intention, and nothing in the tree can generate it. Keep a test that fails on a Built module whose docstring first line is missing or merely restates the filename.
>
> Bottom line: Generate from docstrings, not from the tree. Same tool as idea 13, which is the reason it is worth building at all.

Are there any hooks that could be useful that we are underutilizing?

> Grumpy Sr. Engineer Opinion: There is no `.claude/settings.json` in this repo, so "underutilizing" is generous — you are at zero. And a hook is how a preference becomes a thing that fires at 2am with no explanation attached, so the bar is a recorded incident, not a nice-to-have.
>
> Mentor Sr. Engineer Opinion: Two of the four candidates below map to incidents that actually happened here, which is the only justification that survives contact.
>
> Assessment: Ranked. **(1) SessionStart injecting `docs/.state.md`.** That file exists specifically to be the one-read primer and nothing guarantees it is read — highest value, lowest cost. **(2) Stop hook reporting `git status --short` plus unpushed commit count.** Recorded incidents: a 99-file uncommitted sweep found on arrival, 23 commits sitting local, and the work loop self-blocking on a dirty tree after a usage halt. **(3) PreToolUse blocking `git checkout --` / `git restore` on tracked files** — recorded incident: restoring one file from HEAD wiped in-flight feature edits. **(4) PostToolUse running `ruff format` on the single file just written** — removes a whole class of gate failure for near-zero cost. Nothing that runs the suite on a hook; the gate is the gate, and it is 31 seconds.
>
> Bottom line: Add 1 and 2 now. 3 only if it can be scoped narrowly enough not to block legitimate use. 4 is convenience. Nothing that mutates source beyond formatting.

Is there any part of the general workflow that would greatly benefit from doing mockups first?

> Grumpy Sr. Engineer Opinion: Your one mockup experiment produced a phantom regression. `mockups/seeker/` was never built, and it generated the bug report "we had a beautiful bottom bar previously but it's now gone" — a regression that never happened, which cost a session to disprove and ended with the mockup deleted. That is your evidence base.
>
> Mentor Sr. Engineer Opinion: It failed there because the question was interaction. Look at what actually churns in the bug list: stamp-as-default, hover-to-solo, click-through navigation, wheel-over-the-panel, crop handle hit-testing. Every one is *gesture semantics* — what a drag versus a click means, what happens at the frame edge — and no static picture can answer those. They need the real widget under a real hand.
>
> Assessment: Where a mockup is genuinely the cheapest instrument is *representation* questions: what should this quantity look like, when there is no existing form to copy. Two are live right now. Rule 6's rendering distinctions (absent versus zero, unexamined versus quiet), which `todo/coverage-and-detection-lanes.md` names as V1's standing failure and which three unbuilt widgets inherit. And the circular-signal problem in `todo/block-signal-free-measures.md`, which is explicitly blocked because "a value band and a heat ramp over an angle are wrap-around objects the GUI has no shape for." That item is stalled on a picture nobody has drawn — it is the single best candidate in the tree.
>
> Bottom line: Mockups for representation, never for interaction. And the operational rule the seeker taught: a mockup carries a date and is deleted when its item resolves, because the phantom regression came from a mockup outliving its question.


We should probably make more scripts to update state.md. Which are the most valuable?

> Grumpy Sr. Engineer Opinion: `.state.md` is 140 lines and its stated premise is orienting a session "in one read instead of four." Every addition moves it toward being the four reads. The budget here is *lines*, not scripts.
>
> Mentor Sr. Engineer Opinion: So the rule is: each addition is one line, and if it cannot be one line it has to displace something.
>
> Assessment: Ranked by what is load-bearing and currently invisible. **(1) Budget health, one line** — count in `IN_DEBT`, count in `WITHOUT_PRODUCER`, count actually timed (2 of 11 today). Rule 4 has the largest declared gap of any rule and reading it currently costs three files. **(2) Tree state, one line** — uncommitted files and unpushed commits, given the recorded incidents; this overlaps hook 2 in idea 8 and either one suffices, so pick one. **(3) `doc_drift`'s worst line**, so drift is seen rather than polled. **(4) Fired triggers** — deferred items whose `gated_on` names a now-complete item. Genuinely the most valuable of the four, but it cannot be built until `gated_on` is machine-readable, so it is the payoff of `todo/the-todo-dag-is-prose.md` rather than a script of its own. Not worth building: anything summarizing prose, which is how `.state.md`'s per-item lines already grew long enough to need rereading.
>
> Bottom line: (1) and (2), one line each. (3) is one more line. (4) is a consequence of an open item, not a separate script.

Is there a danger to spawning too many todos? How do we mitigate it?

> Grumpy Sr. Engineer Opinion: Yes, and you are in it — 12 open, 23 deferred, 81 completed. The deferred pile is nearly twice the open pile, a deferred item costs nothing to write, and each one is a claim about the future that ages whether or not anyone rereads it.
>
> Mentor Sr. Engineer Opinion: The failure mode is not volume, it is that writing the item feels like progress. The item file is where the thinking happens, so a well-written deferred item delivers most of the satisfaction of solving the problem and none of the solution — and then sits there being partially wrong.
>
> Assessment: Three distinct dangers, each with evidence in the tree. **(a) Silent triggers.** A trigger nobody polls makes the item a lottery ticket — demonstrated already, since at least one AUTO-GUARDRAILS trigger fired unbuilt and `.state.md` records several deferred items whose triggers fired 2026-07-28. **(b) Prose gates.** `gated_on` cannot be checked; that is the open item `todo/the-todo-dag-is-prose.md`, and it is the load-bearing mitigation for (a). **(c) Maintained items.** Read the `.state.md` lines for `todo/ledger-measurements.md` and `todo/block-signal-free-measures.md`: both now carry paragraphs explaining how the item's own premise changed after it was written. That is an item being maintained, a recurring cost nobody budgeted. Mitigations in order: make `gated_on` structured; add `deferred_on:` and treat an unfired trigger past ~30 days as a delete-or-promote decision rather than default-keep; hold a WIP limit on `status: open`. The strongest is deletion — completion-by-move already proves git is a fine home for item text, so a deleted deferred item loses nothing but its maintenance.
>
> Bottom line: The danger is specific and it is maintained items, not count. Take `the-todo-dag-is-prose` first, then make deferral expire by default instead of persist by default.

