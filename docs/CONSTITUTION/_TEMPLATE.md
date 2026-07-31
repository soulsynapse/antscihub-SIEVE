# INV-<n> — <Name>

**Holds:** <the property that must be true at all times, stated as a fact about the
system, not as an instruction. One sentence.>

**Bearer:** <the noun this constrains — *derived value*, *edit*, *contended resource*,
*module*, *contract*. Then one clause saying why that noun exists under any
implementation. If the bearer is a today-noun (*frame*, *video*, *widget*, *GUI*, *tab*,
*thread*, *filter*, *pixel*, *rectangle*, `__init__.py`), this invariant is contingent on
that noun and the clause states the condition that expires it instead — "true while
elements are addressable by index". An unmarked contingent claim in a permanent document
is the failure this field exists to prevent.>

**Breaks if violated:** <what SIEVE loses. Concrete and specific — "the user cannot
answer X", not "quality degrades". If you cannot name the loss, this is not an
invariant and belongs in CROSSCUTTING.md.>

**Depends on:** <IDs of the invariants whose *form* this one is only valid under, each
with the clause that makes it a dependency — "INV-3, because shedding is what makes
staleness a display state rather than an error". Import direction is not the test: two
contracts can import nothing of each other and still be unable to change independently.
`none` is a real answer and is rare; most invariants here have at least one edge. An
unwritten edge is a rewrite waiting to be discovered.>

**Scope:** <which parts of the tree this governs, as globs.>

---

## <ID> — <Rule title, imperative, one line>

**Rule:** <One sentence. MUST / MUST NOT / SHOULD / MAY, used in the RFC-2119 sense.
One claim per rule — if it needs an "and", split it.>

**Bearer:** <only when narrower than the invariant's. Omit to inherit.>

**Rationale:** <Why this exists, and what went wrong without it. Cite the charter
section or the specific past failure. An agent that understands the reason handles
the case the rule did not anticipate; one that does not will satisfy the letter.>

**Depends on:** <rule IDs, same test as above. Omit if none.>

**Example:**

```python
# do
<the canonical form. This should be copy-pasteable and should come from real code
in the tree, not be invented for the doc.>

# don't
<the failure this rule prevents, written the way it actually appears.>
```

**Adherence:** <the rung, then the mechanism, then the path.

`Rung 1 — unrepresentable.` The wrong thing cannot be written. Name what refuses it.
`Rung 2 — generated.` The thing is not authored at all; it derives from a declaration.
Name the generator.
`Rung 3 — default path.` The easy way is the correct way. Name the reference member an
agent copies.
`Rung 4 — checked after.` CI fails and the work is redone. Name the test.

A rung-4 rule is a placeholder for a rung-1/2/3 mechanism nobody has built, and should
read that way. Write the rung you actually have, never the one you intend: a rule
claiming enforcement it does not have is worse than one that admits it.

`Rung 5 — reviewer judgment` exists and is capped. See CONVENTIONS.>

**Latitude:** <optional. Where an agent may act without asking, and where it must
stop. Present when the rule would otherwise read as a blanket prohibition and cause
defensive over-engineering.>

---

## <ID> — <next rule>

...

<!--
CONVENTIONS

ID scheme: one letter per invariant file, then a number — D-1 (DAG), M-1
(Measurement), V-1 (Visibility), X-1 (crosscutting). IDs are permanent. A retired
rule is struck through in place with a one-line reason and the date; it is never
renumbered and never deleted, so that references in commits and runbooks stay valid.

One rule per claim. Rules are cited by ID from runbooks, PR descriptions, and review
comments. Runbooks state procedure and cite IDs; they never restate rule text,
because the two copies will diverge.

ADHERENCE. A principle whose adherence requires knowing the principle has already
failed — the population is agents, and an agent that has lost context will not recall a
rule, it will do whatever the tooling makes easy. Rungs 1 and 2 do not need the rule to
be known. Rung 3 mostly does not, because copying the nearest working example is what a
context-free agent does anyway. Rung 4 needs the rule known *after* the work, which is
the write-fail-rewrite loop and is why it is the floor rather than the target.

Prefer moving a rule up a rung to writing a better rule. Most rung-4 rules here have a
cheaper rung available and nobody looked.

A rung-1 refusal states the alternative. Refusing and handing over the fix costs an
agent nothing; refusing alone costs it a search, and the search is where it invents
something. `core/filter_base.py`'s element-meaning refusal is the model: it names both
legal answers and says there is no default on purpose.

Rung 5 is a budget, not a fallback. If every rule may fall back to judgment, every rule
will. The rules that are irreducibly a reading — "name the change that would be confined
to this folder" — are enumerated once in CROSSCUTTING.md and that list is closed. A rule
landing at rung 5 because nobody built the mechanism is debt and says so; a rule at rung
5 because it cannot be mechanized is on the list or it is not allowed there.

DEPENDS ON. The invariants are a graph, not a list. The nodes are the properties; the
edges are which properties are only valid in the presence of which others. Two contracts
with no import relation can still be unable to change independently, and that pair is what
produces a rewrite nobody predicted. Write the edge when you notice it, even if the rule
it points at does not exist yet.

Order rules within a file by how often an agent will hit them, not by importance. Within
that, rung 4 and rung 5 first — those are the ones an agent must actually know.
-->
