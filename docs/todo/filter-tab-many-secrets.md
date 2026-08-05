---
title: filter_tab.py owns six secrets
status: open
opened: 2026-08-04T21:41:58-07:00
priority: normal
gated_on: nothing structurally
reads: [src/sieve/gui/filter_tab.py, src/sieve/gui/chain_model.py, src/sieve/gui/wizard.py]
---

# filter_tab.py owns six secrets

Flagged out of the docstring-audit loop, whose tooling was deleted along with
the loop itself in `6317670` — this item is the part of its output that
outlived it. The file cannot be brought to the one-file-one-secret convention
because it plainly hides more than one design decision, and the existing
module docstring already shows it — it is organized as five bolded
sub-paragraphs, one per decision, which is not the shape a single secret
takes. At roughly 500 words it is already well over the 250-word cap
(`filter_tab.py` is not one of the three `CONTRACT_MODULES`), and every
paragraph is load-bearing: none of the five restates what the code already
says.

Six decisions the file is currently the only place that knows:

1. **The composite-pane refresh state machine.** A single-frame request for
   the composite must never displace the window render the graphs are
   waiting on, and at most one composite refresh may be outstanding at a
   time (a second single-frame request kills the first before its only
   delivery). `_composite_outstanding`, `_composite_deferred`,
   `_composite_revisions`, `_refresh_composite`, `_release_composite_slot`.
2. **The two-tier drag discipline, replicated across every detector
   control.** Frequency band, value band, count threshold, D window, and
   solo each get a cheap local repaint on drag (`_cheap_retune` and its
   per-control wrappers) and a full document-committed derive on release —
   the same split stated five times because each control's commit condition
   differs slightly (freq band's echo-compares-equal case, D's gesture
   token, solo's exemption from `recompute` entirely).
3. **Knob-edit routing through the document, with a local fallback.**
   `_submit_params`/`_submit_detector` decide, per edit, whether the target
   node is in the document's pipeline yet; if not (a provisional wizard
   step, or no pipeline open) the same edit is a plain local rewrite of the
   chain value instead of a two-write document command.
4. **The wizard session lifecycle.** Opening snapshots the chain and the
   undo-stack index; a hover preview steals the composite's one outstanding
   slot rather than queuing behind it; Accept and Cancel each reconcile two
   different write paths (document-routed tuning vs. the provisional step
   that never reached the document) back into one consistent chain.
5. **The source/crop boundary card and its write pass.** The four-state
   wording (absent/at-rest/stale/writing), sourced from the file on disk
   rather than trusted from the record, and the materialize/discard/cancel
   gesture that moves between them.
6. **Chain structure editing as document-routed macros.** Remove and reset
   each collapse what used to be several document writes into one undo
   entry, with reset's "parameters-not-structure" scope decision.

No co-change check was run: the flag-path check in CLAUDE.md compares two
*existing* files' commit history to test whether a proposed seam already
holds. Here there is one file and no candidate split already exists to
measure — the six decisions above are described by responsibility, not by a
line range, because splitting a single `QWidget` subclass into pieces is
itself the architecture decision this item is deferring to Kendrick, not a
mechanical file cut.

**2026-08-04, re-checked independently** (docstring-audit trial, told to treat
this flag as unassessed rather than as evidence): confirms FLAGGED, for the
same six decisions, after reading the file end to end and condensing what
could be condensed without cutting anything with a surviving mistake. Module
docstring 531 → 197 words (compressed onto the "one chain, resolved from the
document, driving every surface" framing and a pointer here instead of
restating each decision's mechanism, which is already stated once at the site
that earns it — `_refresh_composite`, `_submit_params`/`_submit_detector`,
`_on_window_frames`, `_open_wizard`, `_refresh_source_card`, `_on_reset`).
14 trivial accessor-property docstrings deleted (derivable from name + return
type, no mistake nameable). Total prose 7,474 → 6,988 words. The condensing
itself was never committed and its run report died with the loop; what is
recorded here is the flag, which is what outlives either.

The co-change check *is* now partly answerable, against files that already
exist: `git log --no-merges` over `src/sieve/gui/*.py`, 38 commits touching
`filter_tab.py`, of which it changes alone in 26–33 depending on the
candidate. Composite specifically: `composite_view.py` + `filter_tab.py` co-
change 10 times against 1 commit where `composite_view.py` changes alone —
consistent with CLAUDE.md's own 2026-07-28 reading of this exact pair ("5
together, 1 alone... not a working seam") and confirming it again six days
later. `wizard.py`/`wizard_model.py` co-change with `filter_tab.py` only 7
times each, against `filter_tab.py` alone 31 times, and neither ever changes
without it (0 alone) — the wizard lifecycle (decision 4) has never yet earned
its own commit, so there is no history evidence either way for the seam
`filter-tab-is-eleven-jobs.md` proposes there; the seam judgment for that item
has to rest on the signal-crossing test it names, not on git.
`materialize_worker.py`/`crop_binding.py` (decision 5) co-change only 5 times
each against `filter_tab.py` alone 33 times — the loosest coupling measured,
weakly favoring that a source/crop-card extraction would hold, for whatever a
count this small is worth.

This does not change the recommendation: `docs/todo/filter-tab-is-eleven-jobs.md`
already carries the extraction order (wizard, then composite, then the band
handlers), the explicit warning that this file's coupling is Qt signal wiring
invisible to both the type checker and import-linter, and the sequencing note
that two of its seams shrink to bookkeeping once `detector-state-dies` lands.
This item stays open as the record of *why* the file is flagged (the six
secrets); the eleven-jobs item is where the split itself is planned. Neither
should restate the other's content going forward.

A straight one-class-per-decision split is not obviously right either: 1
and 4 already share the composite-grab mailbox pattern with the wizard's own
hover preview (decision 4 calls into decision 1's `_composite_revisions`
machinery directly), and 2 threads through every other decision's commit
path. A plausible shape is to keep `FilterTab` as the Qt glue and extract
owned collaborator objects it delegates to — a composite-refresh controller
for (1), and a tuning-router object for (2)+(3) — rather than five new
top-level modules; but that is a judgment call about where the coupling
actually is, which is exactly what this item exists to hand off rather than
guess at under the audit loop's one-file scope.
