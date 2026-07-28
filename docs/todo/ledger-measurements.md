---
title: The ledger's two unmeasured numbers
status: deferred
serves: [A2]
opened: 2026-07-27
gated_on: >
  a floor reading on a *small* machine. The instrumented session ran 2026-07-28
  (docs/findings/2026.07.28-the-session-floor-is-the-window.md) and changed the
  question: there is no machine-independent floor, session memory tracks the
  working window, and memory_reserve's fraction term therefore models the wrong
  variable — least wrongly on the largest machine and worst on the smallest.
  The load-bearing measurement is now one 30-second reading on ~8 GB hardware,
  which nobody has. H4 is answered only in the weak sense and is blocked on
  docs/todo/ledger-producers.md rather than on a session.
reads:
  - src/sieve/gui/concurrency.py
  - docs/todo/cache-eviction.md
  - docs/todo/proxy-retention-policy.md
---

# The ledger's two unmeasured numbers

The resource ledger (completed 2026-07-27) landed the resolver, the byte
column, and the resolved worker split — with three of its hypotheses left as
stated guesses because each needs the reference footage or a live session, not
a unit test. This item is those measurements, lifted verbatim from the ledger
item so they do not dissolve into its completion entry. Each outcome is a
finding in `docs/findings/`; the ledger's constants then cite it.

**H2 is done.** It was the only one of the three that a headless process could
take, so it was split into `docs/todo/luma-worker-sweep.md` and completed
2026-07-28 —
`docs/findings/2026.07.28-the-luma-path-has-almost-nothing-left-to-thread.md`.
What remains is the two that need a person at the keyboard.

- **H3 — the reserve.** ~~Measure the session's RSS floor (app open, video
  loaded, nothing rendered) on the reference workstation and once on a small
  machine.~~ **Run 2026-07-28 on the large machine, and the premise did not
  survive.** There is no floor: idle with a large working window the session
  climbed 3.39 → 4.72 GB over 95 s and released; idle with a shrunk window it
  sat flat at 1.61–1.71 GB for 330 s. Session memory tracks *window extent*,
  which the user sets, while `memory_reserve` scales with *total RAM*. The
  formula is least wrong on the biggest machine and worst on the smallest —
  which is the half nobody has measured, and is now the only reading that
  matters. See `docs/findings/2026.07.28-the-session-floor-is-the-window.md`.
- **H4 — the ledger accounts for what the process actually holds.**
  Instrument peak RSS over a reference tuning session and compare to
  declared-sum plus reserve. A large gap means an undeclared consumer
  exists; finding it is the point. This is also the measurement
  `docs/todo/cache-eviction.md` says nobody has taken — one instrumented
  session serves both. **Answered weakly 2026-07-28**: peak 4.72 GB against
  declared 1.15 + reserve 4.29 = 5.44 GB, so no gross overrun. But the peak
  cannot be split into declared-versus-undeclared, because nothing publishes
  what the four consumers actually held — so the question H4 was written for
  is unanswerable from outside the process. It is now blocked on
  `docs/todo/ledger-producers.md`, not on another session.

The declared-floor test in `tests/unit/test_concurrency.py` and the honest
gap (`UNBOUNDED`) already say what the ledger cannot: until H4 runs, the sum
describes the *declared* session, not necessarily the whole one.

## Why this waits rather than being approximated

An RSS floor taken under `QT_QPA_PLATFORM=offscreen` in a headless process is
not the number `memory_reserve` is trying to hold back: no swapchain, no
driver allocation, no font cache the size of a real desktop's, and no decoder
warmed by an actual scrub. It would be a plausible-looking constant with a
worse provenance than the formula it replaced, which rule 6 says is the failure
mode to avoid — the guess is currently *labelled* a guess, and a measured-looking
wrong number is a downgrade.

H4 is the harder half of the same thing: "peak RSS over a reference tuning
session" only means something if the session is a real one. A scripted sequence
of renders would measure the paths the script chose, and the point of H4 is to
find a consumer nobody declared — which is to say, a path nobody thought to
script.

**The trigger is the same one `docs/todo/proxy-retention-policy.md` is waiting
on**: one recorded tuning session on real footage. Whoever produces that trace
should have `SIEVE_RETENTION_TRACE` set *and* an RSS sampler running, because
the expensive part is the person's few minutes and both instruments ride along
for free.
