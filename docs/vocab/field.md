---
title: field
group: Substrate
position: 10
gloss: Three live senses, two of them in one directory. A step's image-sized result, one number per pixel; a text box; and a record's attribute, which is Python's own word.
origin: emergent
status: unsettled
raised: 2026-08-30
---

Three live senses, one of which the tree does not own, and the pair that
collides shares a directory. The substrate's field is a [step](step.md)'s
image-sized result — one number per pixel, float32, computed where it is drawn
and discarded there. The GUI's field is a text box. The third is Python's own,
the one that arrives with the dataclasses import, and the attributes of a
record in prose. Every sense is right in its own file; what is wrong is that one
directory has two of them, and a reader of a line assigning to `field` there has
to look at the right-hand side to know which.

## Senses

**A measurement per pixel**, in `contract/nodes.py` (`Step.field` produces the
image-sized result; `reduce` compresses it to the scalar a series stores), in
`session.py`'s `run_step`, `note_field` and `evaluate_step`, in
`gui/frame/stepwork.py`, in `surfaces.py`'s overlay, and in both step tools —
`lk_flow` scatters magnitudes "onto the image grid as a field", `lag_mhi` puts
decay and event "in one field". Consistent everywhere it appears, and unnamed
by anything else: it is the only word for the thing.

**A text box**, in `gui/primitives/field.py` — `Field`, `LineField`, and the
comment in `gui/frame/hotkeys.py` about "a focused text field" getting its own
space bar.

**A record's attribute**, in `library.py` (which imports both `field` and
`fields` from dataclasses), in `store.py`'s "a property and not a field",
`gui/view/transport/geometry.py`'s "four fields",
`gui/view/project_list/project.py`'s "every field is a", and in
`contract/nodes.py`, whose `Produced` docstring warns against "a record that
carried those fields" one class above the `Step` attribute named `field`.
`gui/frame/hotkeys.py` holds two of the three ten lines apart: it binds `field`
from dataclasses at the import, and means the widget in the comment under it.

## Fork

The third sense cannot be legislated away — it is the language's word, it
arrives with the import, and it is always either a call or a plural, which is
most of why nothing has broken yet. The hazard is that nothing *would* break
loudly. No module today both imports `dataclasses.field` and binds a local
`field` from a step; `session.py` and `gui/frame/stepwork.py` each do the
second and are one `@dataclass` away from the first, and the shadow would be a
local name, so what fails is a `default_factory` far from the line that took
the word.

Which sense keeps the plain word. Renaming the widget is the cheap direction
and pays twice: `gui/primitives/field.py` is already the wrong home for `EDGE`,
`RADIUS` and `RING_W`, which `check`, `select`, `segmented` and `tabs` import
from it and which [edge](edge.md) flags for the same reason, so one rename
moves two collisions at once. The argument against is that the array sense is
the one that has never been written down anywhere binding, and it is about to
be forced: `contract/nodes.py` says the field is deliberately not among the
products, and that declaring one reopens `KINDS`, because a measurement per
pixel is neither a picture nor a classification. Whatever that fourth kind is
called is this decision, made in one line of `contract/edges.py` by whoever
adds it — and if it lands as anything but `field`, renaming the widget bought
nothing. Not decided: the trigger is a step consuming another step's field, or
a field that gets stored.
