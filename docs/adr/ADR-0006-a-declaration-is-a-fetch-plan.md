---
title: A declaration is a fetch plan
group: Substrate
position: 6
status: settled
decided: 2026-08-23
---

A step declares the inputs it admits — which frames, which spans of which
upstream output, at which forms — as a function of the position being
computed, and that declaration exists to schedule fetching rather than to
conserve memory. A re-fetch the declaration predicted is a defect. A re-fetch
it could not have predicted is only a fetch.

The declaration is a set rather than a reach, because those are different
numbers whenever a step's inputs are sparse: something wanting three fixed
lags and the current frame holds four and spans thirty-one, and one integer
cannot be both. It is a pure function of position rather than a
pin-and-release protocol, so there is nothing to leak when a step is
switched off or the playhead jumps, and the store asks what the active set
needs now instead of remembering what it was told.

Read at one position the set is what must be resident; over the run of
positions about to be served it is what may not be evicted; one ahead it is
what to fetch next. Honouring the point set as the working set is
pathological for sparse inputs — a fetch per offset per position served,
worse than having no declaration at all.

The memory argument is the one that suggests itself and it does not survive
measurement: over consecutive positions the union closes the gaps between
sparse offsets, so retention converges on what a plain window would have
held, and where it stays sparse the playhead is stationary and nothing is
under pressure. Measurements are in `experiments/tool-experiments/`. What
cannot be recovered by any locality rule is the fetch: a jump to a position
whose inputs sit far behind it needs specific distant things that nothing
local would predict, and without the declaration they are discovered at the
moment they are wanted and paid for then. An ADR justified on memory grounds
would license the wrong machinery later — this tree's recorded failure of
defending a budget that turned out to be an artifact (`docs/decode/ideas.md`).

The declaration is over inputs, not frames. A step downstream of another
consumes spans of its output and has the identical failure available:
reading a row that was never computed as though it were a computed zero.
Coverage is recorded rather than inferred, and a downstream declaration
names the spans it requires so the same question — is this present — is
asked before the value is used rather than after it has propagated.

Two things make it enforceable rather than aspirational. A step is handed
exactly what it declared, so reaching for an input it did not name fails
immediately and in its own code — an inaccurate declaration cannot quietly
cost fetches. And the predicted re-fetch is counted: a re-fetch of something
a declaration said was coming is a defect with an address, where previously
it was indistinguishable from the store being slow — the single number that
makes the arrangement falsifiable.

The accepted cost is that a declaration can be honest and still exceed what
exists. That is not a fault in the step; it is a fact about which execution
strategies remain, and the correct response is to run the work as an ordered
pass that never needs random access rather than to pretend it can be
interactive. What is refused is inferring the requirement from behaviour,
because a requirement inferred from a traversal is a property of that
traversal and the next one disagrees.
