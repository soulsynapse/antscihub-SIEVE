---
title: Whether an external input carries a portable identity, so substitution is not silent
status: deferred
deferred_for: decision
gated_on: Kendrick deciding whether SIEVE records something that identifies an external input across machines — a content hash and a home for it — or the reproducibility promise stays one that detects absence and not substitution
priority: high
phase: "03"
opened: 2026-08-07
---

# Whether an external input carries a portable identity, so substitution is not silent

[VISION.md](../VISION.md)'s reviewer paragraph now covers projects with
external inputs: they load the video, the project, and the files the project
names, "and have SIEVE run. It outputs the same results." What backs the new
half of that is
[the derived list](a-run-names-the-external-files-it-needs-before-it-starts.md),
and by its own statement it buys naming and absence, not identity. A reviewer
whose own `*_bg.png` sits at the matching name resolves it, the run completes,
and the numbers differ with no symptom.

The residue is what this item is. `whether-a-project-declares-the-inputs-it-depends-on`
asked two questions and dd333f8 answered one of them — whether the promise
grows to cover external inputs, yes. It priced the second in passing and did
not settle it: a portable identity is a content hash, which is a read of every
external file at save time and again at check time and is not free for a video;
a home, which the identity line in `core/pipeline_model.py` constrains, since
everything on `Node` feeds the cache key and nothing else does, so a recorded
identity sits on `Project` keyed by node id, the shape `checkpoints`, `outputs`
and `crops` already use, and it must not move a key; and a staleness surface,
because a colleague who legitimately regenerates the background changes the
file on purpose and every run refuses until something can say "yes, this one".
Whether a mismatch refuses or reports is part of the same decision — reporting
keeps a stale project runnable and makes the promise advisory, refusing makes
it binding and makes the staleness path required.

The reason this is high and not a note is that the claim is already stated.
Under the narrowing that was rejected, a project with external inputs was
outside the promise and nothing was owed. Under the reading that landed it is
inside, and today the only thing standing between "it outputs the same results"
and a reviewer reading a different background is that the file is at the same
path. That is the same gap the source video has, whose `source_identity` is
`abspath|size|mtime_ns` — a cache key, not a portable identity, and recorded
nowhere in the document (see
[the source identity has no consumer and no case](the-source-identity-has-no-consumer-and-no-case.md),
which is about testing the three facts, not about carrying them between
machines). It is tolerable for the video only because the hand-over is explicit
and singular; the picker and folder scenarios are neither.

A worker can build a content hash. It cannot decide that SIEVE pays for one, or
that a mismatch stops a run — so this waits on Kendrick, and no phase boundary
waits on it. The cheap half is available either way and is where the derived-list
item already points: whatever reports "nothing missing" says what it checked, so
that sentence is never read as "the same files".
