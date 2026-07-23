# Repository instructions

## Performance work

When the user asks to make anything faster:

1. Benchmark the relevant behavior before changing it.
2. Make the smallest performance change that addresses the measured behavior.
3. Run the same benchmark afterward and report the before/after comparison.
4. Add the benchmark report to `findings/` and add a listing for it to
   `findings/.index.md`.

Each benchmark report must:

- start with a BLUF summary;
- follow the BLUF with the detailed benchmark setup, measurements, comparison,
  and interpretation; and
- include a section titled
  `Potential ways this finding could be invalid now or later`.

Do not claim a speedup without the before/after measurements.


## Handoffs from the oracle repo
Handoffs are generated from an oracle repo of the first draft of this project and do NOT know the current state of the project. This means that there are likely inconsistencies, or overstrong framing in the spirit of "do not do this thing [that doesn't even exist in this repo] because the agent wrote that into the handoff because I implied something in those lines.

You should report inconsistencies in the handoffs (always) and ask me about it unless you are 95% certain what I would say the answer is (when appropriate: when you are below 95% confident in the right answer).

The first thing you should do is look at the handoff and the review, find what corrections to make, report them, then ask if you can go ahead and make those corrections across the files to match the current repo. You should state that the file was reviewed and updated with date and time at the top so you know when.

You should update the .isolate-state-divergence.md to help the oracle not make those mistakes to begin with.

As we get further and further down the list, the handoffs will deviate more and more from the current repo as the rewrite diverges from the oracle; this is normal, even with the state updates file.

## Oracle hints
Some handoffs might ask for something that seems impossible. When this is the case, you can craft a prompt for me to ask the oracle repo how to achieve this. I'll pass the answer back to you.

## Follow ups
Once a given task is completed, review `docs/next_steps.md` for work that would benefit from your current context and update it with concrete unfinished work or proposed follow-ups. If there was a significant finding or antipattern, you can propose it as a decision if it will make the long term health of the repository better. This is deliberately broad - when you notice some inefficiency that would annoy a senior developer for not following standard practice, you can note it, and say if it truly applies in this context or if it is theoretical-senior-dev-gripe only. You can also add things to the candidate section of optimizations.md if you found any.

## Indexes
Indexes are directories that group contents of a doc category based on their utility:

1. Results of hypothesis testing
2. Findings that were counterintuitive enough that they were arrived at at least once
3. Patterns to follow
4. Antipatterns

When you make decisions off the docs, you should inform the user how that guided your behavior so that old documentation that no longer holds doesn't contaminate the current live implementation. You should also flag any that seem like they shouldn't be the case so the user can evaluate them.

## Check ins
After a functional change or feature, do a commit following conventional commit standardization.
