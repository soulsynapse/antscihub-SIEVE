# Session record — 2026-08-02 — session records announce their own state

Status: Open
Date: 2026-08-02

Curated primary for the freeze-is-deliberate rule and the `Status: Open`
marker added to PAR-0001's session-record doctrine. Doctrine: PAR-0001.

## Exchange 1 — freezing is deliberate, and Open is a marker

Kendrick, verbatim, correcting the day's practice of declaring records
frozen the moment their argument seemed settled:

> "Also, just circling back for a second, the frozen/not frozen sessions
> can be updated at-will until the session actually is closed. The
> temptation is to add the reasoning as soon as any kind of decision is
> made, but the back and forth is actually what dictates when it's
> frozen or not. For session logs, you should include some kind of
> pointer so that any session log that is not deliberately closed can
> announce the user didn't correctly close out the session with a wrap
> up making sure the logic wasn't lost. That should probably exist as
> some kind of automatic debt pointer."

Design landed in PAR-0001, chosen for symmetry with the repo's existing
marker mechanics — the status line is its own debt entry, the way a
placeholder and a `Proposed` rationale are: `Status: Open` from a
record's first line, flipped to `Status: Frozen` only by a deliberate
wrap confirming the logic landed; `grep -l "^Status: Open"
docs/archive/SESSION-*.md` as the derivation, nothing maintained
anywhere.

Calls made in the design, open to challenge: pre-convention records are
grandfathered rather than retro-edited, because never-edit outranks
marker uniformity and all of them were deliberately closed; the
derivation cannot distinguish an argument deliberately spanning sittings
from an abandoned one — the date on an Open record is the tiebreaker,
and the read is the human's, consistent with the tipping-point rule; and
the residual leniency is named rather than hidden — a record created
without a status line escapes the grep, guarded only by the form rule in
PAR-0001 and `AGENTS.md`.
