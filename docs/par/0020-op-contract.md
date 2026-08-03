# PAR-0020 — The op contract

Status: Proposed
Date: 2026-08-03

Owed: 20260803T211410Z: rationale for the op contract — what an op owns
and what it must never own, split out of PAR-0007 where five op-rules
had accumulated as asides in the tool's rationale (the op's knob
surface, op individuation, the yardstick, field-types-never-rendering,
the op side of the placement rule), which is a system cut in half by
PAR-0001's own straddle test; expected thin, citational, and denial-led
— its expensive internals are mostly already settled and accepted
elsewhere, so its fresh content is the never-list assembled in one
place for authors arriving with minimal context; governs until
acceptance: PAR-0005 for op-as-value and form-as-authorization,
PAR-0007 (Proposed) as drafted for knob placement and the two senses of
*method*, `SESSION-2026-08-03-tool-contract-scope.md` Exchange 11, and
primary `SESSION-2026-08-03-op-contract-split.md`

Borders and contents, stated at filing so the distillation does not
re-derive them (primary: `SESSION-2026-08-03-op-contract-split.md`):

- **Owns:** the responsibility boundary around an op — what an op file
  contains, what it is structurally denied, and the criteria its
  concurrent alternatives compete under.
- **Borders.** Upstream: PAR-0005 (an op is a closed serializable value
  with typed fields, never a callable; its form is its authorization) —
  cited, never restated. Siblings: PAR-0007 (the tool membrane; the
  placement rule is deliberately dual-stated — a membrane denial from
  the tool side, an identity requirement from this side). Downstream:
  PAR-0009 and PAR-0016 (op identity composes into the recipe hash and
  is versioned), PAR-0011 and PAR-0012 (grouping by generic function,
  membership earned by measurement), PAR-0013 (field types imply
  widgets; rendering is never the op's).
- **What it owns, itemized:** the op's param surface (its knobs, as
  typed fields, in the op's own file — never in any tool's model); op
  individuation (verified-equivalent implementations are one op,
  answer-differing methods are two ops — the rule that decides what is
  hashed); the op-level yardstick (membership equivalence: comparator,
  tolerance, target statistic against the reference implementation over
  the corpus); and the never-list — an op never renders, never performs
  I/O or execution, never selects or influences selection, never
  declares verdicts about itself, never owns or names a tool, never
  entangles its identity with its location.
- **The two-yardstick split it receives:** membership equivalence (is
  this implementation the same op?) is this record's and the harness
  verifies it without the tool; use-level meaning (is this substitution
  equivalent for the statistic the user cares about?) stays on the
  tool/use side. PAR-0005's routing of "the equivalence spec" to
  PAR-0007 conflated the two; the routing amends at acceptance.
- **Costly inside:** individuation (misjudged, it changes what is
  hashed — a store migration); identity composition into the hash;
  the knob surface's placement (misplaced, a schema migration plus
  changed hashes for every affected result, per PAR-0006's pricing).
- **Cheap inside, by design:** everything else. `Opaque` is the resting
  state, so the default form cannot be wrong; membership is earned at
  the harness, so an author cannot botch an equivalence claim — no
  channel exists to make one; alternatives coexist and compete on
  measurement, so cheap admission is safe; the interior implementation
  is freely rewritable with no change to any public surface. The
  never-list is what keeps the competition unriggable — an op that
  cannot render cannot differentiate on UI instead of accuracy, and an
  op that cannot vouch for itself cannot rig the market that judges it.

Stated 2026-08-03 in the op-contract split sitting, where the yardstick's
placement in PAR-0007 surfaced the straddle and the cheap-by-design
counter-reading settled the record's character.
