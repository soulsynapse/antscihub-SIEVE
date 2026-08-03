# Session — the op contract split out of the tool contract

Status: Frozen
Date: 2026-08-03

The separable argument, from the PAR-0007 hardening sitting, that ended
with PAR-0020 filed as a stub. Kendrick and Claude (Fable 5). The wider
hardening argument — plain-language rewrite, the evidence case, the
membrane scoping — is a distinct decision-cluster and files its own
primary when it closes; this record holds only the op-contract split.

Kendrick is quoted verbatim. Exchanges are numbered for citation.

---

## Exchange 1 — The position that lost first

Earlier in the sitting, asked which domains the discussion had surfaced
without an existing rationale, Claude had ruled — twice, the second time
against its own first answer — that the count was zero: everything
routed to existing stubs, and the one candidate (the runtime failure
surface) decomposed cleanly into PAR-0015, PAR-0013, and an executor
obligation. That stinginess was correct in method and wrong in one
instance, and the error was exposed not by a scoping pass but by a
concrete misplacement: in a legend for the end-to-end figure, Claude
assigned the equivalence yardstick to the op files — while PAR-0007 as
drafted says the *tool* declares yardsticks for the ops it emits. The
drift went unnoticed by its author and not by Kendrick.

## Exchange 2 — The yardstick surfaces the boundary

> "Hm, the par5 yardstick makes me think that the ops themselves are an
> extremely clear boundary. Tool owns specific things, but ops are
> decomposable. The tool itself and the PAR for ops can be pretty
> strongly coupled, but shoving all the requirements for ops into the
> the tool PAR makes me think there is a lot of possibility for messing
> up the ops themselves. That reads to me as a costly boundary."

Inventory confirmed it: five op-rules were lodged in the tool's
rationale as asides — the op's knob surface, op individuation (the
two-senses-of-method rule, which decides what is hashed), the
yardstick, field-types-never-rendering, and the op side of the
placement rule. PAR-0001's straddle test names this a system cut in
half. The flags were run: tool and op share downstreams, but the Parnas
reversal separates them — reverse `lower`'s arity and no op rule moves;
reverse op-as-value and PAR-0005's substitution architecture collapses
while the membrane stands. The cost is real by the admission filter: op
identity composes into the recipe hash, so misjudging the op's shape,
individuation, or knob surface is a store migration, the data-priced
mistake.

The yardstick confusion resolved into a finding: there are two
yardsticks conflated under one name. Membership equivalence — is this
implementation the same op? — is op-level, verified by the harness
against the reference over the corpus, and never needs the tool.
Use-level meaning — is this substitution equivalent for the statistic
the user cares about? — only the tool/use side can state. PAR-0005's
Consequences routed "the equivalence spec" to PAR-0007 as one thing;
it is one per domain.

## Exchange 3 — The counter-reading settles the record's character

> "The other reading is that ops, by design, and parroted across the
> repo, are intentionally cheap because of all the controls to keep
> them cheap and easy to build, but harsh criteria for them to compete
> with concurrent alternatives of any one op, which can live along side
> it. But a relatively weak PAR, defined by a PAR, still outlines the
> things it must never do, and that is extremely useful for agents and
> people writing from minimal context."

Reconciled as the same design seen from opposite sides rather than a
competing position. The cheapness is the contract's product, not the
absence of one: `Opaque` as the resting state means the default form
cannot be wrong; membership earned at the harness means no author can
botch an equivalence claim, because no channel exists to make one;
knobs in the op's own file mean no coordination surface; derived
registries mean nothing to register. Cheap admission plus harsh
measured competition is a market design, and the never-list is what
keeps the market unriggable — an op that cannot render cannot
differentiate on UI instead of accuracy; an op that cannot declare
verdicts cannot vouch for itself; an op that cannot select cannot tilt
the dispatch that judges it.

What follows for the record: PAR-0020 is thin, citational, and
denial-led. Its expensive internals are mostly settled and accepted
elsewhere (op-as-value and form-as-authorization in PAR-0005, hash
composition in PAR-0009's rulings), so its fresh content is the
never-list assembled in one place — the complete safe envelope for a
minimal-context author in a two-minute read. The pair with PAR-0007
makes the architecture's symmetry legible: two contracts, both stated
as denials, one heavy because tools sit where the coupling pressure is,
one light because ops were designed to have nothing worth coupling to.

## Exchange 4 — Filed

> "Go write down the stuff into that stub while it's fresh, where it's
> borders are, what it owns, what's costly inside, what's cheap inside.
> You can do this as an unordered list and point it at this session."

PAR-0020 filed as a stub at its own number, stamp `20260803T211410Z`,
carrying borders, ownership, the cost split, and the two-yardstick
finding, pointed here. PAR-0007's rewrite — pending from the hardening
argument — narrows at that sitting: it keeps the tool-side of each
shared rule and cites PAR-0020 for the op-side, with the placement rule
deliberately dual-stated, one rule in two records, each stating its own
reason.

---

## Settled

- The op contract is its own system; five op-rules leave PAR-0007's
  ownership at its rewrite, surviving there only as the tool-side of
  each seam (2).
- Two yardsticks, one per domain: membership equivalence is op-level
  and harness-verified; use-level meaning stays on the tool side.
  PAR-0005's single routing amends at PAR-0020's acceptance (2).
- PAR-0020's character: thin, citational, denial-led — the never-list
  is the fresh content; the expensive internals are citations (3).
- The placement rule is dual-stated by design: membrane denial from the
  tool side, identity requirement from the op side (4).

## Open at close

- PAR-0020's distillation and acceptance, ordered in
  `docs/PLAN-DEBT-ORDER.md`.
- PAR-0007's narrowing landed the same day in its plain rewrite
  (primary `SESSION-2026-08-03-par-0007-hardening.md`): the tool-side
  refusals stayed, the op-side rules left, and the placement rule is
  stated in both.
