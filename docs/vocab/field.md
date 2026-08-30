---
title: field
group: Substrate
position: 10
gloss: Three live senses, two of them in one directory. A step's image-sized result, one number per pixel; a text box; and a record's attribute, which is Python's own word.
origin: emergent
status: unsettled
raised: 2026-08-30
---

Three senses, one of which the tree does not own, and the pair that collides
shares a directory. The substrate's field is a [step](step.md)'s image-sized
result — one number per pixel, float32, computed where it is drawn and
discarded there. The GUI's field is a text box. The third is Python's own,
arriving with the dataclasses import. Each is right in its own file; what is
wrong is that one directory holds two, and a line assigning to `field` there
has to be read right-to-left to know which.

## Senses

**A measurement per pixel**, in `contract/nodes.py` (`Step.field` produces it,
`reduce` compresses it to the scalar a series stores), in `session.py`, in
`gui/frame/stepwork.py`, and in both step tools — `lk_flow` scatters magnitudes
"onto the image grid as a field", `lag_mhi` puts decay and event "in one
field". It is the only word for the thing.

**A text box**, in `gui/primitives/field.py` — `Field`, `LineField`.

**A record's attribute**, in `library.py` and `store.py`, and in
`contract/nodes.py` itself, whose `Produced` docstring warns against "a record
that carried those fields" one class above the `Step` attribute named `field`.
`gui/frame/hotkeys.py` holds two senses ten lines apart: the dataclasses
import, then the widget in a comment.

## Fork

The third sense cannot be legislated away — it is the language's, and it is
always a call or a plural, which is most of why nothing has broken. The hazard
is that nothing *would* break loudly. `session.py` and `gui/frame/stepwork.py`
each bind a local field from a step and are one `@dataclass` away from also
importing the other; the shadow would be a local name, so what fails is a
`default_factory` far from the line that took the word.

Renaming the widget is cheap and pays twice: `gui/primitives/field.py` is also
the wrong home for `EDGE`, `RADIUS` and `RING_W`, which [edge](edge.md) flags
for the same reason. The argument against is that the array sense is about to
be forced — `contract/nodes.py` says the field is deliberately not among the
products, and declaring one reopens `KINDS`, since a measurement per pixel is
neither a picture nor a classification. Whatever that fourth kind is called is
this decision, in one line of `contract/edges.py`; if it lands as anything but
`field`, renaming the widget bought nothing. The trigger is a step consuming
another step's field, or a field that gets stored.
