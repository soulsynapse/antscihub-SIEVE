---
title: The crop fan draws the regions in the gap below the card
step: "09.8"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k crop_fan"
opened: 2026-08-09
---

# The crop fan draws the regions in the gap below the card

The crop step cuts a region per dish, and the branch is drawn where it is:
a row of numbered squares in the gap between the crop card and its reader,
left-aligned on the trunk so every arrow stays vertical, all arrows leaving
the one card that made them, the continuing arrow leaving the square the
user selected. Selecting a square is the same notification a canvas drag
sends — the chain below is drawn for that region; the others are the same
chain, unwalked. The card holds the count and the +/− that change it;
adding a region selects it. MOCKUP-MAP.md rows "Crop cuts regions, plural"
and "The crop fan" — `CROPS`, `_crop_count`, `_CropFan`,
`_paint_fanned_edge`, `select_crop` in the referent. What a region *is* in
the document is the tree's to say — schema v1 minted the replicate as an
ordered set of named regions (Phase 2), and this surface is that value's
editor, not a second home for it; if the tree's crop still holds one rect,
that collision comes back to review rather than being settled here.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k crop_fan
    119 deselected in 0.64s
    exit: 5
