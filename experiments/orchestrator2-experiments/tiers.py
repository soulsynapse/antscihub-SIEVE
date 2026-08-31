"""What one decode is stored as, and how each form is made from it (ADR-0017).

A fetcher hands back the source plane whatever form asked for it, so which
form a pick names decides what is *stored* and not what is read. This is the
map the dispatcher fetches through: a key, and an opaque callable that makes
that key's payload from the plane. The dispatcher never learns what a form
is; it holds the callable and calls it.

**Two tiers, and why they are not interchangeable.** Display sampling is what
a canvas wants and is a sixteenth of the bytes at 1/4; source sampling is what
may be recorded. The asymmetry is `forms.py`'s law and not a preference: a
display row derived from the source plane grades EXACT — the plane is native,
the rect contains — so it is admissible; anything derived from the *display*
row has resampled twice and grades APPROX, which may be shown and never kept.
So a step reads the source tier or it reads nothing.

It lives in its own file because both the explorer and `09-display-sampling`
build the same two forms, and a second spelling of one form is a key that
lies: `forms.build` is canonical precisely so two producers of a form agree in
the low bits, and two callers constructing "the display form" slightly
differently would defeat that in the one place a store cannot detect it.
"""

from __future__ import annotations

from typing import Any, Callable

import forms as forms_mod


def source_form(width: int, height: int) -> forms_mod.Form:
    """The whole luma plane as decoded — what every other form derives from."""
    return forms_mod.Form((0, 0, width, height), (width, height), "gray")


def display_form(width: int, height: int, divisor: int) -> forms_mod.Form:
    """The whole frame at 1/divisor in each axis, gray.

    Whole-extent because that is what a canvas shows, and a fixed divisor
    because `AVCodecContext.lowres` takes one — 1/2, 1/4, 1/8. A form keyed to
    the canvas size would name a window, which `forms.py` refuses for the
    reason that matters here: a key naming a session cannot be matched across
    runs, and this one is a cache key.
    """
    return forms_mod.Form((0, 0, width, height),
                          (width // divisor, height // divisor), "gray")


def tiers(source: forms_mod.Form,
          display: forms_mod.Form | None) -> dict[str, Callable[[Any], Any]]:
    """The dispatcher's `tiers` map for these two forms.

    Identity for the source form, because that is already what the fetcher
    returns. `forms.derive` for the display form, so what lands in the pool
    went through the canonical construction and is admissible rather than a
    placeholder. A display form equal to the source form collapses to one
    tier, which is every measurement in this folder before 2026-08-31.
    """
    made = {source.key(): (lambda arr: arr)}
    if display is not None and display.key() != source.key():
        made[display.key()] = (
            lambda arr: forms_mod.derive(arr, source, display)[0])
    return made
