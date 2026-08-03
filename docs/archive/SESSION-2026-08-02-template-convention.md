# Session record — 2026-08-02 — the template convention

Status: Frozen
Date: 2026-08-02

Curated primary for PAR-0004 (draft). Doctrine: PAR-0001.

## Exchange 1 — templates, and drafting at a suspect boundary

Kendrick, verbatim:

> "Before I forget too, PAR and archive folders need some kind of
> template convention. As a new draft PAR (what are we on, 0004?),
> folders or systems that can or should operate off a template are owed
> one, at the judgement of the user. Agents can suggest them for now. As
> a challenge for that new par, one doubt I have is that agents might be
> able to accurately recommend new templates and hit all the right
> requirements, but that'll have to be tested. It can just go in the
> challenge section of the new draft par. Since templates are pretty
> distinctly close to 0003, another doubt for that is that it might
> survive merging with general how-tos where how-tos are treated as a
> system, but the reason that it's landing as it's own draft is that
> templates can signal modularity. Theres no reason an active PAR can't
> be rolled up into an existing PAR as the expansion of it as a system,
> since the rationale of it as a template doesn't have lots to do with
> the rationale of runbooks that don't have templates. It's just one
> part of the runbook system as a whole, probably, and that's probably
> fine. The bar for something being PAR is the near decomposability, and
> because PAR is about system rationale, if the rationale is messy
> between systems or becomes hard to understand and internalized by
> either the repo authors or agents, then the PAR is no longer serving
> it's purpose. This is definitely cutting against a bunch of the stuff
> from this session though. I have some rationale for why this is
> acceptable, but I'd like to know what you think."

The agent's assessment, compressed: drafting at a suspect boundary does
not cut against the scope session once the granularity rule's modality
is noticed — a boundary is a falsifiable hypothesis per record, not an
admission gate, and what would violate the session is *accepting* a
record with a known-fuzzy boundary, not proposing one with the doubt
logged on the record it concerns. Proposed-does-not-govern makes the
provisional boundary free. The asymmetry supports erring fine-grained:
merging living records later is cheap and lossless, splitting a fused
record is the expensive direction. The Parnas reversal test cannot run
against PAR-0003 while it is undesigned — separate drafting is what
makes the boundary testable later at all. And the strongest case that
PAR-0004 stands alone regardless: the day's status-line derivations
already lean on form regularity, templates are the mechanism that keeps
forms regular, and the leniency PAR-0001 names is exactly the gap a
template narrows — a rationale existing with or without runbooks, which
is the modularity-signal instinct made concrete: if a class can be
templated, it is a class, and the template makes its boundary legible.

Also noted, not adopted: this argument is the case for the position
left open in `SESSION-2026-08-02-par-scope.md` — boundary review as a
formal part of hardening, individuation provisional while Proposed.

Executed this sitting: PAR-0004 drafted Proposed with both of
Kendrick's doubts as standing-unresolved Challenges entries; the first
two template instances (`docs/par/`, `docs/archive/` session records)
named in Consequences as judged owed, due when the record governs.

## Exchange 2 — the acceptability rationale, and a doubt against hardening

Kendrick, verbatim, written while Exchange 1's assessment was being
composed — the convergence again independent:

> "Writing this as you're responding: the reason it's acceptable is
> directly supported by the fact theres no ambiguity about where
> something should go or how it should be pointed to. Something being a
> runbook having a pointer to the PAR for templates has zero ambiguity
> about where templates can live, so it being a subset is absolutely no
> problem. Then consider what points to PARs: an architecture reference
> to a giant PAR is useful if the PAR can't be understood without each
> of it's parts. Once it can be understood without each of it's parts,
> or when one part can be split out because the reasoning doesn't touch
> anything else, that becomes a clarity gain: templates *are in service
> to* the runbook system, and what they are is clear enough for it to
> have a clear boundary. Reading your message; we landed on the same
> result. I'm not totally sure the hardening is necessary btw, we can
> mark the hardening process as doubt, since the hardening was just one
> way to deliberately improve a PAR and fell out as procedure before
> being reasoned as necessary. For example, runbook layer and templates
> landed without hardening, and hardening is useful to artificially
> accelerate or bypass the evidence accumulation, but it's just another
> way of saying 'the PAR stands the test of time and multiple
> challenges' (what hardening literally is), and the PAR system now has
> two different ways to do that."

Two things land. The acceptability rationale adds the pointer criterion
to the boundary machinery — a sub-system in service to a larger one
splits cleanly when every pointer to it is unambiguous, and a large
record earns its size only while it cannot be understood without each
of its parts — folded into PAR-0001's Granularity and PAR-0004's
merge-doubt entry. The hardening doubt lands as a standing-unresolved
entry in PAR-0001's Challenges with the agent's counterweight recorded:
hardening is timing insurance rather than mere acceleration — organic
challenges probe what usage happens to touch, the attack front-runs the
load — and the 0003/0004 examples bear on drafting, not the Accepted
gate, since both sit Proposed and govern nothing. Semantics and the
`DEFERRED.md` trigger stand while the doubt does.
