---
title: A kernel protocol that is not one frame in, one frame out
status: superseded
superseded_by: [a-kernel-that-sees-a-span, a-kernel-that-changes-the-rate]
opened: 2026-07-27T15:01:34-07:00
priority: unassessed
gated_on: >
  superseded 2026-07-29 — the trigger fired from inside the tree (REWORK.md
  R2: detection is the arrived case for windowed execution, and
  motion_history's own docstring asks for `Mode.WINDOWED`); the two remaining
  shapes split into one item each, and the decimator's anti-alias record
  moved with its shape
reads:
  - src/sieve/backend/dispatch.py
  - src/sieve/pipeline/executor.py
---

# A kernel protocol that is not one frame in, one frame out

> **Superseded 2026-07-29.** This item's gate was "a filter that actually
> needs one", and its blocker cited an enumeration that could not become
> filters before the protocol widened — while the protocol waited for a
> filter. Naming that deadlock was the unlock (REWORK.md R2): detection *is*
> the arrived case, so `a-kernel-that-sees-a-span` writes the windowed
> signature against it, and `a-kernel-that-changes-the-rate` keeps the
> decimator trigger and the anti-alias obligation recorded below. The
> caution this file preserves — a signature designed against zero instances
> locks in — was tested by `MergingKernel` and held: protocols here extend.
> The body stays as the record of both arguments.

**Why not now.** Two node shapes are valid graphs that the executor refuses at
run time, and both refuse for one reason: `Kernel` takes a frame and returns a
frame. `dispatch.py` declines to invent the second signature before a filter
needs one, and that reasoning has not changed — a signature designed against zero
instances is a signature every kernel written afterwards is stuck with.

**The third shape's trigger has fired and it has been moved.** Multi-upstream
nodes were the third entry in this list until 2026.07.26, when REFINED-VISION's
temporal section was read as a specification: every kind-amplifier it describes
is a *combination* of channels, which is what makes it a discriminant rather than
a filter, so the trigger this entry asked for — "a filter that actually needs
one" — is satisfied several times over. See
`docs/completed-todo/2026.07.26-multi-upstream-kernels.md`,
and `docs/REFINED-VISION.md` **G** for why it gates the rest of that section.
Per rule 5, it is gone from here rather than duplicated.

**What would make it the right time** for the two that remain. A filter that
actually needs one. Each has a different trigger and they are unlikely to arrive
together:

- `Mode.WINDOWED` — a filter needing a span before it can emit, e.g. a temporal
  median for background subtraction. This is the likeliest to arrive first.
- `rate_changing` — a decimator. The warmup arithmetic already handles rate
  exactly and is property-tested, so only the *call* is missing. **One thing to
  record before it lands**, because discovering it afterwards means invalidating
  results rather than a design: a decimator must carry its own temporal
  anti-alias lowpass, or high-frequency behaviour folds into the measured band
  and arrives disguised as something slower — grooming at 8 Hz sampled at 12 fps
  reads as 4 Hz. `wavelet.default_freqs`' 0.45·fps cap does not cover this; it
  stops the *analysis* asking for a frequency that is not there, not the
  *decimation* from manufacturing one. The anti-alias belongs inside the filter
  rather than as a separate node a user can forget to place, by the same
  reasoning that `downsample` offers no un-anti-aliased mode. See
  `docs/REFINED-VISION.md` **E**.

**A fourth shape was never deferred and is now built.** A *stateful streaming*
filter — one frame in, one frame out, carrying what it learned from the last
frame — needed no new arity, only somewhere to keep the state. `StatefulKernel`
and `KernelBinding.start` are that, and `background_ema` is the filter; see
`docs/completed-todo/2026.07.26-a-kernel-that-can-remember.md`. The three shapes
above stay here, and the precedent it sets for them is worth naming: the state
lives on the *binding*, made once per `execute`, so whatever a windowed or
merging kernel needs to be handed, it will be handed by `start` and not by a
registry entry.

One consequence for the WINDOWED trigger specifically. A temporal median was
named above as the likeliest first windowed filter, on the grounds that it is
what background subtraction wants; there is now an EMA background model that
does the job streaming. That does not remove the trigger — a median is robust to
transient occlusion in a way an EMA is not — but it does mean the first windowed
filter has to earn its place against something that already works, rather than
being the only way to get a background.

Read: `src/sieve/backend/dispatch.py` `Kernel` and `StatefulKernel`,
`src/sieve/pipeline/executor.py` `UnrunnableNodeError`.
