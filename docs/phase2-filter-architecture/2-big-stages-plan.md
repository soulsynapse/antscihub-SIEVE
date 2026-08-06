# Phase 2: Structuring for future filter development

**End goal:** three years of ordinary churn from now, with ~30 working filters
in the repo, adding filter #31 touches only that filter's own directory — and if it requires new functionality, the capability to safely add that in without breaking everything else. Nothing else in the repo has to be edited, re-read, or re-reasoned about to add it.

Thus, below is a list of what is reasoned to be **what must be true for SIEVE to absorb a filter it was not designed for — such that the cost of adding the 31st filter is equal to or less than the cost of adding the 1st.**

## Using the MCP to queue tasks
During any given pick up, you can do one of three things:

1. Implent a single unfinished plan step.
2. Add a new problem statement and steps.
3. If no actionable item remains, drain the rest of the queue. This should only be done when there isn't a clear way forward.

## Working with this plan:
1. Verify a problem that is structurally blocking to the end goal. You can look to the 1-big-stages-lookahead.md for ideas, and 0-big-stages-identification.
2. State the problem *that specifically blocks the end goal* with **IF**, **THEN**, **RESULTING IN**. Each problem statement gets a h2 numbered entry, the IF/THEN/RESULTING IN is right below the problem statement header, and the rest of the info for addressing the problem lives with that entry.
3. Under the IF THEN RESULTING IN problem list (and there can be multiple), you draft a solution very generally, such that all the if-then problem statements are addressed. Each if/then/resulting in statement should live directly below the solution proposition, with checkmarks for which of them they address. A solution doesn't address all the if/then statements doesn't go forward unless I say it is acceptable, but one that does, can go forward.
3. Then make a list of steps, and a completed when statement. Steps should be scoped to 1 chunked deliverable that can be done in under 50 steps.


---






