# SIEVE Rewrite — Agent Handoff

You are implementing SIEVE, a video signal-processing tool, in a clean repo. A v1 exists in a separate folder - you may check against it (antscihub-optical-flow-detector) when necessary, but shouldn't without reason. The rewrite exists because while v1 shipped and served it's purpose, it became difficult to maintain — the kind of drift that happens when structure isn't enforced by tooling. This handoff is about building v2 so that structure enforces itself.

## What matters

SIEVE's value is speed of the interactive tuning loop. Users don't fall in love with the architecture; they fall in love with dragging a slider and watching graphs fill in faster than the video plays. Every design choice serves that, or it doesn't belong. The latency budgets in the architecture doc are the operational definition — they approximate product requirements, not aspirations.

The second thing that matters is that v2 stays editable as it grows. v1 didn't. The path from a clean codebase to an unmaintainable one is short and mostly invisible until you're already down it, so the goal is to build the observations that make drift visible early, and let the tooling do the enforcement so you can spend your attention on the interesting problems.

## Build the guardrails, then work inside them

Rather than checking against constraints every time you write code, build tools that check for you. 

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

## Start here

Read the docs. 

