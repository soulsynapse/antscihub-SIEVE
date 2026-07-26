# Insertion & swap interaction

A clickable mockup of the operation-stack insertion flow proposed in
`docs/filter-tab-parity-plan.md` (stage-sectioned stack, "common here" picker).
It exists to settle *interaction* decisions by mouse, and to pin them in
writing so later work — by anyone, at any capability — does not drift.

## Run

```
uv run python mockups/insertion/stack_insert.py --variant repair
uv run python mockups/insertion/stack_insert.py --variant strict
```

PNG review without a display: `--shot {gap,picker,catalog,conflict} --png out.png`.

## The interaction contract (what is being pinned)

1. **Seams are invisible until hovered.** The gap between two steps shows
   nothing at rest. On hover it grows a hairline across the stack width and a
   circled plus at center. Click anywhere in the gap — not just the plus.
2. **Click a seam → "Common here" popover.** A short curated list for that
   seam (curation is keyed on the type flowing through the seam), each item a
   name plus a one-line blurb. Below a rule: "See all operations… (N fit this
   seam)".
3. **See all → catalogue overlay.** Scrim over the stack, centered card:
   search box; the full list of operations that fit the seam's incoming type
   (operations that don't fit the seam at all are not listed); a guidance
   pane on the right built from the filter's markdown (`summary`, When to use
   it, What it does not do, cost); Insert button.
4. **Replace = the same picker.** Hovering a step reveals `⋯` (replace);
   a conflicted step shows explicit `Swap… / Remove` buttons. Both open the
   identical popover/catalogue flow with the caption "REPLACE ‹name›".
5. **Stage structure is fixed.** Stage headers (SPATIAL PREP, SIGNAL
   EXTRACTION, TEMPORAL FILTER, DETECTION) carry a right-aligned type chip
   (`image → per-block series`) — that chip is how order-of-operations is
   taught. Steps insert *within* the structure; the stages themselves are not
   draggable, addable, or removable.
6. **Validity is derived, never stored.** One walk down the stack grades each
   step ok / conflict (first type mismatch) / unreached (after one). The
   footer reports "runs · N steps · Σ ms/frame" or "won't run — N conflicts".

## The open decision (why there are two variants)

Inserting an operation can invalidate the step below it (insert an extraction
above `normalize` and `normalize` now receives a per-block series).

- `--variant strict` — prevention. The popover simply omits offenders (with a
  count: "2 hidden — they would break the step below"). The catalogue shows
  them disabled, and the guidance pane names the way out: replace the step
  below first.
- `--variant repair` — permit-then-repair. The popover and catalogue offer
  them with a warning badge ("needs a change below"). Inserting one puts the
  step below into a conflict state: red edge, "expects image · receiving
  per-block series", inline `Swap… / Remove`, and the stack won't run until
  resolved. `Swap…` reopens the picker for that step, now filtered to the new
  incoming type.

Try both; the thing to feel for is whether strict's hidden options make the
catalogue feel dishonest, and whether repair's broken-but-visible state reads
as guidance or as an error you were allowed to make.

## What is fake

Everything: the registry (twelve invented operations), costs, captions, and
the palette (deliberately not the app's — the skin is not the decision).
Unlike `mockups/filter_tab.py`, no real `src/` widgets are used; this mockup
is about a panel that does not exist yet, not about how existing widgets
compose.

## What survives

Per `mockups/README.md`: not the code. The interaction contract above gets
recorded in the TODO item that builds the real stack panel, the chosen
variant gets written down with its reason, and this folder is deleted.
