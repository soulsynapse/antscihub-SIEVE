---
title: refusal
group: Substrate
position: 5
gloss: A no with a kind on it — what a producer answers with instead of a frame, drawn from a closed set of three: permanently gone, wrong shape, or not to this caller now.
origin: emergent
defined: 2026-08-30
---

A no with a kind on it: what a producer answers with instead of a frame, from a
closed set of three. GONE is permanent — remember it, because asking again
costs the same and gets the same. FORM says the position is fine and the shape
asked for is not one this producer serves. LATER says the position is
deliverable, but not to this caller now. The kind is the whole word: what a
caller may do with a no differs entirely by which it is. Only GONE is a hole. See [form](form.md) for what a FORM refusal is about, and
[position](position.md) for a GONE one.

## Where it lives

Every consumer spells it out separately. `store.answer` files a `GONE` into
`missing` and caches neither of the others: caching a moment or a shape
complaint turns one refusal into a permanent answer.
`fill._from_source` adds only `GONE` to `holes`. `Serving.commit` blanks the
canvas only on `GONE`: a forward-only source asked behind its head refuses
`LATER`, and blanking there would report its whole past as empty.

`Answer` is what makes the three readable — a frame or a refusal, never both
and never neither, enforced in `__post_init__`, so the old `None` return that
meant all three at once is unwritable. `read_form` is the one place that acts on a kind
without asking its caller: a `FORM` refusal is retried at the producer's own
form and built down, free because `FORM` comes before any decode.

Each kind exists because one source tool could not be written without it.
`video_file_source` refuses `FORM` ahead of the decode and `GONE` at a packet
that will never decode. `image_directory_source` forced `FORM` to exist: an
image of another size is a good picture in a shape the source could not
declare. `synthetic_source` is the only raiser of `LATER`, which had nowhere to
go before — answering `None` would have filed a live source's past as permanent
holes.
