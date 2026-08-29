---
title: A key carries a version
group: Substrate
position: 10
status: settled
decided: 2026-08-28
---

A durable key folds, beside the parameters the answer depends on, a version
saying which definition of the step those parameters were fed to — declared
like the rest, folded unconditionally, including for a step with no
parameters at all, and bumped by the author at the moment the code's answer
changes, never derived from the code. What the code *calls* is not the
code: a third-party solver an answer depends on belongs in `params`, which
holds what the answer depends on and not only what a user set.

What this closes is the one hole the key had left. Everything a stored
value depends on as *data* was already folded — the source, the form, the
parameters, the input actually consumed (ADR-0005) — and nothing named the
code that turned those inputs into the number. Two runs either side of an
edit to a `field` were different answers under one name, and a series the
first wrote was handed to the second, covered, with nothing anywhere in a
position to notice: the same silent reuse the downstream-parameter rule
refuses, arrived at from the other side. Like the provenance defect
ADR-0005 records, it is invisible to every cost instrument this tree runs,
because a stale value read back costs even less than a right one computed.

The null option — no version at all — has a known ending, because build
systems have run it at scale for decades. Make's model is exactly a key
over inputs with the rule outside it: a target depends on its sources and
never on the recipe that builds it, and the workaround culture that grew in
that gap — `make clean`, clean builds on suspicion, "delete the cache and
rerun" as the first move of every debugging session — is what a tuning
loop cannot afford, since wiping stored series on suspicion forfeits
precisely the accumulated work the loop exists to reuse. The workflow
family nearer this tree's shape (Luigi is the clearest case) keys a task by
its name and parameters, reuses any existing target under that identity,
and users of those systems converge on the same fix by hand: a version
parameter folded into the task's identity, bumped when the logic changes.
This decision is that fix adopted on purpose rather than reinvented after
the first stale series.

The derived option — hash the code into the key — fails in both directions
at once, and that is also observed rather than predicted. joblib's memoiser
hashes the decorated function's own source: a rename or a moved comment
invalidates answers that did not change, while an edited helper outside the
hashed body reuses answers that did — one mechanism, over- and
under-invalidation together. Snakemake grew code-change rerun triggers and
had to make them optional, because invalidation at the granularity of
"the text moved" forces reruns nobody wanted. Nix and Bazel do make
hashing the whole build description correct — by making hermeticity the
product, sealing every dependency into the hash's reach and paying
rebuild-on-formatting as the going rate. SIEVE is not buying hermeticity;
its product constraint is a loop where stored work is the asset. A hash
over a step's bytecode here reproduces the double failure at smaller
radius: it invalidates a rename that changed nothing and still misses a
solver changing under a step whose own bytes did not move.

That last case is why the boundary sits where it does. A version can only
honestly cover what its author can see change, which is this tree's code;
an upgrade inside a third-party solver changes the answer without touching
any line an author would bump beside. So the solver's identity belongs in
`params` — which holds what the answer depends on, not only what a user
set — and the version covers the remainder. Declared-not-derived is
also how mature systems mark semantic identity wherever machinery cannot
judge equivalence: a pickle protocol, a file-format version, a schema
migration number are all an author asserting "this is a different answer
now", because no hash distinguishes a change in meaning from a change in
spelling.

The accepted cost is that nothing checks a bump happened. A `field` edited
without one names the series it just stopped agreeing with, and the store
hands back the old numbers as covered — `series.py` names that failure
where the next producer will read it. What is refused is the hash as
*arbiter*, not as *tripwire*: a check that notices the tools' text moved
against a recorded baseline detects the missed bump while leaving the
author to say whether the answer moved — by bumping, or by re-recording
the baseline, both explicit acts. That check is this ADR's contract in
`checks/`, under the convention that a settled ADR ships at most one
named check whose failure cites its number; the hash it holds decides
nothing and never reaches a key. That is the
price of refusing both false invalidation and a hermeticity this project
has no use for, and the bet behind it is that a change to a step's answer
is a rare, authored, reviewed event in this tree's own commits — a place
where a missing bump can at least be seen, which a wrong hash never is.
