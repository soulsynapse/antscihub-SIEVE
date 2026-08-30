---
title: form
group: Substrate
position: 2
gloss: What a frame is, apart from which instant it is — which source pixels, at what sampling, in what format. All three at once, never one of them.
origin: emergent
defined: 2026-08-30
---

What a frame is, apart from which instant it is: which source pixels, at what
sampling, in what format. All three at once, never one of them — not a
resolution and not a pixel format, because two consumers wanting one instant at
one size in different formats want two arrays, and so do two wanting one format
at two crops.

Where a form sits differs by tier. In the store it is half of a key, beside the
[position](position.md); below the store it is a mode, where a tier holds one
form at a time and changing it wipes what was written rather than adding a
key.

## Where it lives

`contract/forms.py`, frozen so it can be half of a key. The rect is in source
pixels, so a form survives resampling and still says which region it came from;
`Form.key()` spells that durably enough to match across runs.

`grade` reads containment and the format matrix. It returns EXACT only from a
*native* form — one at source sampling — because the canonical construction is
crop, resize, convert in that order, and a frame already resized cannot be
re-cropped back onto it. A resampled form derives APPROX: showable, never
storable. Chroma is the floor in the other direction — gray cannot answer for
bgr at any grade.

`Store` is keyed by `(position, form)`. Equality is not the whole order on
forms, so a miss asks `dominator` second, and that never crosses pixel formats
— narrower than `grade`, for the low-bit reason its docstring gives.

`ChunkStore` holds one form at a time and takes gray only. The proxy is one
resampled form over the whole source, so everything derived from it grades
APPROX. `Serving.held_form` is that single form — which is why the chunk tier
refuses a position it has, never having written it in the form asked for.

Both edge kinds that are pixels carry a form.
