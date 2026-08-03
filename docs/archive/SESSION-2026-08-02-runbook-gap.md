# Session record — 2026-08-02 — the runbook gap

Status: Open
Date: 2026-08-02

Curated primary for PAR-0003 (draft). The argument is open by its
author's own statement — the problem is named, the answer is nebulous —
so this record stays `Status: Open` until the design argument closes.
Doctrine: PAR-0001.

## Exchange 1 — naming the problem: the missing how-to layer

Kendrick, verbatim:

> "one actual challenge for the PAR system that would be good to address
> right now: architecture.md holds the settled synthesis, PAR holds the
> why, but nothing adds in the derived-and-tested runbook(s) of the
> system PAR speaks to. Tightening up what ARCHITECTURE.md explicitly
> points to could be handy, but I think this lands as concretely outside
> of what PAR is. There are a bunch of ways to meet the rationale, some
> deliberately stated, but how execution in the repo should respect the
> rationale is left to the reader. I think the next, extremely clear
> step, is to have a new PAR detailing the system to codify how to pass
> the information about how agents and people should improve, use, or
> otherwise leverage the benefit the system exists to provide. As
> rationale, this is improving on PAR *specifically* to close the
> diataxis loop: Agents and people can pick up tutorials from convention
> within the repo, PAR holds the explanation and reference for working
> in the repo directly. The last item is the how-to guides. For clarity,
> the answer to this is nebulous; I'm only naming the problem, so this
> is debt to be resolved, with a draft PAR pointing at why it needs to
> exist, which is this session."

The agent's assessment, compressed. The diataxis mapping is right, and
the strongest evidence for the gap is that the layer already exists de
facto as orphans — `README.md`'s mismatch runbook and `AGENTS.md`'s
Procedures are how-to guides living where they landed, which under the
granularity rule is what "no named system" looks like; naming the system
is recognition, not invention. The central design tension is
"derived-and-tested" against the anti-bureaucracy invariant: a runbook
is hand-maintained state about a tree that moves — PAR-0002's drift
failure — so the design must find how much of a runbook can be derived
or verified without the verifier itself becoming bureaucracy.

Candidate directions held open, deliberately undecided here:

- Runbook steps that are literally executable — commands the suite or a
  smoke script actually runs, so drift reds something.
- Runbooks rendered from tests rather than written beside them — the
  test tree as the source of truth, the guide as a derived view.
- Hand-authored prose whose *pointers* are verified, the way marker
  reasons point at governing sections — cheapest, weakest.

One boundary caution, also open: if the layer lands well it will tempt
absorbing the tutorial convention; task-oriented ("I need to do X now")
versus learning-oriented must stay a drawn line or the diataxis
distinction collapses in the implementation.

Executed this sitting: PAR-0003 drafted `Proposed`, recording only what
is decided — the system exists and is anchored; it is outside PAR;
its purpose is closing the diataxis loop — and naming the rest open.
Design debt filed in `DEBT.md`, since `Proposed` alone carries hardening
debt but not design debt.

## Exchange 2 — the name and the heuristic (design session, first sitting)

Kendrick, verbatim, opening the design session:

> "First: renaming runbook -> how-to. This is adopting the diataxis
> terminology directly, and pattern matches deliberately; better for
> agentic work. Thoughts?"

The agent's assessment, compressed. For: the record already defined the
layer by its diataxis role, with "how-to guides" as the referent and
"runbooks" as the gloss — the rename stops using the gloss as the name;
"how-to" is the accurate superset (the stated purpose is how-to breadth,
"runbook" names the layer after its narrowest member); and "runbook"
primes the SRE incident-response genre, misrouting an agent asking
"where do I learn to do X." Against, the position that lost: "runbook"
carries the stronger *executable* prior — SRE culture treats runbook
automation as the goal state — while stock diataxis how-to guides are
hand-authored prose with no verification implied, so the rename trades
away the one prior pointing at the derived-and-tested constraint.
Resolved: the discipline is carried by the record and the machinery,
not the noun; the name's job is routing consumption.

Kendrick, verbatim, settling it:

> "how-to is the form and I agree with adopting the stance that
> anything that can be a script should be a script as a governing
> heuristic."

Two decisions land. **The name is how-to**; "runbook" is retired
wholesale — no subgenre survival — since a two-tier vocabulary (a
how-to layer containing runbooks) reinstates the unqualified-name
ambiguity the rename kills. Frozen records and this file's name keep
the word; retirement bars reuse, not history. **The governing heuristic
for the derivation-and-test discipline: anything that can be a script
is a script** — which adopts Exchange 1's first candidate direction
(literally executable steps, so drift reds something) as the default,
demotes the other two to the residue for what genuinely cannot
execute, and answers the traded-away prior above: the executable
discipline the old name gestured at is now doctrine, so the name is
free to do routing.

Surfaced in passing, deferred by Kendrick ("can surface it later if
necessary"): `AGENTS.md`'s never-reuse-a-retired-name rule cites no
governing record — a possibly unfiled gap, parked here.

Still open after this sitting: the form (per-system guides or a tier
of their own), the home, the residual discipline for the prose
remainder, and Exchange 1's boundary caution against absorbing the
tutorial convention.
