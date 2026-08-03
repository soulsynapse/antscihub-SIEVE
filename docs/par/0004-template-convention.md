# PAR-0004 — The template convention

Status: Proposed
Date: 2026-08-02

## Context

The named system: the template convention — the scaffolds that keep a
record class's form regular. The occasion: `docs/par/` and
`docs/archive/` records share load-bearing form — status lines, dated
titles, provenance and Challenges sections — held today only by
imitating the neighbors. Form regularity is not cosmetic here, because
the repo's derivations lean on it: `grep -l "^Status: Proposed"
docs/par/*.md` and `grep -l "^Status: Open" docs/archive/SESSION-*.md`
are debt derivations that work only while every record carries the
line, and PAR-0001 names the residual leniency in exactly those terms —
a record created without a status line escapes the derivation, guarded
only by the form rule. A template is that guard made concrete: the form
stated once and copied at creation, rather than re-derived from a
neighbor each time.

Primary: `SESSION-2026-08-02-template-convention.md`.

## Decision

Folders or systems that can or should operate off a template are owed
one, at the judgment of the user. Agents can suggest templates — for
now; whether an agent can also draw one correctly, hitting all the
requirements a form actually carries, is an open doubt logged below.
Judgment stays with the user for the same reason friction confirmation
does (PAR-0001): a ceremonial template for every folder is PADding, and
the tipping point is a human read.

Everything else — the template form, its home, and how conformance is
checked — is open. Whether this system is one part of the how-to layer
was resolved at PAR-0003's acceptance: it is in service to that layer
and remains its own record, under PAR-0001's pointer criterion (the
second doubt below, closed).

## Consequences

- The first two instances judged owed (2026-08-02): `docs/par/` records
  and `docs/archive/` session records. Producing them is this record's
  first work once it governs; a Proposed record does not govern, so
  nothing is owed yet beyond this draft.

## Challenges

- **2026-08-02 — "Agents might be able to accurately recommend new
  templates and hit all the right requirements — but that'll have to be
  tested."** Kendrick's doubt, standing unresolved: no evidence either
  way yet, which is why the decision above keeps template-drawing at
  user judgment with agents suggesting. Resolves when tried. First
  evidence 2026-08-03, confirmed by Kendrick, and it points the way the
  decision already does: `how-to/repo-work/draft-a-par.md` was first
  written by an agent distilling one session and did not work; the
  derivation procedure that does work was hand-written, and the same
  pass found the file misnamed — what it contains clears the bar for a
  draft, not for acceptance, so it split and `accepting-a-par.md` is
  hand-written separately. Adjacent rather than direct: a how-to
  distilled from a session is not a template drawn from requirements,
  so the doubt stands rather than resolving.
- **2026-08-02 — "This might not survive merging with PAR-0003 —
  templates are probably one part of the runbook system as a whole, and
  that's probably fine."** Kendrick's doubt, standing unresolved and
  deliberately not blocking. It lands as its own draft anyway because
  templates can signal modularity and carry a rationale that
  how-tos-without-templates do not (the derivation-guard argument in
  Context); because PAR-0003 is itself undesigned, so the boundary
  cannot be tested against it yet; and because merging living records
  later is the cheap, lossless direction — an active PAR rolling up
  into another as that system's expansion is within doctrine.
  Kendrick's acceptability rationale (primary, Exchange 2): templates
  *are in service to* the how-to system ("runbook" at the primary's
  date; renamed at PAR-0003's first design sitting) with zero ambiguity about
  where they live or how they are pointed to, so subset status is no
  problem — the pointer criterion now in PAR-0001's Granularity.
  Resolved 2026-08-03, at PAR-0003's acceptance: the record survives
  as its own — the acceptability rationale above held as the ruling,
  the derivation-guard argument in Context owes nothing to guides, and
  merging later stays the cheap, lossless direction should Challenges
  entries ever straddle the two records (PAR-0001's revision test).
