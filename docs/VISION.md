# VISION v3

The reason for v3 is to make the repo easy to grow. v2 works, and works well, but the way the code is structured, it is faster to do the refactoring here.

The ideal case: v2's evidence decides what comes over, one decision at a time, with the boundaries enforced from the first commit and the missing pieces integrated from the start. A boundary that held ports; one that needed propping gets re-derived; and a v2 decision transfers only where no ADR here overrides it — several already do (the kernel apparatus, the detect package, the importer). The port is asymmetric on that evidence: the non-GUI half held; the GUI half didn't ([PLAN.md](PLAN.md)).

## The loop

SIEVE turns video into behavioral measurements using interpretable signal-processing tools. The user builds a pipeline; SIEVE runs it. Its value is the speed of the tuning loop: drag a slider, watch the graphs refill faster than the video plays. Architecture that does not serve that loop does not belong. Two settled rules guard it: preview and production are one execution path, so what you tuned against is what the run produces ([adr/one-execution-path.md](adr/one-execution-path.md)), and the naive path is the product surface — every tool runs correct-but-slow on any machine, and fast paths land only on a measured budget violation ([adr/correctness-is-the-default.md](adr/correctness-is-the-default.md)). The numbers are below, enforced from `bench/budgets.py`, and measured headless before a single widget exists.

## Two speed regimes

Both are load-bearing and improving one at the cost of the other is a defect. Pre-pipeline runs from opening a video to having replicates cut and a stretch selected; the intended feel is a video editor. In-pipeline runs from dragging a slider to seeing the graph update; the intended feel is direct manipulation, not job submission.

```
PRE-PIPELINE (feels like a video editor)
  Open file → first frame:        < 500 ms
  Scrub/seek → frame repaint:     < 100 ms
  Scrub release → exact frame:    < 250 ms
  Cut confirmed → ready:          < 200 ms

IN-PIPELINE (feels like direct manipulation)
  First tool → first graph tick:  < 2 s
  Slider drag → preview repaint:   < 100 ms
  Slider drag → graph update:      < 200 ms
  Full preview render (5–10s clip): < 3 s
  Band drag → graphs repaint:      < 50 ms
  Band power arrives → density rebuilt: < 100 ms
  Knob settle → graphs rebuilt:    < 3 s
  Knob settle → graphs start filling: < 500 ms
```

Every limit is anchored to a perceptual response band rather than to a measurement — ~100 ms reads as instantaneous, ~1 s holds the flow of thought, ~10 s holds attention (Card, Moran & Newell). `bench/budgets.py` carries the anchor for each row, and `tests/bench/test_budget_table.py` parses this block and fails if the two ever disagree, so neither side can be edited alone. A budget anchored to perception outlives the hardware that first met it; one anchored to what was achieved once is history wearing a rule's costume.

**Scope: these ceilings are promised for the reference workload** — the stirred clip through the chain the preview session runs, not any graph a user can construct. That is how a service-level objective is stated everywhere it works: a promise conditioned on a workload, not a wish about all workloads. Outside the scope, what survives is the honesty half — input never blocks, progress is visible, and a stale frame is labeled stale. A miss inside the scope is a defect, or a debt declared in `budgets.IN_DEBT` against the `docs/todo/` item that repays it; widening the scope is a decision about the product, made here, not conceded one alarm at a time.

## Features, and why I want them:

1. Tool *contracts*. If cropping is a 'contract' from day 1, then the hand off that it needs (ability to draw boxes on a canvas, stamp tool, etc) can fairly easily live on a separate tab, *or* live as a tool item itself on the 2nd tab. The settled shape: a drawn overlay is an editor bound to a param field, entering the same command path as a typed value ([adr/gui-knows-kinds-not-tools.md](adr/gui-knows-kinds-not-tools.md)).
2. Stereotyped GUI features. Tools say how they're populated, mostly. This makes tool build out much faster. Same ADR: widgets and overlays generate per param kind, never per tool — kinds grow slowly and deliberately, tools grow fast and for free, and that asymmetry is the design.
3. Way less bloat from comments and docstrings. This alone was like 50% of the repo last time. The mechanism, so it doesn't regress silently: the contract lives in the module docstring, the reasoning lives in the ADR it cites, and nothing else earns prose (CLAUDE.md holds the comment test).
4. Adding a new tool should take a few hours whether it is the 5th tool or the 50th tool. The checkable form: a tool is one module in `sieve.tools` and zero edits anywhere else, and a tool that needs a second file is an architecture failure to stop and fix ([adr/a-tool-is-one-file.md](adr/a-tool-is-one-file.md)).
5. Detect is resolved: crop, span, and the detector are graph nodes natively ([adr/detector-is-a-node.md](adr/detector-is-a-node.md)), on the declared-lookahead contract the v2 window lacked.

The end result is that tools are most of the customization surface: if you design what is in the tool folder right, it should work with SIEVE. It declares what it wants, and what it can emit, etc. It should be intuitive for users to wire things up.

Done correctly, I will be able to rework the GUI in an afternoon with the help of Claude. All the mappings and dependencies should be non-confusing and clear.

## Components, and what each must never own

The never-lines are the forbidden edge set. None of them is enforced by this table: each is an import contract (`docs/todo/the-import-contracts-bind-before-any-code.md`) or an ADR gate, and the layer order gives every package its first never for free — nothing imports upward.

The **bold** spans in "Owns" are the enumeration inside the prose, and each one is a phrase the package's `__init__.py` first line has to say — checked, since that line is where a reader arrives and the SCAFFOLD annotation it feeds could only ever prove it was copied faithfully.

| Package | Owns | Never |
|---|---|---|
| `core` | the **dimensioned types**, the **tool contract and registry**, **schema v1**, **`ops/`** — membership closed ([adr/core-membership-is-closed.md](adr/core-membership-is-closed.md)), and `ops/` waits for its second caller ([adr/ops-admission-is-two-tools.md](adr/ops-admission-is-two-tools.md)) | Qt, cv2, codecs, processes (`core-purity`); a v2 field name; a new child without revising the ADR |
| `tools` | **every pipeline step**, **one module each** ([adr/a-tool-is-one-file.md](adr/a-tool-is-one-file.md)); the one place outside `decode` where cv2 is legal | a second file per tool; reaching the runtime — `run` is a plain function handed its inputs |
| `pipeline` | **the DAG**, **the plan**, **cache keys**, **the one executor** | a `tool_id` branch ([adr/no-kernel-apparatus.md](adr/no-kernel-apparatus.md)); reaching into `ops/`; Qt (`headless`) |
| `decode` | **the codec boundary** — **lowering into ffmpeg**, **prefetch**, **decoder identity**; v2 verbatim | Qt; knowing what a tool or a schema is |
| `cli` | **the headless front end**; with the saved file it is **the cluster handoff** | Qt (`headless`); cv2 — a frame is reached through `decode`, never by a second seek strategy |
| `gui` | **rendering values**, **emitting intents**, **holding view state** | computing anything — the `gui-computes-nothing` exception list is empty from commit one; a `tool_id` branch ([adr/gui-knows-kinds-not-tools.md](adr/gui-knows-kinds-not-tools.md)); cv2 |
| `bench` | **the budget table** and **the metric bus** — the loop's claims as numbers | Qt; sitting in the execution path it measures |
| `storage` | **sink writers** (`crop_writer`, `checkpoint_writer`) | a second output format before someone asks ([PLAN.md](PLAN.md), revival table) |

## Vision

Five users, end to end.

The ideal scenario is pretty close to v2.5's gui split up, complete with hotkeys. User lands and they are met with the project pane. They hit right, and it takes them into the project, at a pipeline view level. The pipeline view level has v2's modularity, but you can press up and down to go between them, and pressing right lets you move between replicates.

When a person sits down, they're at the project screen. Their old projects are there, and they can see a list, and when they click an item, it shows them project stats that they're interested in.

They go into the project folder and they see replicates is the first pipeline item. They can see how it's all split; with 6 replicates, they have to pick one to go into, pressing right or just clicking from the replicate thing. They can hit a down expander arrow that will show them all the help text they need and they can scroll it if they want; this is the wizard, reimagined.

To the left is the canvas, and below it is one pinned pipeline step. It's the detection tools by default (making a shape similar to the v2) but the user can select anything to pin there. The bottom area is the scrubber from v2, just much taller. It shows the selected signal that was cached, like how v1 did it, so if the user scrubs the footage or does a full length detection, it'll give them the detection information for that run.

The user then scrolls down a bit. The outputs from each step reach downwards; the step that generated the background skips over the step for color thresholding, passing behind it, and then the color thresholding and background both make it to a background subtraction step, which ingests both items. That is elegantly shown with the lines drawn downwards to the background subtraction. (Two inputs into one step is the merging shape v2 designed for and never built; it lands as the contract-plus-executor extension ADR-2 anticipated — `window` grows a port-keyed form — not as something a tool improvises.) The user checks off the outputs they want persisted from the background subtraction, and selects 'process', which gives them an overview of the steps and an estimate of the time it'll take on this machine — the estimate is the consumer that finally revives the spec's cost declarations, which arrive with this screen and not before ([adr/declared-means-verified.md](adr/declared-means-verified.md)). They can run it here, or take the project to a cluster: the saved file plus `sieve run` is the HPC handoff — the same artifact executed headless, which the `headless` contract exists to keep true. Job templates and chunking across nodes wait on a real cluster target ([PLAN.md](PLAN.md), revival table).

Another user finds SIEVE and wonders if it can help them determine if a project will work. They download it and see it doesn't have the optical flow settings they need; they want to use a special version. Looking at the tool contract, they use an agent to put together a tool that accepts the outputs of pre-existing tools and processes and outputs exactly what they were looking for. It takes them about an hour, and it touches one file ([adr/a-tool-is-one-file.md](adr/a-tool-is-one-file.md)).

A reviewer looks at SIEVE as part of their evaluation of a manuscript. They load the video file and the project file, and have SIEVE run. It outputs the same results. Where necessary, the author had selected "deterministic run", and because that choice changes outputs it is a param and was saved to the file ([adr/param-not-preference.md](adr/param-not-preference.md)). When they save, they see a list of *all the possible* outputs the tools could emit — declared on the specs, so the list cannot lie — and they check a few extra ones for fun, but ultimately recommend the paper for acceptance without much fanfare.

In six months, I realize that I'm getting a lot of feedback that the UI really doesn't work for people. I open the app, and because the mappings are clean, I can reshuffle things into mock ups to see which works best pretty easily. It isn't too much work, because there is a list of required bindings for the app to be equally operational — the intent kinds the command layer is keyed by ([PLAN.md](PLAN.md), Phase 7) are that list, and any layout that emits them all is a complete GUI.

Another user opens SIEVE. They are trying a background subtraction isolation method but they have three different generated backgrounds and they want to know which one does better. Two of them are two different background subtraction settings. They add both to the pipeline, making two outputs. The downstream step for the actual subtraction asks them to select which input they want to use - they click to add a local one, and it lets them. there are 3 options to select from, at the top of the tool step; two have lines that are reaching down from previous steps that show where they came from. The third has a little dot above it, like a line that trails off into the background. They're represented as 3 buttons, and the active one is highlighted. They swap between them and scrub around the footage to see how it does.

## What binds where

This document owns the target: the loop, the edge set, and the claims above. Settled decisions are ADRs, indexed in [ARCHITECTURE.md](ARCHITECTURE.md); sequence and port dispositions are [PLAN.md](PLAN.md); measurements are `docs/findings/`. v2.5's DESIGN-SESSION is an archive, not a source: its surviving invariants were minted as ADRs 7–12, and its op algebra is dissolved ([adr/no-kernel-apparatus.md](adr/no-kernel-apparatus.md)).
