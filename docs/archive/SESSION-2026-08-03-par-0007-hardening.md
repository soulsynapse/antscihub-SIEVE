# Session — hardening PAR-0007

Status: Frozen
Date: 2026-08-03

The sitting that rewrote PAR-0007 in plain language and gave it an
evidence base. Kendrick and Claude (Fable 5, then Opus 5). The
op-contract split argued in the same sitting is a separable decision
and files its own primary
(`SESSION-2026-08-03-op-contract-split.md`); it is referenced here
only where it narrowed this rationale.

Kendrick is quoted verbatim. Exchanges are numbered for citation.

---

## Exchange 1 — The commission

> "Problems with par7: this is the hardening pass. First, it is not
> written in plain language. Second, it is not convincing of it's own
> worth, even though it is arguably the most important PAR after par1.
> Par7 should be written in plain language first and foremost. If
> repo-specific language or references need to be used, have them in
> parentheses.
> Evidence first:
> - Other systems that worked because of this seam
> - Other systems that failed because of this seam
> - Other systems that didn't adopt this seam and failed as a result
> - Other systems that didn't adopt this seam and succeeded without it"

Both halves of the diagnosis held. The record was written in the
house's most allusive register, which is hostile to the audience the
contract itself names — behavioral scientists and agents. And it argued
each rule locally while never arguing why the arrangement as a whole
deserved to exist, so a reader could grant every paragraph and still
ask why tools should not simply compute.

The four cells were filled with transfer verdicts attached, on the rule
that an exemplar cited without one is decoration. Working: SQL, LLVM,
Snakemake/Nextflow. Failed having adopted it: TensorFlow 1.x (the
author felt the cost) and Maven (the vocabulary was too poor, so
authors smuggled execution back in) — two distinct modes, and SIEVE has
a designed answer to each, the second being that a missing operation is
landable named debt. Refused and failed: ImageJ, with the caveat that
it succeeded enormously for interactive single-user work, and v1.
Refused and succeeded: Unix pipes and scikit-learn.

The fourth cell produced the worth-argument the record was missing.
Those systems can skip the arrangement because nothing downstream wants
the description; the arrangement is forced only under four commitments
— content-derived result identity, execution improving independently of
authored work, silent substitution of equivalents, and more authors
than reviewers. SIEVE's outcomes commit it to all four. **The boundary
is the bill for commitments made elsewhere, not a matter of taste.**

Placement, settled later in the sitting: evidence goes in Context, not
in the plain top section, and ImageJ is explicitly cleared for
citation.

## Exchange 2 — The name

Candidates were priced on three axes: clear to the user, clear in the
repo, and pattern-match risk. The incumbent's defect was that
*contract* was doing two jobs — the boundary (the system) and the
signature (how it is held) — which invites an agent to pattern-match to
Design-by-Contract, inspect the signature, and stop, missing that the
boundary lives in what the signature does not show.

> "I can agree with that. I agree tool contract is fine, but the
> tagline is very valuable."

Ruled: title and filename stand. What changed is a word discipline the
rewrite now obeys — *contract* means the signature only; where the
boundary is meant, the boundary is named. Also rejected: "the tool
boundary" (collides with PAR-0006's use of boundary), "tools describe,
never execute" (one rule, not a system), "the authoring seam" and "tool
isolation" (both pattern-match wrongly).

## Exchange 3 — The boundary, stated specifically

Kendrick set the filter: name the architectural boundary; everything
else is upstream, downstream, or cheap-and-internal; do not scope a
record to internals cheap to change later; *if it is all cheap, it is
not a PAR*. Two flags on any multi-domain answer — shared upstreams and
downstreams mean two domains were scoped together, and identical
expensive internals mean things were shuffled to look different.

Three candidate domains were enumerated. **The knowledge boundary
collapsed into the call boundary**: under purity, what a tool knows and
what its functions receive are the same fact, and that identity is the
design's central trick, converting an unenforceable rule into a
checkable one. **Identity placement** survived as a separate candidate
— different downstream consumer (the store), different cost currency
(data rather than code) — and was merged anyway, on the reversal test:
if result identity were made location-independent tomorrow, the rules
against operations living in tool files would still stand on the call
boundary's own grounds, so they are not separately revisable.

Settled: **PAR-0007 owns the membrane around the tool file — what
crosses it in each direction, and the guarantee that nothing else
does.** The expensive internals are the crossing rules; everything
about how a tool does its translation inside is cheap and deliberately
unowned.

## Exchange 4 — The consistency check that found the splice

> "Is this consistent with the ops passing things to the tool? That
> whole decision chain was expensive to converge on from before, but
> very illustrative."

Consistent, and the check sharpened the membrane. Three flows, none of
which passes anything to the tool: operation field-type declarations
flow to the settings panel around the tool, which is why the
pass-through in Exchange 11 of the scoping sitting is literal; the
authored method choice flows from panel to step to description, so only
the tool's own settings ever enter `lower`; and the one thing crossing
inward is vocabulary — **operation names cross as imports; operation
meaning, implementation and settings never do.**

The check exposed a gap: if the chosen operation never passes through
`lower`, the returned description must carry a point where the choice
is attached later. Whether such a point may exist is a property of what
`lower` returns and therefore expensive; how the attaching is done is
ordinary machinery. Neither half was stated anywhere — the record now
states the first and routes the second to PAR-0014, citation both ways.

## Exchange 5 — Ownership, twice collapsed

> "So for clarity: it doesn't own the parameter definitions, it owns
> the parameter values. Correct?"

Answered no, then found to be half right and the correction itself
defective. The plain reading fails — the settings model, its
constraints and its defaults are literally in the tool file — but
against the surface under discussion (a method's own knobs) the claim
is exactly right, and that half is now PAR-0020's.

The correction's own defect was an equivocation on *own*. The repo
already distinguishes custody from responsibility — PAR-0006 says
params *live in* the pipeline file, while a tool *owns* the
translation — and "the step owns the values" collapsed the two. A Step
has no functions; a thing with no functions cannot hold a
responsibility.

> "I'm not even sure it owns definitions."

Pushed further and it collapsed again, correctly. Applying the test
that makes *own* mean anything — answerable for it, and may change it —
a tool fails for nearly everything in its settings model: it cannot
invent a field type, cannot decide whether something may be a setting
at all, cannot rename a field freely, and cannot withdraw one once a
result is stored. **What remains is that a tool owns the translation
and what its own settings mean: content, never form.** Three verbs
replace the overloaded one — declares, lives in, interprets — and the
rewrite defines *own* once before using it.

The yield beyond vocabulary: this is why tools are cheap to write and
safe to accept from an agent. The author supplies only content; all
form is supplied to them, so an agent can get the measurement wrong —
visible and reviewable — but cannot get the structure wrong, because
the structure was never theirs to set.

## Exchange 6 — The framing, and what it fixed

> "The tool is the synthesis that eventually makes it to the user...
> theres a GUI, a bunch of elegant back end stuff, ops, validation
> layers, preferences that are set outside of the tool itself, and then
> the tool: the thing that brings them all together... you can look at
> a tool by what it has, what it doesn't, and how good the things it
> has are, and immediately know where to make improvements."

Coherent, and it predicted the collapse in Exchange 5 rather than being
embarrassed by it: a junction that owns things is a junction that
couples. Two corrections were argued and taken. Preferences do not
converge at the tool, and the exclusion is the criterion — **the tool
is the convergence point of everything that determines the answer**,
and preferences by definition cannot. And the tool is where those
systems are *named* together, never where they are called; "brings them
all together" is one step from "orchestrates them all," which is the
object this record exists to prevent.

The framing was then revised twice by Kendrick, dropping a conference
analogy (its venue half lost the pipeline's composition) and dropping
the tool owning the red display:

> "It was giving it more power than it needed and the domain was
> shifting it's borders I feel."

Correct, and forced rather than preferential: whether an operation
exists is knowledge of the world outside the membrane, so a tool cannot
own the display of its own gaps without ceasing to know nothing.
Settled: rendering is PAR-0013's; the computation is not a new system
but the query PAR-0011 already answers at placement, plus the
resolution PAR-0014 already performs, plus the debt machinery's marker
text. **No universal error handler and no final validation pass** —
both are god-object shapes that would have to reach into the systems
this architecture keeps apart. What PAR-0007 keeps is only that a
tool's declarations make the gap computable without the tool asserting
anything about itself.

The final framing was placed verbatim at the top of the rewrite, with
the one thing it leaves out stated immediately after: the tool can be
the coherence check only because it holds no power over anyone on the
list.

## Exchange 7 — What the record means downstream

The end-to-end walk (definitions declared by tool and operation, values
living in the step, the panel composing, the executor borrowing and
calling, the store identifying, the harness licensing) became the
diagram inside the rewrite. Checking it against `ARCHITECTURE.md`
surfaced three defects in the synthesis, of which one is a genuine
contradiction: the GUI section says the settings panel is generated by
walking the tool's settings alone, which this rationale's ruling makes
wrong. The rule belongs to PAR-0013, undrafted — but the incorrect
sentence is in tier 1 now, so the repair travels with this rationale's
acceptance. The other two are the stale example signature and a run
figure that hides the attachment point.

Ruled on figures: repair the existing one, never add a second, because
two diagrams sharing parts must be kept consistent by hand.

Also found: the three how-to guides this record promises cannot be
followed today — the first depends on the kernel's names, the second on
the harness and the panel, the third has no reader until the harness
exists. The consequence was amended to say the guides arrive as their
surfaces land. A guide for something that cannot be done is fiction in
the layer that is read first.

---

## Settled

- Plain language throughout, repo terms parenthesized; evidence in
  Context with transfer verdicts attached (1).
- The worth-argument is the fourth cell's condition: the arrangement is
  forced by four commitments SIEVE has already made (1).
- Title and filename stand; *contract* means the signature only (2).
- The record owns the membrane around the tool file (3).
- Operation names cross inward as imports; meaning, implementation and
  settings never do (4).
- `lower`'s returned description may carry an attachment point; the
  attaching is PAR-0014's (4).
- *Own* is defined once and used narrowly; declares / lives in /
  interprets replace it elsewhere. A tool owns content, never form (5).
- The tool is the convergence point of everything that determines the
  answer; preferences are excluded by that criterion; systems are named
  together, never called (6).
- The tool never declares its own defects; the gap is derived. No
  universal error handler, no validation-pass component (6).
- `ARCHITECTURE.md`'s GUI section is corrected at acceptance; its
  figure is repaired rather than duplicated (7).
- The how-to guides arrive as their surfaces land, not at acceptance
  (7).

## Open at close

- PAR-0007's judgment, by attack. Unchanged by this sitting: the
  rewrite argues the decision better, it does not accept it.
- PAR-0005's amendment, without which the refusal of the voiding
  declaration falls.
