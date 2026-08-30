---
title: form
group: Substrate
position: 2
gloss: What a frame is, apart from which instant it is — which source pixels, at what sampling, in what format. All three at once, never one of them.
origin: emergent
defined: 2026-08-30
---

What a frame is, apart from which instant it is: which source pixels, at what
sampling, in what format. All three at once, never one of them — a form is not
a resolution and not a pixel format, because two consumers wanting one instant
at the same size in different formats want two arrays, and so do two wanting
one format at two crops. Form is one half of every key the substrate holds a
frame under; [position](position.md) is the other, and is the half that says
which instant.

The rect is in source pixels, so a form survives being resampled downstream and
still says which region of the recording it came from. That is what makes one
form able to answer for another.

## Where it lives

`contract/forms.py` holds the record, frozen so it can be half of a key, and
`Form.key()` spells one durably enough to match across runs — which is what
lets a cut written yesterday be recognised as answering today.

`grade` reads containment and the format matrix. It returns EXACT only from a
*native* form — one at source sampling — because the canonical construction is
crop, resize, convert in that order, and a frame already resized cannot be
re-cropped back onto it. A resampled form derives APPROX, which is showable and
never storable. Chroma is the hard floor in the other direction: gray cannot
answer for bgr at any grade.

The word predates this file across the whole substrate. `store.py` keys on it,
`serve.py` ranks routes by how far a held form is from the wanted one,
`chunks.py` can miss because a window was written in a different one, and the
tool contract gives it to both edge kinds that are pixels — a mask carries a
form for the same reason a frame does. Two experiments are named for the
negotiation between forms rather than for the frames being negotiated over:
`experiments/orchestrator-experiments/07-form-negotiation.py` and
`experiments/tool-experiments/02-form-derivation.py`.
