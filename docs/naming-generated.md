# Tool names derived from the contract

DRAFT / WIP, a view and not a decision. Generated 2026-11-09 against the tree at e17fe0fc by
docs/findings/experiments/2026-11-09-tool-naming-table.py from the registry's facets; rerun it
rather than edit the table. The grammar is Kendrick's sketch in docs/spec/tool-naming.md,
`type-[and-type]-family-operation-to-type`, with types named at the class where a tool takes several
(`plane` over bgr, gray, hsv, mask, flow; `table` over blobs, tracks; `any` for all). Family is the
one facet no tool declares and is assigned by hand in the script; the `trimmed` column drops what the
family implies (a transform produces `same`, a measure produces `signal`, a convert's operation is
its output). The strain column is the class word overstating the declared union, or the grammar
having no form for the tool.
| current | contract | family | literal grammar | trimmed | strain |
|---|---|---|---|---|---|
| agreement | `flow -> gray` | convert | `flow-convert-agreement-to-gray` | `flow-agreement-to-gray` |  |
| attach | `blobs + marks:blobs -> blobs` | transfer | `blobs-and-blobs-transfer-attach-to-blobs` | `blobs-and-blobs-transfer-attach` |  |
| background | `bgr/gray/mask -> same` | transform | `plane-transform-background-to-same` | `plane-background` | plane minus flow/hsv |
| bake | `bgr/blobs/flow/gray/hsv/mask/signal/tracks -> same` | cache | `bgr-or-blobs-or-flow-or-gray-or-hsv-or-mask-or-signal-or-tracks-cache-bake-to-same` | `bgr-or-blobs-or-flow-or-gray-or-hsv-or-mask-or-signal-or-tracks-cache-bake` | spans classes |
| bg-subtract | `bgr/gray + bg:('gray', 'bgr') -> gray` | transform | `plane-and-plane-transform-subtract-to-gray` | `plane-and-plane-transform-subtract-to-gray` | plane minus flow/hsv/mask |
| blobs | `gray/mask + diff:gray -> blobs` | convert | `plane-and-gray-convert-blobs-to-blobs` | `plane-and-gray-to-blobs` | plane minus bgr/flow/hsv |
| blobs-to-mask | `blobs -> mask` | convert | `blobs-convert-paint-to-mask` | `blobs-paint-to-mask` |  |
| changeenergy | `gray/mask -> gray` | transform | `plane-transform-changeenergy-to-gray` | `plane-transform-changeenergy-to-gray` | plane minus bgr/flow/hsv |
| coarsegrain | `flow/gray/mask -> same` | transform | `plane-transform-coarsegrain-to-same` | `plane-coarsegrain` | plane minus bgr/hsv |
| combine | `mask + with:mask -> mask` | transform | `mask-and-mask-transform-combine-to-mask` | `mask-and-mask-combine` |  |
| count | `blobs -> signal` | measure | `blobs-measure-count-to-signal` | `blobs-measure-count` |  |
| crop | `bgr/flow/gray/hsv/mask + roi:mask -> same` | transform | `plane-and-mask-transform-crop-to-same` | `plane-and-mask-crop` |  |
| csv | `signal -> signal` | sink | `signal-sink-csv-to-signal` | `signal-sink-csv` |  |
| decode | `blobs + plane:('bgr', 'gray') -> blobs` | transfer | `blobs-and-plane-transfer-decode-to-blobs` | `blobs-and-plane-transfer-decode` |  |
| file | `- -> path` | source | `none-source-file-to-path` | `none-source-file-to-path` |  |
| filter | `blobs -> blobs` | select | `blobs-select-filter-to-blobs` | `blobs-select-filter` |  |
| flow | `gray/mask -> flow` | convert | `plane-convert-flow-to-flow` | `plane-to-flow` | plane minus bgr/flow/hsv |
| gray | `bgr -> gray` | convert | `bgr-convert-gray-to-gray` | `bgr-to-gray` |  |
| hsv | `bgr -> hsv` | convert | `bgr-convert-hsv-to-hsv` | `bgr-to-hsv` |  |
| inrange | `bgr/hsv + settings:path -> mask` | convert | `plane-and-path-convert-inrange-to-mask` | `plane-and-path-inrange-to-mask` | plane minus flow/gray/mask |
| inside | `blobs + regions:blobs -> blobs` | transfer | `blobs-and-blobs-transfer-inside-to-blobs` | `blobs-and-blobs-transfer-inside` |  |
| kinematics | `tracks -> tracks` | transfer | `tracks-transfer-kinematics-to-tracks` | `tracks-transfer-kinematics` |  |
| mask | `bgr/flow/gray/hsv/mask + mask:mask -> same` | transform | `plane-and-mask-transform-mask-to-same` | `plane-and-mask-mask` |  |
| morphology | `mask -> mask` | transform | `mask-transform-morphology-to-mask` | `mask-morphology` |  |
| motion | `gray/mask -> gray` | transform | `plane-transform-motion-to-gray` | `plane-transform-motion-to-gray` | plane minus bgr/flow/hsv |
| reduce | `gray/mask -> signal` | measure | `plane-measure-reduce-to-signal` | `plane-measure-reduce` | plane minus bgr/flow/hsv |
| region | `bgr/flow/gray/hsv/mask + geometry:path -> blobs` | source | `plane-and-path-source-region-to-blobs` | `plane-and-path-source-region-to-blobs` |  |
| rescale | `bgr/gray/mask -> same` | transform | `plane-transform-rescale-to-same` | `plane-rescale` | plane minus flow/hsv |
| resolve | `tracks + labels:path -> tracks` | transfer | `tracks-and-path-transfer-resolve-to-tracks` | `tracks-and-path-transfer-resolve` |  |
| sample | `blobs + plane:('gray', 'mask') -> blobs` | transfer | `blobs-and-plane-transfer-sample-to-blobs` | `blobs-and-plane-transfer-sample` |  |
| size | `blobs -> signal` | measure | `blobs-measure-size-to-signal` | `blobs-measure-size` |  |
| smooth | `signal -> signal` | transform | `signal-transform-smooth-to-signal` | `signal-smooth` |  |
| spacing | `blobs -> signal` | measure | `blobs-measure-spacing-to-signal` | `blobs-measure-spacing` |  |
| speed | `flow -> gray` | convert | `flow-convert-speed-to-gray` | `flow-speed-to-gray` |  |
| threshold | `gray -> mask` | convert | `gray-convert-threshold-to-mask` | `gray-threshold-to-mask` |  |
| track | `blobs -> tracks` | convert | `blobs-convert-track-to-tracks` | `blobs-track-to-tracks` |  |
| tracks-csv | `tracks -> tracks` | sink | `tracks-sink-csv-to-tracks` | `tracks-sink-csv` |  |
| tracks-filter | `tracks -> tracks` | select | `tracks-select-filter-to-tracks` | `tracks-select-filter` |  |
| transitions | `tracks -> signal` | measure | `tracks-measure-transitions-to-signal` | `tracks-measure-transitions` |  |
| travel | `tracks -> signal` | measure | `tracks-measure-travel-to-signal` | `tracks-measure-travel` |  |

What the table shows, read down the strain column: ten tools take a subset of `plane`. Four are
principled, single-channel operations (`motion`, `changeenergy`, `reduce`, `flow` on gray and mask);
the rest look arbitrary and are the soft refusals the grammar was meant to surface: `rescale` and
`background` without hsv, `coarsegrain` without bgr and hsv, `bg-subtract` without mask. `bake`
spans every class but path, so `any` wants to be "any wire" and not "any type". `file` has no head
and `csv`/`tracks-csv` are sinks that produce, so sources and pass-through sinks need their own
forms. `filter`/`tracks-filter`, `threshold`/`inrange` and the three `blobs-and-*-transfer-*` tools
become visible siblings. Every single-input measure and transform gets longer with no information
the current name lacked beyond the family word.