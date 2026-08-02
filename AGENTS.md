# Working in this repo

Instructions for any agent or person making changes. Nothing here restates
what a governing record holds — follow the pointers.

## Orientation order

1. `README.md` — the map: locations, the record tiers and their walking
   path, the debt files, the mismatch runbook.
2. `docs/ARCHITECTURE.md` — before writing code. The one-stop shop: it
   reports, it does not govern. Read deeper — `docs/arch/`, then
   `docs/archive/` — only until convinced; the walking path and authority
   order are ARCH-0001.
3. `DEBT-AUTO.txt` — what is presently owed in-tree; `DEFERRED.md` — what is
   not yet due. Building from DEFERRED.md goes poorly, by design.
4. The live planning cycles: `docs/PLAN-TOOL-CONTRACT.md` (code) and
   `docs/PLAN-DISTILL.md` (record distillation, ARCH-0001). Exhausted plans
   sit in `docs/archive/` — `PLAN.md` there holds marker form rule v1, the
   layout settlement, and the classification rule, all still load-bearing.

## The working loop

- One decision at a time. A proposal is the deliverable — nothing is built
  until the proposal is confirmed. A plan settles sequence and definition of
  done, never build authorization.
- Proposals arrive complete enough to be judged whole; lead with the
  concrete. A proposal names the records that govern it; one that can cite
  none says so — that absence is signal, not license.
- A contradiction — between records, or between a record and the tree — is
  named out loud before anything is built on top of it, never silently
  resolved toward the easiest reading.

## Where records go

- A settled decision → the active planning document's gate; when it is an
  architecture decision (scope: ARCH-0001), it is recorded as an
  architecture rationale in `docs/arch/` — with `docs/ARCHITECTURE.md`
  amended in the same commit —
  and the gate cites it. An exhausted plan freezes under its name and moves
  to `docs/archive/`; a successor cycle takes a new name.
- A not-yet-due intention → `DEFERRED.md`, always with the trigger that
  makes it due.
- A present gap no marker can carry → `DEBT.md`.
- A component the named milestone reaches but that isn't built → a
  placeholder: a real module at its real import path raising
  `sieve.debt.Owed` in marker form rule v1, quoting signatures only from the
  settled record, its docstring pointing at the governing sections.
- Everything derivable from the tree is derived, never hand-maintained (the
  anti-bureaucracy invariant, judged at conformance passes).

## Procedures

- After placing, removing, or rewording a marker: `python -m sieve.debt
  write`, and the regenerated ledger travels in the same commit as the
  change it reflects.
- The suite is green before a commit lands; green includes placeholder
  skips exactly matching the automatic ledger's test-tree entries. Nothing
  physically blocks committing red — possible is not in-contract.
- Chunk commits: decision-record amendments land separately from placements
  and code.

## Never

- Hand-edit `DEBT-AUTO.txt`.
- Invent an API surface a placeholder should merely point at.
- Build from `DEFERRED.md`.
- Catch `Owed` outside the debt machinery.
- Reuse a retired name — file-format fields, documents, or module paths.

## Session boundaries

Start with the orientation order. End with: working tree clean, suite
green, regen a no-op, and nothing valuable left unfiled — a decision,
intention, or gap that surfaced along the way gets its record (see "Where
records go") before the session closes. Durable context has homes; if
something fits none of them, that is a missing home to name, not a reason
to park prose somewhere unowned.
