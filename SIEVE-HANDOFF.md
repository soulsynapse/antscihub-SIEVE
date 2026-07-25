# SIEVE Rewrite — Agent Handoff

You are implementing SIEVE, a video signal-processing tool, in a clean repo. A v1 exists in a separate folder - you may check against it (antscihub-optical-flow-detector) when necessary, but shouldn't without reason. The rewrite exists because while v1 shipped and served it's purpose, it became difficult to maintain — the kind of drift that happens when structure isn't enforced by tooling. This handoff is about building v2 so that structure enforces itself.

Read every file under `docs/` before writing code — architecture doc, ADRs, specs, vision. Those are the considered decisions; this prompt is orientation on top of them. Where something here seems to conflict with the docs, the docs win; flag the conflict. However, the docs are written over time, and might have some internal inconsistencies or inaccuracies. Do a test against the objectives, propose an ADR, and update the docs when approved.

## What matters

SIEVE's value is speed of the interactive tuning loop. Users don't fall in love with the architecture; they fall in love with dragging a slider and watching graphs fill in faster than the video plays. Every design choice serves that, or it doesn't belong. The latency budgets in the architecture doc are the operational definition — they approximate product requirements, not aspirations.

The second thing that matters is that v2 stays editable as it grows. v1 didn't. The path from a clean codebase to an unmaintainable one is short and mostly invisible until you're already down it, so the goal is to build the observations that make drift visible early, and let the tooling do the enforcement so you can spend your attention on the interesting problems.

## Build the guardrails, then work inside them

Rather than checking against constraints every time you write code, build tools that check for you. In the first working commits, put in place:

- **Layer enforcement.** The architecture doc defines a layered dependency model. Encode it as an import-linter contract (or equivalent) in CI. Once it's there, the kinds of cross-layer entanglement that made v1 hard to change simply won't compile.
- **Latency benchmarks in CI.** pytest-benchmark on the interactive-loop budgets — scrub, slider-to-repaint, graph fill rate against playback. A regression beyond the stated margin fails the build. This is your defense against the gradual drift that's otherwise invisible until users notice.
- **Filter-contract property tests.** Hypothesis, from the first filter onward. Any valid params → output shape and dtype match declaration, no NaN unless declared, deterministic filters produce byte-identical output. This is what keeps the contract honest as filters accumulate.
- **A lightweight code-health check.** Build a small tool (a Nox session, a script, whatever fits) that flags things worth a second look: files that have grown unusually large, functions that touch more than one layer, modules with high fan-in and fan-out, tests that grew brittle. Not a linter with hard rules — a report you run periodically and act on when something stands out. Design it so it's cheap to extend as you learn which signals actually matter for this codebase.

Once those are in place, trust them and move fast. The point of building the guardrails is exactly so you don't have to keep the constraints in your head. Build new ones as needed - use your judgement.

## Sequencing

Build vertically. One decode path, one filter, one worker, one graph, one slider — end to end, rough but real — before widening any single layer. v1 already proved what the vertical slice needs to feel like, and that knowledge is more valuable than a beautiful substrate built in isolation.

A working sketch:

- Skeleton and guardrails (Ruff, Pyright, pytest, import-linter, Nox, benchmark harness, code-health check).
- Pre-pipeline loop: open, scrub, cut replicate, background materialize. This is where the tool first has a feel, and where the latency budgets first get tested against reality.
- One filter end-to-end. Intensity is the simplest; it exercises the full stack without hiding behind complexity.
- The rest of v1's filter set (change energy, LK optical flow, windowed-block, threshold, scalogram band). This is where abstractions get stressed; refactor the contract here if it resists, not after ten filters exist.
- Everything else — caching, compaction, HPC handoff, backend dispatch, guidance, determinism CI, review mode — after v1 parity, sequenced by what actually blocks users.

Adapt this once you see the repo. The shape matters more than the specifics.

## Building well as you go

While you're building, keep an eye on two things beyond correctness:

**User experience.** Some kinds of code hurt the user without hurting any test — a silent worker roundtrip on a UI operation, a decode that blocks the event loop, a filter that materializes when it could stream, a widget that rebuilds on every parameter change instead of updating in place. Test for these explicitly when the shape of the code suggests they're possible. The latency benchmarks catch the big ones; smaller ones need judgment. If you're writing something that touches the interactive loop, ask what would happen if it were 5× slower and whether the test suite would notice.

**Maintainability and product trajectory.** After finishing a piece of work, briefly assess: is this the code a future contributor (or future you, or future me) would want to change when the next requirement arrives? Where would it resist change? Note anything worth revisiting in `NOTES.md` — not as a promise to fix, just as an honest map of where the debt is. The architecture reserves space for a lot of future capability (HPC, backends, guidance, review mode); when you write something today, briefly consider whether it's compatible with those directions or whether it silently forecloses them.

Neither of these needs to slow you down. They're a pass over what you just wrote, not a filter on what you write.

## Rule of three before abstraction

Don't build a plugin system before three plugins, a DAG executor before a fork, backend dispatch before two backends, or a cache before caching is a measured bottleneck. v1 was fast without most of these. The architecture reserves space for them; the code doesn't need them yet. Concrete first, abstract on the second or third caller.

If a decision would shape the codebase in a way that's hard to reverse later, that's an ADR — draft it as `Proposed` in `docs/05-adr/` and either implement against it briefly while awaiting review, or flag it explicitly. If it's a local implementation choice, just make it.

## Staying in sync

I trust you to make most decisions. What I need is to be in the loop on the ones that shape the product.

**Stop and wait for me:**

- After the pre-pipeline loop works end to end. Show me a screen recording — this is the earliest point where the tool's feel is testable, and feel is the thing I need to sign off on.
- At v1 parity. Full v1 pipeline running on a canonical clip. Show me the tool running.

**Flag it and keep going, but make it visible:**

- New top-level dependencies not covered by an ADR.
- Deviation from an existing ADR (draft the superseding ADR).
- A latency budget missed where the fix is architectural rather than local.
- Changes to load-bearing contracts (filter contract, pipeline artifact, worker protocol) once they have more than one implementer.

Everything else, use your judgment.

The lightweight coordination mechanism is a single `NOTES.md` at the repo root — what's in progress, what's deferred and why, open questions for me, and observations from the code-health checks that seem worth remembering. Two-line entries, updated as you go. Draft ADRs handle the decisions; PR descriptions carry the narrative for individual changes; `NOTES.md` is the connective tissue.

## Practical notes

- Build the GUI early and ugly. Polish it last. But measure its interactive latency from the first day it exists — panels can look wrong, but the scrub cannot be slow.
- One end-to-end smoke test that grows with the vertical slice, rather than a new test per phase. After the pre-pipeline work it covers open-scrub-replicate; after first filter it covers a filter run; at parity it runs the full v1 pipeline.
- Coverage: `core/` is pure and should be well-tested. GUI panels are not — chasing coverage there produces brittle tests. Test behavior, not lines.
- Determinism CI when it's cheap to add. If you can byte-compare a canonical clip early, do it. If it requires the full pipeline to exist first, defer it and note it in `NOTES.md`.


## Context management.

Start a session by drafting the scope to the next checkpoint that optimally maintains your operational context without letting it grow too big. This should be a running to-do, which you edit as the last thing of the session. Check in, then the last line should say you're ready to compact. Give me the compact cmd written out to optimize the next session. You can utilize an LLM wiki under 06-ops using best practices, or document a run book. No docs you write should be 

## Documentation

All documentation should NOT be in the imperative. Docu voice should be written in the descriptive voice. It should follow the epistemic status EXPLICITLY, often and freely, where relevant. You can write guardrail scripts to ensure this. The tags are [STABLE] [ASSUMPTION] [INTENT] [STALE WHEN] [OPEN QUESTION].

Examples:

"The cache expires after 60s."	vs "[INTENT] cache TTL: 60s (see config.ts). Confirm the runtime value hasn't drifted."

If I have written 'always', 'never', 'must' etc flag it so I can correct it.

## Start here

Read the docs. Write the plan or edit it for best practices. Note what you need feedback on. Set up the guardrails as your first working commits — layer enforcement, benchmarks, property-test scaffolding, code-health check. Then produce your phase-1 plan as a draft ADR (if it involves decisions worth capturing) or a `NOTES.md` checklist (if it's execution). Confirm with me before writing feature code.

If the repo state or the docs suggest a different sequencing than what's here, say so in your first message. This handoff is orientation, not a script.

