---
title: Declared means verified
adr: 8
position: "01.04"
status: settled
decided: 2026-08-06
---

A spec declaration is either consumed by running machinery or refused by name
at registration; nothing is stored against a future consumer, and no
declaration certifies its own correctness.

Why: v2.5's design session hit the self-certifying declaration three times —
the random-access flag, a lowering's claimed output type, the catalog entry's
claim of generality — and each patch was a conformance test bolted on after
the fact; its own verdict was that declares-itself-correct fails at every
layer (`docs/archive/DESIGN-SESSION.md`, Exchanges 5 and 8). v2 shipped the
quieter half of the lesson: declarations serving deferred machinery — cost
estimates, `backend_agnostic`, `frame_bytes_ratio` — sat unread, anchoring
readers to paths that did not exist. The registration gate refuses both:
declarable means runnable, or refused by name. One licensed shape: a
declaration whose consumer is scheduled by the plan (presentation
stereotypes, read first in Phase 7) is admitted early only with a
registration-time validity check — a closed vocabulary, refusal by name —
standing in as the consumer until the real one lands.
