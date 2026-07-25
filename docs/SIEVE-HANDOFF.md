# SIEVE Rewrite — Agent Handoff

You are implementing SIEVE, a video signal-processing tool, in a clean repo. A v1 exists in a separate folder - you may check against it (antscihub-optical-flow-detector) when necessary, but shouldn't without reason. The rewrite exists because while v1 shipped and served it's purpose, it became difficult to maintain — the kind of drift that happens when structure isn't enforced by tooling. This handoff is about building v2 so that structure enforces itself.

## What matters

SIEVE's value is speed of the interactive tuning loop. Users don't fall in love with the architecture; they fall in love with dragging a slider and watching graphs fill in faster than the video plays. Every design choice serves that, or it doesn't belong. The latency budgets in the architecture doc are the operational definition — they approximate product requirements, not aspirations.

The second thing that matters is that v2 stays editable as it grows. v1 didn't. The path from a clean codebase to an unmaintainable one is short and mostly invisible until you're already down it, so the goal is to build the observations that make drift visible early, and let the tooling do the enforcement so you can spend your attention on the interesting problems.

## Build the guardrails, then work inside them

Rather than checking against constraints every time you write code, build tools that check for you. 

Once those are in place, trust them and move fast. The point of building the guardrails is exactly so you don't have to keep the constraints in your head. Build new ones as needed - use your judgement.


## Start here

You were probably told to build one thing. If something else needs to exist first, or be fixed first, or if it is in conflict, if you are at least 95% sure what I want, just do it.

Look at the ARCHITECTURE.md file for how it fits in. If there is something in the SCAFFOLD.md for where it should live, put it there. SCAFFOLD is a crude map - you don't have to follow it exactly, but it is designed to approximate the separation of responsibility the final product has.

For different steps, the following in the src\sieve\docs should be updated if touched:

- `FILTER_CONTRACT.md` — the interface implemented by each filter
- `PIPELINE_SCHEMA.md` — the serializable DAG artifact (project file / HPC handoff)
- `CACHE_KEY_SPEC.md` — content-addressed cache key derivation
- `WORKER_PROTOCOL.md` — subprocess IPC, shared-memory frame transport
- `BACKEND_DISPATCH.md` — CPU/GPU/threading policy
- `GUIDANCE_FORMAT.md` — the markdown convention colocated with filters
- `PREVIEW_SEMANTICS.md` — warmup handling for temporal filters in preview
- `REVIEW_OUTPUT_SPEC.md` — Step 7 review-mode data contract