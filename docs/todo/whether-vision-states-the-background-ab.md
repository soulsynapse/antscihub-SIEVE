---
title: Whether VISION's picker scenario states an A/B of two backgrounds
status: deferred
deferred_for: decision
gated_on: Kendrick deciding whether the scenario compares two backgrounds at once — which costs the multi-root graph — or stays as one outside file standing where a generated one stood
priority: normal
phase: "03"
opened: 2026-08-07
---

# Whether VISION's picker scenario states an A/B of two backgrounds

Until `f4f7991` the paragraph opened on a user who "have two different
generated backgrounds and they want to know which one does better", then
described swapping the generating step out for a file picker — which leaves one
candidate, so the comparison the opening promised cannot happen. That run
resolved the contradiction by dropping the comparison: the opening now says the
background was made outside the project and stands where the generated one
stood, which is the same sentence
[ADR-18](../adr/a-users-file-wires-in-like-any-other-input.md) already used for
the case it is for.

That is the reading that costs nothing, and it is not obviously the one
intended. A real A/B needs both roots alive at once and a control that switches
which one feeds the subtraction — the multi-root graph
[the first source tool](the-first-source-tool-moves-the-three-single-root-assumptions.md)
is about, plus a comparison surface nothing has scoped. The choice is which of
two things VISION binds: a file standing in for a generated input, or tuning by
comparison between two inputs. Only the second makes the picker a tool for
deciding rather than a tool for substituting, and only Kendrick can say which
the scenario was for. Restoring it would be its own paragraph saying outright
what it costs, not a clause smuggled back into this one.

No boundary waits on this. Phase 4 closes either way, and the picker mechanism
is specified without it.
