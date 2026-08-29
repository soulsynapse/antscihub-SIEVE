---
title: A key carries a version
group: Substrate
position: 10
status: settled
decided: 2026-08-28
---

A durable key folds, beside the parameters the answer depends on, a version
saying which definition of the step those parameters were fed to — declared
like the rest, folded unconditionally, and bumped by the author when the
code's answer changes, never derived from the code. A third-party solver an
answer depends on belongs in `params`, not in the version, because a version
can only honestly cover what its author can see change.

Without a version, two runs either side of an edit to a `field` are
different answers under one name, and nothing is in a position to notice —
the same silent-reuse defect ADR-0005 records, arrived at from the code side
rather than the data side.

The null option — no version at all — is Make's model: a target depends on
its sources and never on the recipe. The workaround culture that fills the
gap (`make clean`, clean builds on suspicion) is what a tuning loop cannot
afford, since wiping stored series forfeits precisely the accumulated work
the loop exists to reuse. Workflow systems nearer this tree's shape (Luigi
is the clearest case) converge on the same fix by hand: a version parameter
folded into the task's identity, bumped when the logic changes. This
decision adopts that fix on purpose.

The derived option — hash the code into the key — over- and
under-invalidates simultaneously. joblib hashes the decorated function's
source: a rename invalidates answers that did not change; an edited helper
outside the hashed body reuses answers that did. Nix and Bazel make hashing
correct by making hermeticity the product and paying rebuild-on-formatting
as the going rate. SIEVE is not buying hermeticity; its product constraint
is a loop where stored work is the asset.

The accepted cost is that nothing checks a bump happened. What is refused is
the hash as *arbiter*, not as *tripwire*: a check in `checks/` notices when
a step's text moves against a recorded baseline, and the author says whether
the answer moved — by bumping or by re-recording, both explicit acts. The
hash decides nothing and never reaches a key. The bet behind the cost is
that a change to a step's answer is a rare, authored, reviewed event in this
tree's own commits — where a missing bump can at least be seen, which a
wrong hash never is.
