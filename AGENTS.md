# Working in this repo

Instructions for any agent or person making changes. Nothing here restates
what a governing rationale holds — follow the pointers.

**`proto_sieve/` is exempt from everything in this file.** It is a
disposable spike on the decomposition, governed solely by
`proto_sieve/AGENTS.md`, which replaces this file rather than extending
it. No PAR, no marker, no stamp, no ledger regen, no session primary, and
no citation in either direction. Working there, read that file and stop.

## Orientation order

1. `README.md` — the map: locations, the record tiers and their walking
   path, the debt files, the mismatch how-to. For a task with a guide,
   `how-to/<domain>/` is tier 0 — follow it and fall back down the
   chain only when it fails (PAR-0003).
2. `docs/ARCHITECTURE.md` — before writing code. The one-stop shop: it
   reports, it does not govern. Read deeper — `docs/par/`, then
   `docs/archive/` — only until convinced; the walking path and authority
   order are PAR-0001.
3. `DEBT-AUTO.md` — what is presently owed in-tree; `DEFERRED.md` — what is
   not yet due. Building from DEFERRED.md goes poorly, by design.
4. The live planning cycles: `docs/PLAN-TOOL-CONTRACT.md` (code);
   `docs/PLAN-DEBT-ORDER.md` (distillation). Distillation runs system by
   system from the stub records' markers in the automatic ledger,
   ordered by that plan (PAR-0001, PAR-0002). Exhausted plans sit in
   `docs/archive/` — `PLAN.md` there still holds the layout settlement,
   load-bearing until its distillation lands (PAR-0018's marker); marker
   form rule v2 and the classification rule are PAR-0002.

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

## Where things go

Three kinds of writing: a **rationale** — living, amended in place, and
still taking markers once accepted; a **primary** — the curated session
argument, frozen once wrapped; a **stub** — a marker carrier. **PAR is
Project Architecture Rationale**, deliberately not an ADR — and *record*
is not the word for a rationale; it pattern-matches to ADR semantics and
re-imports the immutability the rename retired (PAR-0001).

- A settled decision → the active planning document's gate; when it is an
  architecture decision (scope: PAR-0001), it is recorded as a project
  architecture rationale in `docs/par/` — with `docs/ARCHITECTURE.md`
  amended in the same commit —
  and the gate cites it. An exhausted plan freezes under its name and moves
  to `docs/archive/`; a successor cycle takes a new name.
- A rationale argued out in the session → its primary goes to
  `docs/archive/SESSION-<date>-<slug>.md` in the same commit, cited from
  the rationale's Context. Quote the person verbatim, compress the
  argument, keep the positions that lost, number the exchanges so they can
  be cited. Start it when the first decision lands, append as the argument
  runs, freeze it when the argument closes — one primary per argued
  decision-cluster; a sitting that settles separable arguments files
  separate primaries (PAR-0001). It opens with `Status: Open`; freezing
  is a deliberate wrap that flips it to `Status: Frozen` — never freeze
  just because a decision landed. A distillation files none — it is
  already reading its primary. Keep decisions and the alternatives that
  died with their reasons; never the route taken to reach them.
- A rationale not yet ready to govern → `Status: Proposed`; whatever
  governed before keeps governing, and the tier-1 citation stays put
  until acceptance. Hardening sessions are never owed — a deliberate
  attack on a draft is convened at judgment (PAR-0001). More than one
  primary per decision is expected.
- Execution guidance for a task — how it is done, never why → a guide
  in `how-to/<domain>/` (PAR-0003); folding it into a rationale is the
  ballooning force arriving by another door. Found inaccurate, a guide
  is repaired on the spot by whoever hit it.
- A not-yet-due intention → `DEFERRED.md`, always with the trigger that
  makes it due.
- A present gap with no better file to carry its marker → an `Owed:`
  marker line in `DEBT.md` (one per file; a second simultaneous gap is
  grammar-extension pressure, PAR-0002).
- A component the named milestone reaches but that isn't built → a
  placeholder: a real module at its real import path raising
  `sieve.debt.Owed` in marker form rule v2, quoting signatures only from
  the settled record, its docstring pointing at the governing sections.
- A settled system owed its rationale → a stub at its own number:
  status line, its `Owed:` marker, the citations that govern until
  acceptance — never rationale prose (PAR-0002, "What counts as debt").
- Any marker's reason opens with its statement stamp — the UTC time the
  debt was stated, `YYYYMMDDTHHMMSSZ`, hand-written at statement time.
  The suite catches malformed, duplicate, and implausible stamps; a
  discharged stamp is never reused.
- Everything derivable from the tree is derived, never hand-maintained (the
  anti-bureaucracy invariant, judged at conformance passes).

## Procedures

- After placing, removing, or rewording a marker: `python -m sieve.debt
  write`, and the regenerated ledger travels in the same commit as the
  change it reflects.
- The suite is green before a commit lands; green includes placeholder
  skips exactly matching the automatic ledger's test-tree entries. Nothing
  physically blocks committing red — possible is not in-contract.
- Chunk commits: rationale amendments land separately from placements
  and code.

## Never

- Hand-edit `DEBT-AUTO.md`.
- Invent an API surface a placeholder should merely point at.
- Build from `DEFERRED.md`.
- Catch `Owed` outside the debt machinery.
- Reuse a retired name — file-format fields, documents, or module paths.
- Commit raw session transcripts. The curated session record is the
  primary; a transcript is a worse one (PAR-0001).

## Session boundaries

Start with the orientation order. End with: working tree clean, suite
green, regen a no-op, and nothing valuable left unfiled — a decision,
intention, or gap that surfaced along the way gets its home (see "Where
things go") before the session closes. Durable context has homes; if
something fits none of them, that is a missing home to name, not a reason
to park prose somewhere unowned. A session record left `Status: Open` is
derivable debt announcing an unwrapped argument (`grep -l "^Status:
Open" docs/archive/SESSION-*.md`); wrap it at close, or leave it
announcing deliberately when the argument genuinely spans sittings.
