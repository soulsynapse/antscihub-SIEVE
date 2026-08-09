# What the mockup settles

`mockup/mockup.py` is the settled v3 surface
([adr/a-position-is-asked-for-in-the-chain.md](adr/a-position-is-asked-for-in-the-chain.md)).
This map is its reading guide: what the mockup decides that the tree's
`src/sieve/gui` does not yet have, where each decision lives in the file, and
— as load-bearing as the list itself — what the mockup does *not* decide.
Symbols, not line numbers: the file moves under licensed revisions.

The build history is intent evidence: every reshaping was ordered through the
orchestrator on 2026-08-08/09, so each surface below traces to an instruction
of Kendrick's, readable in `~/.agent-orchestrator/logs/`. The four inventions
the module docstring names (`PinnedStep`, `MockComposite`, the crop editor,
output-as-step) are VISION worked through; everything else began as a copy of
its `src/sieve/gui` counterpart and was reshaped from there.

## The deltas

| Surface | What is settled | Where |
|---|---|---|
| Source is a step | The video is chosen on the first card of the chain, not on a screen before it; a stage of one, never removable; the chooser lists the project's sources and browsing **appends** to them rather than replacing | `STAGES`, `_source_chooser`, `_remove_button` |
| Crop cuts regions, plural | One crop step owns a list of rects; the card holds the count and two mini-buttons, the four spin boxes edit whichever region is selected; adding a region selects it; a floor (`CROP_MIN`) keeps every rect grabbable | `CROPS`, `_crop_count`, `_crop_pair`, `add_crop` |
| The crop fan | The regions are numbered squares in the gap below the crop card, left-aligned on the trunk so every arrow is vertical; all arrows leave the one card that made them; the chain below is drawn for the selected square, and selecting a square is the same notification a drag sends | `_CropFan`, `_paint_fanned_edge`, `select_crop` |
| Arrow logic | An output leaves the bottom of its card and arrives at the top of its reader; a line crossing a non-reader passes **behind** that card (occlusion, not routing); every edge is vertical in its own lane; arrowheads always point down; ports are named only where a step has more than one input | the block comment above `_EDGE_STUB`, `_lanes`, `PORT_NAMES` |
| Output is a step | What leaves the chain is a card at the foot of it; the write list is that step's param, a ticked product **is** an edge into its card (its inputs are derived from the ticks), the edges are labeled by product, and Run sits on its form — the run/save screen is dissolved | `WRITES`, `refresh_output_inputs`, `_write_list`, `_run_row` |
| Settings is the right pane | Three sliding positions: project ⟷ pipeline ⟷ step. A card's → button selects that step and slides right; the step pane is caption card, generated form, guidance expander, in one scrolling column | `Control`, `_SlidingPanes`, `_settings_button`, `build_step_pane` |
| Swap is the same box | The ⇄ button opens the add box **over the card**, lit on the tool already there; the offering is keyed on the position's type signature, not declared by the tool standing there. No menu, no wizard, no dialog. Anchored — ↑/↓ have nothing to move, ←/→ still walk the offer. Taking one keeps the node's id, so its edges and the ticks naming it survive; its knobs and guidance do not, because they belonged to the tool that left | `_swap_button`, `offer_at`, `retool`, `Control.swap_here`, `RETOOLED` |
| Card verbs | Click selects (the same selection ↑/↓ moves); ◆ pins — one slot, pinning evicts; ✕ removes — the chain reads past the removed step (its readers inherit its inputs), and the walk and pin land on the step above; the project card opens on double-click | `ChainCard`, `_sources_of`, `Control.remove`, `_project_card` |
| Adding a step | ADD STEP on the project card opens a box in the chain — card-shaped, card-numbered, dashed on the edges it would be spliced onto, holding the offer for the gap it stands in. ↑/↓ move the box through the gaps and the offer rewrites with it, ←/→ walk the offer, enter takes it, esc closes. The gap under the output is not a position. What lands is spliced: the new step reads the gap's step and whatever read past the gap reads it. **The box never writes on opening** — it is a picker, which is what makes esc free, and one mutation is issued when an offer is taken | `_AddBox`, `_add_box`, `offer_after`, `add_node`, `Control.add_here`, `Control.fill_box`, `_ChainColumn.hold_box` |
| The pinned step | One step held under the canvas at full width, detection by default; the slot re-fits to what natural height the step asks for; its card in the stack says where the surface went; steps with no plots state their surface in words | `PinnedStep`, `MockWindow._fit_pin`, `NO_SURFACE_NOTE` |
| Project selector | The same stack surface as the pipeline — library card above, one `ChainCard` per project, selection accent, ↑/↓ move it, double-click enters. Not a platform list widget. The library card carries NEW PROJECT (mint an empty project, the selection lands on it without entering the pipeline) and the selected card alone carries OPEN LOCATION at its foot, both in the timeline button's dress | `build_project_pane`, `_project_card`, `_chrome_button`, `add_project`, `Control.new_project`, `_reveal_project` |
| Hotkeys | ←/→ move the position (project/pipeline/step), ↑/↓ move whichever selection the position owns, P pins the current step, A opens the box on the pipeline; the rail shows only on pipeline and step. An open box owns both pairs — ↑/↓ move it where it can move, ←/→ walk its offer, enter takes it, esc closes — because it is a position the walk cannot stand on | `MockWindow` shortcuts, `Control.go` |
| The scrubber | Dragging the window's body slides the whole window; the edge handles resize only while the HANDLES toggle beside the strip is armed; the divider band above the timeline is not draggable | `MockStrip`, `build_seam`, `build_timeline` |
| Chrome | Dark throughout, including the OS title bar; stage headers with `in -> out` chips; scrollbars stay the platform's | `_darken_title_bar`, `_stage_header`, `_stack_stylesheet` |

## What the mockup does not settle

- **The canvas contents.** The heat rings and the in-band grid are still
  indicative, and now for a stated reason: they read a mask no node emits, so
  the mockup draws a picture of a decision that has not been made
  ([todo/a-declared-surface-is-drawn-by-nothing.md](todo/a-declared-surface-is-drawn-by-nothing.md)
  carries it). The rest is no longer sample. The walk owns the surface and
  emission display generates per kind
  ([adr/the-walked-step-owns-the-canvas.md](adr/the-walked-step-owns-the-canvas.md)),
  the kind is `ElementKind`
  ([adr/an-outputs-kind-is-the-picture-it-makes.md](adr/an-outputs-kind-is-the-picture-it-makes.md)),
  and Phase 10 builds the composite, the magnifier and the solo gesture from
  the mockup as shape. The crop boxes were always the exception: a rect
  param's generated editor is settled
  ([adr/gui-knows-kinds-not-tools.md](adr/gui-knows-kinds-not-tools.md)).
- **The tool lists.** `NODES`, `STAGES`' membership, `SWAPPABLE`'s entries,
  the per-step knob sets and guidance strings are sample data. What is
  settled is the derivations they stand in for — the swap offering comes
  from the position's signature, the write list from what the chain can
  emit — and the open questions about those derivations stay open
  (`docs/todo/the-offering-predicate-is-not-the-edge-legality-check.md`).
- **What a filled position's form holds.** The box settles where a step goes
  and what is offered there; the card it becomes has no knobs, and neither does
  a card whose tool was swapped, because the mockup writes those per position
  and a tool that arrived at run time was never one of them. The real form is
  generated from the tool's params
  ([adr/gui-knows-kinds-not-tools.md](adr/gui-knows-kinds-not-tools.md)), so
  this is a mock limitation rather than a shape. That a swap drops the knobs at
  all is not: the id survives and the params do not, because they were the
  departed tool's.
- **An offer that is empty.** Every stage in `SWAPPABLE` has entries, so the
  referent never draws a position with nothing to stand in it. The tree's
  first case is the other one
  ([findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md](findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md)),
  and what a box with an empty offer says is not settled here.
- **The output step's file rows.** The `into` folder and the format combo
  on the output form arrived with no instruction behind them; the format
  choice in particular collides with `storage`'s one-format rule and will
  be worked over later. The settled part of the output card is the shape —
  write list as ticks, ticks as edges, Run on the form.
- **The mechanism.** Nothing here weakens VISION's flexibility claims: the
  command layer stays keyed by intent kind, editors stay generated per param
  kind, and a complete GUI is still any layout that emits every intent kind.
  The mockup fixes which layout v3 ships, not what a layout is made of.
- **Its own shortcuts.** Module globals stand in for the document, widgets
  compute their own data, and an added step is appended to `NODES` rather than
  inserted because every table here is keyed by position — mock limitations,
  none of them surface, all of them forbidden to the real `gui` by contracts
  that already exist.
