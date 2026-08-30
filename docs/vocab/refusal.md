---
title: refusal
group: Substrate
position: 5
gloss: A no with a kind on it — what a producer answers with instead of a frame, drawn from a closed set of three: permanently gone, wrong shape, or not to this caller now.
origin: emergent
defined: 2026-08-30
---

A no with a kind on it: what a producer answers with instead of a frame, drawn
from a closed set of three. GONE is permanent — remember it, because asking
again costs the same and gets the same. FORM says the position is fine and the
shape asked for is not one this producer serves. LATER says the position is
deliverable, but not to this caller now. The kind is the whole word, because
what a caller may do with a no differs entirely by which one it is, and a
refusal without one is indistinguishable from a frame nobody has asked for yet.

Only GONE is a hole. See [form](form.md) for what a FORM refusal is about, and
[position](position.md) for what a GONE one is about.

## Where it lives

Every consumer spells the distinction out separately. `store.answer` files a
`GONE` into `missing` and caches neither of the others, since caching a moment
or a shape complaint turns one refusal into a permanent answer.
`fill._from_source` counts all three as missed and adds only `GONE` to `holes`.
`Serving.commit` clears the canvas only on `GONE` and otherwise holds the
picture, because a forward-only source asked behind its head refuses `LATER`
and blanking there would report a live source's whole past as empty.
`serve.Route` is closed for the reason given as "the reason `Refusal` is" — a
consumer that branches on a fixed set cannot anticipate a producer minting its
own name.

The pairing with `Answer` is what makes the three readable at all. An answer is
a frame or a refusal, never both and never neither — `__post_init__` enforces
it — so the old `None` return, which meant all three at once, cannot be written
any more; a caller that reaches past the record gets an AttributeError rather
than a plausible blank. `read_form` is the one place that acts on a kind
without asking its caller: a `FORM` refusal is retried at the producer's own
form and built down, which is free precisely because a source refuses `FORM`
before decoding anything.

Nothing coordinated this. `store.py`, `fill.py`, `serve.py` and three source
tools written weeks apart all say refusal for the record and name the kind at
the point they branch on it, and each of the three kinds is there because one
of those tools could not be written without it: `video_file_source` refuses
`FORM` ahead of the decode and `GONE` at a packet that will never decode,
`image_directory_source` is the folder that forced `FORM` to exist at all (an
image of another size is a good picture in a shape the source could not
declare), and `synthetic_source` is the only one that can be asked to produce
each kind on demand — and the only raiser of `LATER`, the kind that had nowhere
to go before, when it had to raise instead because answering `None` would have
filed a live source's entire past as permanent holes.

The verb is looser than the noun and deliberately left so: prose in
`registry.py` and `footage.py` says a gate or a cost "refuses" in the ordinary
English sense, which is not this record and reads as itself.
