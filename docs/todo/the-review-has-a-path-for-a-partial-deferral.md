---
title: The review has a path for a partial deferral
priority: normal
status: open
gated_on: nothing
opened: 2026-08-07
---

# The review has a path for a partial deferral

The review's deferral branch says amend the criterion and set the item back
to `open`, which assumes the amendment leaves work to do. 01.2 committed
everything except the struck part, so the amended criterion passed the moment
it was written and `open` meant a session would be started to do nothing
(`findings/loop/2026.08.07-the-review-prompt-has-no-path-for-a-partial-deferral.md`).

The missing case is: the criterion was wrong, the work under the surviving
half is done, and what the strike removed is now somebody else's item. That
is `done` plus a minted item, not `open` — and the minted item is what keeps
the struck subject from vanishing, which is how 02.1's format-contract split
was handled by hand.

02.1's review found the same gap from the other side: it could settle one of
three blockers and not the other two, and had no status meaning "partly
settled, still stopped". It wrote a section in the item instead, which worked
because a human read it.
