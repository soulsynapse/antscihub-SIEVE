# ORGANIZATION

ARCHITECTURE answers how data moves and what an operator owes the engine. This
document answers where code lives, how someone finds it, and how a folder that
stopped earning its place gets removed. Those are different questions with
different enforcement: ARCHITECTURE's rules are checkable by machine, and most
of the rules here are judged by a reader. Sections §4.4 and §5.3 are the
exceptions — they are meant to become CI checks. Until they exist, everything
here is enforced at review.

The criterion is Parnas, *On the Criteria To Be Used in Decomposing Systems
into Modules* (1972): a module is a home for a decision that might change, not
for a step in the processing sequence. Supporting vocabulary is Ousterhout,
*A Philosophy of Software Design* (deep vs shallow modules) and Lakos,
*Large-Scale C++ Software Design* (physical design, levelization). The
package-per-capability instinct is old and unremarkable — Django apps, Rails
engines — and is not being invented here.

## 1. A folder exists because it hides a decision

The legitimacy test: name the change that would be confined to this folder. If
you cannot name one, or the honest answer is "several unrelated ones," the
folder is not a module.

1. A secret is a decision that can plausibly change on its own: a wavelet
   basis, a decode backend, a storage layout, a scheduling policy, an on-disk
   format. Changing it should touch one folder and no callers.
2. Sequence position is not a secret. "Runs early," "is called by the GUI,"
   "is low-level" describe where code sits in a call chain, and decomposing on
   that basis is the failure Parnas 1972 is about.
3. Breadth is fine; incoherence is not. A bag of thirty filters is a good
   module if the thing it hides is *how a filter is implemented* behind one
   declaration the engine reads. Thirty unrelated helpers sharing a category
   name hide nothing.
4. One folder, one secret. If two changes would each touch half the folder and
   neither touches the other half, it is two modules wearing one name.

Forbids: folders organized by when code runs or by how abstract it feels.

## 2. A folder is named so the thing can be found

Legitimacy is not enough. A module nobody can locate gets reimplemented, and a
bespoke reimplementation hidden in the wrong place is the most expensive
outcome in this codebase.

1. Names state a capability, not a position or a taxonomy. `decode`, `storage`,
   `detect` name what is hidden. `core`, `backend`, `common`, `utils`, `helpers`
   name a position in the stack or a shrug, and each is a standing invitation
   to accumulate.
2. When you want to add a kind of thing, there is one obvious folder it goes
   in, and the things that make up that kind live next to it — the operator,
   its declarations, its fixtures, its reference example.
3. Many folders is the expected end state. A tool of this class is a large
   grab-bag of capabilities, and a task reaching into six bags at once is
   normal, not a smell.

Forbids: a correct module with a name that guarantees nobody looks inside it.

## 3. Both tests, and what failing each costs

Every folder passes §1 and §2. The two failures are not equally serious and do
not get the same remedy.

1. **Fails §2 only** — real secret, bad name or bad location. Cheap: rename or
   move. No argument required; anyone may do it.
2. **Fails §1 only** — findable bin. This is the junk drawer, and it is the
   expensive one, because the name reads as legitimate while the contents
   accumulate. Remedy: dissolve. Each member moves to the folder whose secret
   it actually belongs to, or becomes its own module if it turns out to hide
   something. The remedy needs a trigger or it is one nobody schedules: a folder
   carrying a bin warning (§3.3) across some number of commits incurs a
   structural debt, and when that debt comes due the folder is defended in a line
   or dissolved (STRATEGY §3.5). That is what keeps creation free under §6
   without free creation becoming a target — the check sits on the folder's
   subsequent behaviour rather than on the act of making one, and a folder that
   never acquired a second importer is exactly what the computable signals
   detect. The number of commits is a guess and is held open with its own trigger
   (STRATEGY §9) rather than asserted here.
3. Signals a folder is a bin: members with no importers in common; a member
   whose only caller is one specific call site; a docstring that lists contents
   rather than stating a secret; a name from §2.1's second list; growth without
   any change ever being confined to it. The first two are computable from the
   import graph and belong in the §5.3 checker as warnings — otherwise §1 stays
   a rule nobody schedules time to apply. The rest are read.
4. Dissolving is the normal end of life for a folder, not a reproach. A bin
   that existed for six months and then distributed cleanly did its job as a
   staging area.

Forbids: a folder surviving on the strength of its name.

## 4. The surface is `__init__.py`

A package's `__init__.py` is its public API and its advertisement. This is the
mechanism that makes §2 real rather than aspirational. The filename is Python's
and expires with it; the durable bearer is the package surface — one declared
place stating the secret and the exports, whatever a language calls it (STRATEGY
§6.5). What follows is stated over the file because the file is what a reader
opens.

1. `__init__.py` states, in one line, the secret the package hides, then
   exports the names callers are meant to use. It is the first thing read and
   the cheapest place to prevent reinvention.
2. Exported surface should be small relative to what the package contains —
   Ousterhout's deep module. A package whose exports enumerate its internals
   hides nothing and has only added a path segment.
3. Reaching past the surface into a submodule means one of two things: the
   surface is wrong and should export what you needed, or you are depending on
   an internal that was free to change. Both are resolved by editing
   `__init__.py`, never by importing deeper and moving on.
4. **CI-checkable:** every package has a purpose line and a declared export
   list. A package with neither is not announcing itself and fails the build.

Forbids: packages that are directories rather than modules, and imports that
reach through them.

## 5. Dependencies point one way

Physical design, in Lakos's sense: the import graph is part of the design and
is allowed to constrain it.

1. Contracts sit at the bottom and import nothing of ours. The engine and the
   operators depend on contracts. The GUI and CLI sit at the top and are
   depended upon by nothing.
2. No cycles between packages, at any level. A cycle means the two packages
   share one secret and should be one module, or that a shared secret needs
   extracting into a third.
3. **CI-checkable:** import direction and acyclicity. This is the one
   organizational property that can be verified exactly, so it is verified
   rather than reviewed.
4. A folder that everything imports is either genuinely foundational — in which
   case it has one secret and a small surface — or it is a bin that grew by
   convenience (§3.2). The import count alone does not distinguish these; the
   §1 test does.

Forbids: the GUI becoming a dependency of the thing it displays, which is how
the display and the pipeline drift apart.

## 6. New homes are proposed freely

Proposing a folder is cheap and should stay cheap, including for agents working
without much context. This is safe only because §3 exists.

1. When something has no obvious home, propose one. Do not park it in the
   nearest folder that will accept it, and do not leave it beside its single
   caller.
2. A premature folder is a visible, locatable mistake with a known remedy. A
   bespoke function hiding inside an unrelated module is invisible and gets
   reimplemented by the next person who needs it. The first failure is strictly
   cheaper, and the asymmetry is why the bar for proposing is low.
3. A proposed folder states its secret in `__init__.py` at creation (§4.1).
   That sentence is what later makes it evaluable — a folder that never claimed
   a secret cannot be shown to have lost it.
4. Nobody needs permission to apply §3.1. Re-homing is maintenance.

Forbids: reinvention through the path of least resistance, and organizational
paralysis as the alternative.

## 7. Not reinventing, in order

The sequence when you need something: read the module guide (§8), then the
package surfaces (§4.1), then the reference implementation for that kind of
thing, then propose a home (§6).

1. Each bag holding a kind of thing carries a minimal reference member, in
   tree, exercised by CI. It is the runbook. Prose instructions for adding a
   filter drift silently; a reference filter breaks the build.
2. Minimal is not the same as trivial. The set must cover the hard shapes — one
   member carrying state across frames, one taking more than one input, one
   changing rate, one declaring a two-sided window, one reducing across a
   collection (ARCHITECTURE §1.12) — because a single easy member
   demonstrates only the easy contract, and the hard contracts are exactly where
   someone reinvents rather than reuses. The two-sided window is the shape whose
   absence had the highest price last time: an operator needing lookahead and
   unable to declare it gets built outside the graph (ARCHITECTURE §3.1), and a
   reference set that cannot demonstrate the declaration is how the next author
   concludes the same thing. The five are an inventory of the hard shapes that
   exist today, and the set expires by addition rather than by replacement
   (STRATEGY §6.5). What stops it growing as the product of the shapes is
   ARCHITECTURE §2.7: the axes are fields of one signature, so one member can
   carry two of them at once and what has to be covered is the axes rather than
   their combinations.
3. Reference members are the answer to "how do I do this correctly," and their
   completeness is measured by ARCHITECTURE §2 — declarations, cost shape,
   benchmarked through the engine.
4. Harmless duplication is not the target. Two similar helpers in the folder
   where both belong will be noticed and merged. The target is the helper that
   is *hidden*, which never gets noticed and never gets merged.

Forbids: adding a kind of thing by reading someone else's implementation and
guessing which parts were load-bearing.

## 8. The module guide is generated

Parnas, Clements & Weiss (1985) call this the module guide: a hierarchy of
modules with each one's secret stated in a line, whose only job is telling a
newcomer where to look.

1. It is generated by walking packages and emitting each purpose line and
   export list (§4.4). It is never hand-maintained, because a hand-written map
   of a moving codebase is wrong within a month and worse than absent — it is
   confidently wrong.
2. If the generated guide reads as incoherent, the codebase is incoherent. The
   guide is a diagnostic, not a document to be improved directly.

Forbids: documentation of structure that can drift from structure.

## 9. What this document is not

No decision log: this is not a stream of decisions and the project does not
want the ceremony. No per-module documentation — that is `__init__.py`'s job
(§4.1) and duplicating it here is the same drift ARCHITECTURE §4 forbids for
code. No layered rings, application layers, or repository/service scaffolding:
those come from decomposing by processing step, which §1.2 rejects outright.

No enumeration of the current folders, either. That is the generated guide's
job, and a list here would be stale and authoritative-looking at the same time.
The tests in §1 and §2 are what stay true; the inventory does not.
