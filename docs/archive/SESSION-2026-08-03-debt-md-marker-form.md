# Session: DEBT.md entries are marker lines

Status: Frozen
Date: 2026-08-03

One exchange, landed during the v2 dissolution. The occasion: the
dissolution of `DEBT.md`'s entries into stub records was mid-landing
when Kendrick generalized the move to the file itself.

## Exchange 1 — the last resort joins the surface

Kendrick: "also, if it isn't already, a very obvious move: DEBT.md
follows the same debt format that gets picked up in all the other
files, making debt-auto the only file that ever needs to be read"

It already is, by construction — the finding is that nothing in the
machinery needed to change. `DEBT.md` is a tracked UTF-8 file at the
repo root and is not among the enumerator's named boundaries (sentinel,
ledger, `docs/archive/`), so a column-0 `Owed: <stamp>: <reason>` line
there enumerates today, keyed `(DEBT.md, <file>)`. What the move
changes is doctrine, not code: an entry in the last-resort file is
stated *as a marker*, so even hand-stated debt enumerates, and
`DEBT-AUTO.txt` becomes the only file ever read for present debt. The
"last resort" thereby sharpens from a format exception into a pure
location rule — where a marker lands when no better file exists to
carry it — and PAR-0002's "no in-tree marker can carry" phrasing was
reworded, since every present debt is now an in-tree marker.

One limit, named rather than hidden: the text surface's grain is one
marker per file, so `DEBT.md` carries one gap at a time. This is
doctrine agreeing with itself rather than a defect — PAR-0002's
Outcomes already read a nonempty `DEBT.md` as standing pressure to
extend the marker grammar, and a second simultaneous gap now delivers
that pressure structurally, as an enumeration error instead of a judged
prose state.

Not resolved here, deliberately: the nebulous-role challenge in
PAR-0002 (whether an always-empty escape valve earns its root slot, or
retires until a grammar failure recreates it). The move sharpens the
file's role but the challenge is about the file's existence when empty,
which marker-form entries do not touch. It still resolves on observed
steady state.
