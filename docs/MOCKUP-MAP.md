# What the mockup settles

`mockup/mockup.py` is the settled v3 surface
([adr/the-mockup-is-the-gui-end-state.md](adr/the-mockup-is-the-gui-end-state.md)).
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
| Swap is a dropdown | The ⇄ button on the card opens a menu of what could stand at this position; the offering is keyed on the position's type signature, not declared by the tool standing there. No wizard, no dialog | `_swap_button`, `SWAPPABLE` |
| Card verbs | Click selects (the same selection ↑/↓ moves); ◆ pins — one slot, pinning evicts; ✕ removes — the chain reads past the removed step (its readers inherit its inputs), and the walk and pin land on the step above; the project card opens on double-click | `ChainCard`, `_sources_of`, `Control.remove`, `_project_card` |
| The pinned step | One step held under the canvas at full width, detection by default; the slot re-fits to what natural height the step asks for; its card in the stack says where the surface went; steps with no plots state their surface in words | `PinnedStep`, `MockWindow._fit_pin`, `NO_SURFACE_NOTE` |
| Project selector | The same stack surface as the pipeline — library card above, one `ChainCard` per project, selection accent, ↑/↓ move it, double-click enters. Not a platform list widget. The library card carries NEW PROJECT (mint an empty project, the selection lands on it without entering the pipeline) and the selected card alone carries OPEN LOCATION at its foot, both in the timeline button's dress | `build_project_pane`, `_project_card`, `_chrome_button`, `add_project`, `Control.new_project`, `_reveal_project` |
| Hotkeys | ←/→ move the position (project/pipeline/step), ↑/↓ move whichever selection the position owns, P pins the current step; the rail shows only on pipeline and step | `MockWindow` shortcuts, `Control.go` |
| The scrubber | Dragging the window's body slides the whole window; the edge handles resize only while the HANDLES toggle beside the strip is armed; the divider band above the timeline is not draggable | `MockStrip`, `build_seam`, `build_timeline` |
| Chrome | Dark throughout, including the OS title bar; stage headers with `in -> out` chips; scrollbars stay the platform's | `_darken_title_bar`, `_stage_header`, `_stack_stylesheet` |

## What the mockup does not settle

- **The canvas contents.** The magnifier, the block-grid overlay, the solo
  gesture, the heat rings — indicative, not final. Who owns the surface is
  no longer open: the walk does, and emission display generates per kind
  ([adr/the-walked-step-owns-the-canvas.md](adr/the-walked-step-owns-the-canvas.md))
  — but the kind vocabulary waits for its first consumer. The crop boxes
  are the exception: a rect param's generated editor is settled
  ([adr/gui-knows-kinds-not-tools.md](adr/gui-knows-kinds-not-tools.md)).
- **The tool lists.** `NODES`, `STAGES`' membership, `SWAPPABLE`'s entries,
  the per-step knob sets and guidance strings are sample data. What is
  settled is the derivations they stand in for — the swap offering comes
  from the position's signature, the write list from what the chain can
  emit — and the open questions about those derivations stay open
  (`docs/todo/the-offering-predicate-is-not-the-edge-legality-check.md`).
- **Adding a tool.** The mockup has no affordance for it — a deliberate
  gap, not a settlement, and the one place ADR 22's popup default does not
  apply. VISION's add-tool box (the new-project scenario) is the binding
  wording: a box below the last step holding what could go there, the offer
  derived from what the source resolved to. What an offer is keyed on stays
  open (`docs/todo/the-offering-predicate-is-not-the-edge-legality-check.md`).
- **The output step's file rows.** The `into` folder and the format combo
  on the output form arrived with no instruction behind them; the format
  choice in particular collides with `storage`'s one-format rule and will
  be worked over later. The settled part of the output card is the shape —
  write list as ticks, ticks as edges, Run on the form.
- **The mechanism.** Nothing here weakens VISION's flexibility claims: the
  command layer stays keyed by intent kind, editors stay generated per param
  kind, and a complete GUI is still any layout that emits every intent kind.
  The mockup fixes which layout v3 ships, not what a layout is made of.
- **Its own shortcuts.** The swap menu does not rebuild the card (knobs are
  keyed by position), module globals stand in for the document, widgets
  compute their own data — mock limitations, none of them surface, all of
  them forbidden to the real `gui` by contracts that already exist.
