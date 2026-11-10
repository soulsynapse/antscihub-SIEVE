# Tool names under five conventions

A view, not a decision. Each column renames the whole catalogue under one convention that users of
the source tool praise; where a convention has no good answer the least-bad name is written so the
strain shows. Written 2026-11-09 against the tree at 4203efbc.

- **Blender** (geometry nodes, post-3.0): fixed verb families, `sample-*` reads the second input
  onto the first, `select-*` keeps by a field, `write-*`/`import-*` for files; measures are result
  nouns; conversions `a-to-b`; long names allowed.
- **Houdini** (SOPs): bare operation word; kind prefix only when the operation exists on more than
  one kind; `*-transfer` names what moves (Attribute Transfer's rule, second onto first);
  conversions `a-to-b`.
- **TouchDesigner**: one short operation word reused across kinds, every tool suffixed with the
  kind it processes, no exceptions; conversions `a-to-b`.
- **ImageJ / Fiji**: menu-command style, verb-noun naming the result the user wants (Subtract
  Background, Analyze Particles, Find Maxima); the algorithm never appears.
- **dplyr / scikit-image**: verb-first API grammar, short, one verb per operation class (`filter`,
  `select`, `mutate`, `summarise`; `label`, `regionprops`, `remove_small_objects`); the object is
  implied by the pipe.

| current | Blender | Houdini | TouchDesigner | ImageJ | dplyr / skimage |
|---|---|---|---|---|---|
| agreement | flow-agreement | flow-agreement | agreement-flow | measure-flow-agreement | agreement |
| attach | sample-marks | mark-transfer | attach-blobs | assign-marks | join-marks |
| background | background | background | background-frame | build-background | background |
| bake | bake | bake | bake-any | cache | cache |
| bg-subtract | subtract-background | bg-subtract | subtract-frame | subtract-background | subtract-background |
| blobs | mask-to-blobs | blobs | components-mask | analyze-particles | label |
| blobs-to-mask | blobs-to-mask | blobs-to-mask | blobs-to-mask | draw-particles | rasterize |
| changeenergy | change-energy | change-energy | changeenergy-gray | measure-change-energy | change-energy |
| coarsegrain | average-blocks | coarsegrain | coarsegrain-frame | bin | downsample |
| combine | combine-masks | mask-combine | combine-mask | image-calculator | logical |
| count | count-blobs | blobs-count | count-blobs | count-particles | count |
| crop | crop-to-mask | crop | crop-frame | crop-to-selection | crop |
| csv | write-csv | signal-csv | csv-signal | save-as-csv | write-csv |
| decode | read-aruco | aruco | aruco-blobs | read-aruco-tags | decode-aruco |
| file | import-video | file | file-path | open | open |
| filter | select-blobs-by-field | blobs-filter | filter-blobs | exclude-particles | filter |
| flow | optical-flow | flow | flow-gray | compute-optical-flow | optical-flow |
| gray | bgr-to-gray | bgr-to-gray | bgr-to-gray | convert-to-8-bit | rgb2gray |
| hsv | bgr-to-hsv | bgr-to-hsv | bgr-to-hsv | convert-to-hsv | rgb2hsv |
| inrange | select-color-range | hsv-threshold | threshold-hsv | color-threshold | threshold-color |
| inside | sample-region | region-transfer | inside-blobs | assign-region | join-region |
| kinematics | kinematics | kinematics | kinematics-tracks | measure-motion | mutate-kinematics |
| mask | apply-mask | mask-apply | mask-frame | clear-outside | apply-mask |
| morphology | open-close-mask | morphology | morphology-mask | open-close | opening-closing |
| motion | frame-difference | frame-difference | difference-gray | subtract-previous-frame | frame-difference |
| reduce | plane-statistic | plane-reduce | reduce-frame | measure | summarise |
| region | import-regions | region | region-frame | load-rois | read-regions |
| rescale | scale-frame | rescale | rescale-frame | scale | rescale |
| resolve | resolve-identity | resolve | resolve-tracks | assign-identity | resolve-identity |
| sample | sample-plane | plane-sample | sample-blobs | measure-intensity | regionprops |
| size | blob-size | blobs-size | size-blobs | measure-size | summarise-size |
| smooth | smooth-signal | smooth | smooth-signal | smooth | smooth |
| spacing | blob-spacing | blobs-spacing | spacing-blobs | measure-spacing | summarise-spacing |
| speed | flow-speed | flow-speed | speed-flow | measure-speed | flow-magnitude |
| threshold | threshold | gray-threshold | threshold-gray | threshold | threshold |
| track | blobs-to-tracks | track | track-blobs | track-particles | link |
| tracks-csv | write-tracks-csv | tracks-csv | csv-tracks | save-tracks-as-csv | write-tracks-csv |
| tracks-filter | select-tracks-by-property | tracks-filter | filter-tracks | exclude-tracks | filter-tracks |
| transitions | transitions | transitions | transitions-tracks | count-transitions | transitions |
| travel | travel | travel | travel-tracks | measure-travel | summarise-travel |

What each column buys and what it costs, read down the table:

- Blender is the only column that fixes the direction of a two-table tool structurally: attach,
  inside and sample become the `sample-` family, second input written onto the first. It is the
  longest and splits into verb-noun operations beside noun measures.
- Houdini changes the least and is the convention the repo half-follows already (`tracks-filter`,
  `tracks-csv`, `blobs-to-mask`); `filter`/`csv` get the prefix their tracks twins have, and
  `inrange`/`threshold` become the pair they are. The `*-transfer` family is imported, not given.
- TouchDesigner is the most scannable and makes the Tab filter line a type filter; every name
  changes, the suffix repeats the wire, and direction stays unsaid.
- ImageJ reads best to a biologist and worst to a graph: every name is a command, so a chain of
  them reads as a macro, and several (`image-calculator`, `measure`) are ImageJ's actual words
  carrying its baggage.
- dplyr/skimage is the shortest and the most familiar to anyone who has written analysis code, and
  it makes `filter` the right word rather than the wrong one; it leans on the wire to say the
  object, exactly as the pipe does, so it is the convention that most assumes the display pass.
