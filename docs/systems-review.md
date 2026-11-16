# Systems review

Built a part a session by `docs/spec/systems-review.md`, which says what each part holds and the
order they are written in; a part not yet here is not yet written. The evidence it argues from is
`docs/findings/2026-11-16-what-came-back.md`, cited by class as F01 to F25. A figure here is of the
tree and the log at 2026-11-16, on v5-systems-review at `69903324`.

## 1. What SIEVE wants to be, and the pressures it is and is not under

### The aim

SIEVE finds when and where in a video something happens, by a chain of small scripts tuned under
one player. Its name is Signal Isolation of Ethological Video Events, and the README's first
sentence says how: it "runs independent video-analysis scripts as nodes in one graph, under one
shared player, so no script needs a GUI of its own" (`README.md`). The isolating is done by a band:
every node that hands out a plane or a signal carries two handles, the player zeroes what lies
outside them before anything downstream reads the node, and on a signal the rows inside are the
gate (`README.md`, the facets table; `sieve_player/graph.py:gated`).

One person uses it, Kendrick, who is also its one author of record: the 398 commits of v5 that are
no merge are all his (`git log v5 --no-merges --format=%an`).
The footage is his own, of ants, and what `video-tests/` holds is what the program has been built
against: 96 minutes of 1080p at 60 fps, 345,595 frames, one of four files of one experiment
(`Thermal hysteresis 4 days/`); 10.6 minutes of 1080p AVCHD whose seeks do not land where asked
(`00000.MTS`, F07); 7.9 minutes of 5312x2988 HEVC (`GX010047c2_02_17_26.MP4`); and smaller clips,
down to 234x304. The figures are ffprobe's.

A session of work produces a document and what the document wrote. Three of the nine documents
under `video-tests/`, read as JSON, chain `top-hat, threshold, detect, track, travel, smooth,
count, size` over a `region` chosen by a `file` selector, or `reduce, smooth, changeenergy,
coarsegrain` over a cut clip, and four of the nine hold a `csv` node. Beside a document lies its
held series, `<document>.series`
(`sieve_player/held.py`), 52 MB for the 96-minute file. In the folder lie csv files named by the
rows they cover (`00000_24841-26638.csv`, `tools/csv.py`), folders of clips a region cut
(`tools/_cutfile.py`), and geometry files drawn in `utilities/geometry`. So the work is: draw where,
tune a chain on a window of rows until the band keeps what is wanted, walk it over the clip, write
a table. The worker's ladder is that order, a scrub, the window walk, the clip walk
(`sieve_player/worker.py`).

What it has declined to be, each by a decision the tree or the log records:

- A tool with a window of its own, or a wide one. "Chains get longer; tools do not get wider"
  (`README.md`); the 38 tools under `tools/` have a median of 54.5 lines.
- A player that knows a tool. It learns every tool from the attributes the tool declares, and the
  registry "never rejects one" (`sieve_player/registry/README.md`).
- A program whose results depend on what a cache holds. Bake was retired whole (`07dd9830`), and a
  cut file is served only as the footage it is: "a document's results never depend on what the
  store holds" (`README.md`, `cut_file`).
- A learner. `pyproject.toml` depends on PySide6, OpenCV, av, numpy and psutil, and nothing that
  trains or runs a model; every tool is classical image processing.
- A tracker that holds identity through a pile. A day of linker variants was dropped for want of
  ground truth to judge them by (`4d8f513e`), and a session's note of 2026-11-01 has Kendrick wanting
  the loose ants where they cross and not the ids inside the cluster. That is his word at second
  hand.
- A race with TRex. `v5-runs`, which measured SIEVE against a port of it and added a decoder that
  reads ahead, is parked two commits off v5 and unmerged (`c0b417f4`).

### The pressures

| pressure | SIEVE | evidence |
| --- | --- | --- |
| Users who are not the author | is not under | One author in the log. No installer: the README opens on a venv and the commands to run from it. |
| Authors of tools who have not read the player | is under, by an unusual road | No tool lies outside `tools/`, though `discover(*roots)` takes any folder. But 390 of the 398 commits carry `Co-Authored-By: Claude` (`git log v5 --no-merges --format=%b`), and a session arrives having read nothing. The registry's `hint(facet)`, a broken tool shown as an `Entry` with its error, and `WIDGET_FACETS` held by a test answer that author. F17 is its class: in the ledger's words of `997700a3`, what the pane looks for on a widget "was found by hasattr at ten sites and written nowhere". |
| Saved documents that must still open | is under, at a small count | `document.VERSION` is 3 in thirty-six days, with `_lift_bakes` and `_lift_cuts` for two tools since removed. F12, 16 commits, 11 of them coming back. Nine documents lie under `video-tests/`; the cost of each further format change grows with that count and with the held files and stores beside them (the ledger, of `391bddd9`: "a held file made before this is found by nothing"). |
| The length and size of footage | is under | 345,595 rows in one file and 15.9 megapixels a frame in another. `walk.STACK_BYTES`, `SIEVE_MEMO_GB`, `SIEVE_CACHE_GB`. F06 (`75212615`: 256 rows of 5K BGR was 12 GB), F08, F23, and the findings named for a cost (`what-the-poll-costs`, `what-the-trace-costs`, `what-the-held-file-costs` and their like). |
| The count of files in a study | is headed for | The experiment's folder holds four videos and one document. `tools/file.py` picks one file by rule; nothing runs a document over each. Kendrick named running a pipeline over pieces of footage as the largest thing missing (2026-11-14, as the ledger records it). `sieve_player/bare.py` walks one clip in a process of its own, started by the window. |
| Who writes the code | is under, and no reference is | Sessions that end, several at once on some days, write nearly all of it and run the player on screen for little of it: the ledger counts 59 commits that say something was not run. F13, prose the code had left behind, 36 commits; F14, specs rewritten, 30; F24, two sessions' work in one commit; F25. |
| More than one machine or platform | is not under | Windows throughout: the README's commands, and F18's refusals to replace an open file (`a603747b`). |

The second and sixth rows are one fact read twice, and it is the reading here most open to
dispute: that a session without memory stands to the player as a third-party author stands to
Houdini, so that a declared, checked surface for tools answers a pressure SIEVE is under although
it has one author. The rows a reference is under and SIEVE is not are the first and the last.

### Among its neighbours

| program | evaluation | first | on a wire | unit of work |
| --- | --- | --- | --- | --- |
| Houdini | Pull: "Nodes are never cooked unless they are asked for their data", and the asker is "some UI element (such as the viewport) that observes the nodes whose display flag are enabled" [1] | Interactive; TOPs then run a network over many files, "Creates work items based on files that match a certain pattern" [2] | Geometry with attributes (m) | The `.hip` file, and paths relative to it (m; `tools/file.py` cites `$HIP`) |
| Blender | Push of what changed, then evaluation of what depends on it and is seen: "the dependency graph only updates what was dependent on the modified value", "avoid updates of invisible objects" [3] | Interactive; a background render from the command line (m) | Datablocks, each evaluated on a copy [3] | The `.blend` file (m) |
| Nuke | Pull: "This is known as a 'pull' system", by the scan-line, "the fundamental unit for image processing" [4] | Interactive; a script renders without the interface (m) | Rows of an image's channels [4] | The script (m) |
| Raven Pro | No graph: views of one sound, each computed from it (m) | Interactive; a detector "rapidly scan[s] recordings to automatically create selections" [5], and its batch form writes a table a file (the 1.4 manual's chapter 10, as a search summarised it, not fetched) | Nothing is wired. What passes between steps is the selection table, "saved as text files" [5] | The sound and its selection tables; a workspace "saves all information about Raven's state" [5] |
| Bonsai | Push: an observable is "a sequence of elements ordered in time", and a connection means "the downstream operator ... subscribes, or 'listens', to the notifications" [6] | Live acquisition (m) | Any element, frames and values measured of them alike (m) | The workflow file (m) |
| SLEAP | No graph: label, train, infer, in that order (m) | Both, as two programs: `sleap-label` "runs the GUI application for labeling and viewing `.slp` files", `sleap-track` is "the command-line interface for running inference" [7] | Nothing is wired; the `.slp` file passes between steps [7] | The `.slp` project |
| ImageJ | No graph: a command acts on the image in front (m) | Interactive, then recorded: "The macro recorder is an excellent way to generate macro code", and Process > Batch > Macro takes "an input and output directory" [8] | Nothing is wired; the image and the results table (m) | An image; for a study, a macro and a folder [8] |
| VapourSynth | Pull, by the frame: a filter called with `arInitial` "should request the input frames it needs and return NULL", and returns its frame "only ... when called with activationReason arAllFramesReady" [9] | Batch: "a core library written in C++ and a Python module to allow video scripts to be created" [10]; no interface of its own (m) | Frames, with "additional metadata ... attached to frames" [10] | The script (m) |
| SIEVE | Both. A frame node is pulled by row and memoized under a key of its params and its upstream (`sieve_player/graph.py`); a walk then pushes each row of a range through the series chain (`sieve_player/walk.py`) | Interactive. `--plan` and `smoke.py` run without the window; no command walks a document over a file | Both: planes (`bgr`, `gray`, `hsv`, `mask`, `flow`), tables a row (`blobs`, `tracks`), a `signal` a range, and a `path` (`python -m sieve_player.registry`) | A document, JSON, on one video, with its held series beside it and its cut files in a store |

(m) is from memory and was not fetched. [1] sidefx.com/docs/hdk/_h_d_k__op_basics__overview__cooking.html
[2] sidefx.com/docs/houdini/tops/cooking.html [3] developer.blender.org/docs/features/core/depsgraph
[4] learn.foundry.com/nuke/developers/150/ndkdevguide/2d/architecture.html
[5] ravensoundsoftware.com/software/raven-pro [6] bonsai-rx.org/docs/articles/observables.html
[7] legacy.sleap.ai/guides/cli.html [8] imagej.net/scripting/batch
[9] vapoursynth.com/doc/api/vapoursynth4.h.html [10] vapoursynth.com/doc/introduction.html. Each was
fetched on 2026-11-16 and read through a summarising fetch, so a quotation is as that reader gave it.

Three things the table says. SIEVE is the only row with both evaluations; that the classes of the
walk and the thread that drives it (F02, F03, F21) lie where the two meet is this session's
reading, and part 4 is where it is checked. On the wire it stands with Bonsai, frames and what is
measured of them in one graph, and apart from Houdini, Nuke and VapourSynth, each of which carries
one kind. And in what it is for it stands nearest Raven, a band over a signal that leaves a table
of where things were, while Houdini, Raven, SLEAP and ImageJ each have a second form that runs
over many files, and SIEVE has none.

### Where it is headed

Direction, none of it in the tree.

- A pipeline run over pieces of footage, replicates cut in space and bouts cut in time, and the
  results brought back to the footage: Kendrick, 2026-11-14, "Periods to bouts follows regions to
  crop", as the ledger and a session's note record it. The spatial half has begun: a region serves
  the clip it cut (`README.md`, `cut_file`; `07dd9830`).
- From one file to the files of an experiment. No commit says it; it is read from the four videos
  beside one document, and is this session's inference.
- Identity over finished tracks: `tools/resolve.py` is in the tree since `57b02e09` and in none of
  the nine documents.
- Names. A pass over the tools' and the regions' names is his to make after a conversation
  (2026-11-09, as the ledger records it; `09094ef1` cancelled two renames).
- Less of the monitor. `46899a83` records his word that its log is largely not needed; F20, the
  class with the most commits coming back, is in large part that log's.

## 4. The systems SIEVE has, and what each module holds

The player's half: every Python file under `sieve_player/`, 13,828 lines. `tools/`, `utilities/`
and the launchers are the next session's, and the lines they add to this part are not here yet. The
spans and the imports are from
`python -X utf8 docs/findings/experiments/2026-11-16-what-a-module-holds.py sieve_player`, with
`--members sieve_player/window.py` for the window's; what a name does is from reading it. A count
of sites is from a `grep` over `sieve_player/`, the pattern beside it.

### The systems

A system here is a job with one owner that others go through. Each row says where that holds and
where it does not.

| | system | modules | lines | what goes through it, and what goes round it |
| --- | --- | --- | --- | --- |
| S1 | The document | M01 | 546 | Every reader and writer of the pipeline: the canvas, the pane, the plan, the graph, the window, `bare.py`, `__main__.py`. Nothing writes a node but through `Document` or a node's fields. It has no history of its changes: the tree holds no undo. |
| S2 | The registry of tools | M11, M12 | 250 | Discovery (`main.py`, `__main__.py`, `bare.py`) and the menu's facts (`window.py:PlayerWindow.__init__`). The facets it declares are read round it: `registry:probe` has no caller outside its package (A2). |
| S3 | The plan and the keys | M02 | 248 | `graph.py:Graph.sync` and `__main__.py:show_plan`; every key the memo, the held file and the ledger hold is `plan.py:_key`'s. Nothing goes round it. |
| S4 | The runtime | M03, M04 | 822 | The worker, the walk, `bare.py`, the simulations and `bench.py` compute through `Graph`; the display reads `Graph.peek`. The memo is its own. |
| S5 | The decoder | M05 | 586 | The graph alone reads rows of it. The window opens it, corrects its count and tells it where the store is (H6). |
| S6 | The walk and its thread | M06, M07, M08 | 714 | One `_Walk` under three drivers: the worker's window lane, its clip lane, and `bare.py`'s process. |
| S7 | The held results | M09, and W14 of M24 | 337, and 103 counted in S10 | `held.py` holds the runs and the file; when a run is held, served or written is `window.py`'s (H2). |
| S8 | The store | M10 | 87 | Which folder, and what lies in it for whoever draws it. What a file in it is named is its writer's: a tool's and the decoder's. |
| S9 | The stream and its readers | M13 to M23 | 4,412 | Every run, read, turn and paint is an `Event` through one `Emitter`; the ledger, the catalogue, the report, the dump, the pace and the monitor's window read it. It is 4,412 lines to the 3,590 of S1 to S8 together. |
| S10 | The interface | M24 to M33 | 5,081 | Widgets that are told and report: by its module's own word each of the canvas, the pane, the plot and the strip knows nothing of the runtime, and `window.py` is the one place the two sides meet. |
| S11 | Launch and diagnostics | M34 to M37 | 358 | `play`, the command line, the recent list, where stderr goes. |
| S12 | The icon reference | M38 | 387 | Nothing of the player reads it. |

### What each module holds

| | module | lines | holds, by job |
| --- | --- | --- | --- |
| M01 | `document.py` | 546 | The saved form (`Document`, `Node`, `Wire`, `save`, `load`). Formats past (`VERSION`, `Document._lift_scale`, `_lift_bakes`, `_lift_cuts`). Reading a tool's facets (`expects`, `paths`, `static`, `inputs`, `optional`, `is_selector`). The rules of a wire (`produces`, `kind_of`, `fed`, `fits`, `validate`). Asking a selector for a file (`pick_path`, `pick_video`, `as_written`). A document from a list of tools (`from_tools`). What the plot shows (`shown`). |
| M02 | `plan.py` | 248 | Keys (`_key`, `base_key`). The plan (`plan`, `Entry`, `Plan`, `walked`, `shared_fold`). Why a node does not run (`_standing`). The plan as a sync event carries it (`facts`). |
| M03 | `graph.py` | 766 | What a band keeps (`inband`, `banded`, `gated`). Counting bytes (`nbytes`). The memo (`Memo`, `Ref`, `to_hold`). What a tool's `run` is handed (`Frames`, `Series`). Decoders on served files (`Readers`, `Graph._reader`). Asking a cutting tool for its files (`Graph.cut_file`, `Graph._named`). Computing and peeking (`Graph._compute`, `Graph.peek`, `Graph.density`). What a run said (`Graph.note`, `Graph.standing`). The stream's facts and its pass-throughs (`Graph.progress`, `Graph.began`, `Graph.tally`, `Graph.probe`, `Graph.demand`, `Graph.serving`). |
| M04 | `density.py` | 56 | A plane as counts on a fixed axis (`fold`). |
| M05 | `decoder.py` | 586 | Rows on two cursors (`Decoder`, `_Cursor`). The frame cache (`Decoder._put`, `Decoder._trim`). The table of frame times and its file in the store (`frame_times`, `_keep_times`, `_kept_times`, `read_frame_times_ahead`, `STORE`). Which footage a file is (`footage_print`, `footage_print_by_stamp`). Where the stream ends (`EndOfStream`, `Decoder.ends_at`). |
| M06 | `walk.py` | 384 | A walk of a range (`_Walk`). What a stack may hold (`_stack_for`, `_fits`, `STACK_BYTES`). Stepping (`_Stepped`, `_Walk.step`). The chain run whole (`run_chain`). The densities (`_Walk.fold`). |
| M07 | `worker.py` | 236 | The thread and its ladder (`Worker._serve`, `Worker._turn`). The scrub (`_Scrub`). The asks the GUI side sets (`Worker.set_window`, `request_row`, `walk_clip`, `give_clip`). |
| M08 | `bare.py` | 94 | The clip walked in a process of its own (`main`, `job`, `_Told`). |
| M09 | `held.py` | 337 | The runs and which serves a range (`Run`, `Runs`, `Chain`). The file (`File`). What a file is good under (`stamp`, `tools_print`). Bytes as text (`in_units`, `per_row`). |
| M10 | `store.py` | 87 | Which folder (`folder`, `chosen`, `choose`, `probe`). What it holds (`held`, `disk`). |
| M11 | `registry/__init__.py` | 169 | Discovery (`discover`, `Entry`, `is_tool`). The facets a tool and a widget may have (`FACETS`, `WIDGET_FACETS`, `hint`, `probe`). The menu's facts (`category`, `description`, `signature`). Who produces and expects a type (`types`). |
| M12 | `registry/__main__.py` | 81 | The report and the check (`report`, `check`). |
| M13 | `stream.py` | 215 | The event and its kinds (`Event`). Building one (`Emitter.probe`, `Emitter.turn`, `Emitter.demand`). What a thread has not left (`Emitter.still_out`). |
| M14 | `ledger.py` | 676 | The stream over time (`Ledger`, `Bucket`, `Walk`, `View`). What a node costs a row (`row_cost`). A history saved and read (`save`, `saved`, `replay`). |
| M15 | `catalogue.py` | 1,026 | The detectors (`unread`, `thrash`, `grows`, `seeks`, `slower`, `waits`, `signals`, `late`, `restarts`, `stalls`). What they found, kept (`Log`, `Sofar`, `_Baseline`). The figures any reader shows (`rows`, `needs`, `gui`, `machine`, `tight`, `alike`). A cold walk projected (`cold`, `Projection`). |
| M16 | `report.py` | 146 | Findings as text (`report`, `text`, `line`). |
| M17 | `trace.py` | 188 | The stream to a file (`Dump`, `read_dump`). To Chrome's format (`to_trace`). Resident memory (`rss`). |
| M18 | `stats.py` | 71 | Means and a rate for `bench.py` (`Stats`). |
| M19 | `machine.py` | 171 | The machine sampled (`Machine`, `Watch`, `thread_cpu`). |
| M20 | `pace.py` | 100 | A walk's rate (`Pace`, `Figure`). A duration as text (`clock`). |
| M21 | `pacecontrol.py` | 86 | The rate drawn (`PaceControl`). |
| M22 | `dev/timeview.py` | 1,214 | The monitor's window (`Window`, `TimeView`, the tracks, the panels, `Problems`, `Table`). |
| M23 | `dev/simulations.py` | 519 | A fault built on purpose for each detector (`_Run`, `run`). |
| M24 | `window.py` | 1,498 | The table below. |
| M25 | `canvas.py` | 948 | The network editor (`Canvas`). What a dragged wire may land on and what the menu offers (`Canvas.compatible`, `targets`, `_joins`, `_landing`, `menu_entries`). A type's colour (`type_color`). |
| M26 | `menu.py` | 187 | The Tab menu (`TabMenu`). |
| M27 | `pane.py` | 309 | A card a node (`Pane`, `Pane._build`). The video node's card (`Video`). What a widget is told if it can take it (`Pane.set_source`, `Pane.set_cut_files_in_use`). |
| M28 | `widgets.py` | 214 | A settings form and its rows (`ParamWidget`, `ChoiceList`, `Slider`, `ValueField`). |
| M29 | `plot.py` | 766 | The plot (`Plot`, `Line`, `Field`, `ChipRow`). The frame over it (`Stage`, `Head`). |
| M30 | `timeline.py` | 399 | The strip and the controls (`Strip`, `Controls`, `Timeline`). A series as min and max a column (`envelope`). A row as a time (`timecode`). |
| M31 | `theme.py` | 564 | The grays, sizes and the sheet (`sheet`, `gray`, `layer`). Fonts and glyphs (`install_font`, `glyph`). Widgets (`Layer`, `Form`, `Badge`, `CloseMark`, `GlyphButton`, `Splitter`, `readout`). |
| M32 | `filemenu.py` | 114 | Open Recent drawn (`fill`, `Row`, `when_text`). |
| M33 | `storecontrol.py` | 82 | The store drawn (`StoreControl`). |
| M34 | `__init__.py` | 52 | `play`, and its names imported on first use (`__getattr__`). |
| M35 | `__main__.py` | 41 | The command line (`main`, `show_plan`). |
| M36 | `recent.py` | 57 | The recent list (`note`, `entries`, `last`). The user's folder for SIEVE (`app_folder`). |
| M37 | `dev/__init__.py`, `dev/console.py`, `dev/qt_trace.py` | 208 | The Dev menu (`install`, `show`). Where stderr goes (`console.py:start`, `_Tee`). Where a Qt warning came from (`qt_trace.py:install`, `watchdog`). |
| M38 | `dev/reference/` | 387 | The icon sheet (`icons.py:Icons`, `Sheet`, `Marks`) and its download (`build_icons.py:download`). |

### What `window.py` holds

Composition is carrying a change or a result between two owners; the window's own is what a main
window has in any program; another owner's is a job with a rule of its own that a module either
has already or would be. The last is a reading, and the column is where to disagree with it.

| | job | names | lines | whose |
| --- | --- | --- | --- | --- |
| W01 | Not code: the docstring, imports, constants, comments and blank lines between names | | 182 | |
| W02 | Building the widgets and wiring their signals | `PlayerWindow.__init__`, `resizeEvent`, `_split_default`, `closeEvent`, `Header`, `Column` | 222 | composition |
| W03 | The runtime's life: a video opened, its decoder, graph, stream, ledger, samplers and worker made and unmade | `_open_video`, `_unload`, `_shortened`, `_sample`, `_timed`, `_gb` | 126 | composition |
| W04 | A change carried to the runtime | `sync`, `reflag`, `_picked`, `_restate`, `_keys`, `_params_changed`, `_store_changed`, `_asked_again`, `_invalidate` | 88 | composition |
| W05 | Results carried to the widgets | `_series_ready`, `_show_pinned`, `_set_length`, `_show_size`, `_show_takes` | 53 | composition |
| W06 | The selection, the pins and the bands relayed | `_select`, `_show_plot`, `_tell_shown`, `_show_bands`, `_toggle_pin`, `_band_dragged`, `_band_released` | 40 | composition |
| W07 | The clip walk asked for and told of | `_toggle_clip`, `_paced`, `_clip_walked`, `_clip_ready` | 31 | composition |
| W08 | A failure said | `_failed`, `_worker_ended`, `_draw_failed`, `_clip_refused` | 17 | composition |
| W09 | The store chosen | `_choose_store` | 10 | composition |
| W10 | The document's file: new, open, save, unsaved changes, recent, the title | `set_document` to `_retitle`, fourteen names | 101 | the window's own |
| W11 | The transport's state: the window, the playhead, play | `set_window`, `goto`, `seek`, `_scrub_begin`, `_scrub_end`, `toggle_play`, `_tick`, `_hover` | 75 | the window's own |
| W12 | The frame display: an array as an image, the overlay heated, the drawers, a click offered to them | `Display`, `to_qimage`, `heat`, `over`, `flow_top`, `imageable` | 181 | another's: a widget, as M29 and M30 are |
| W13 | Which file the video and each path input is: the selector asked, the loader run once a file, the file watched | `_pick_video`, `_pick_paths`, `_watch_taken`, `_path_changed`, `_note_selectors`, `load`, `_same` | 137 | another's: no module has it |
| W14 | When a run is held, served, given or written | `_ask_window`, `_as_given`, `_show_held`, `_chain`, `_key`, `_window_ready`, `_hold_run`, `_write_held`, `_clip_result`, `_whole`, `_save_held` | 103 | another's: S7 |
| W15 | The bare walk's process started, read and ended | `_toggle_bare`, `_start_bare`, `_bare_said`, `_end_bare` | 66 | another's: M08, whose lines these read |
| W16 | Which row's frame is shown, and whether the gate is on | `_show`, `_row_ready`, `_update_gate` | 34 | another's: W12 and S4 |
| W17 | How late the GUI thread's timer fires | `Lateness` | 18 | another's: S9 |
| W18 | The tools as a mapping, the broken ones apart | `catalogue` | 14 | another's: S2 |

The lines sum to 1,498, the file. 182 are not code, 587 composition, 176 the window's own, and 553
another owner's, which is 42% of the 1,316 that are code. The ledger's `Landed in` lines name
`window.py` first or second in fifteen of the twenty-five classes.

### What a module holds for another

Each cites its line above and the ledger class that came of its lying there, where one was traced.
A class is named only where a quoted commit is of that job; "none traced" is not "none".

- H1. W12: the frame is the one painted surface with no module. None traced.
- H2. W14: `held.py`'s opening says "the window says when a run is held and written", and the
  window's eleven names are that rule. F05, which the ledger has landing in `window.py` seven times
  and `held.py` four; `391bddd9`.
- H3. W13: the loaders' memory (`_taken`, `_driven`) and a file watcher live on the window. F01:
  "the document named the second video and the player had the first open" (`8a08c367`).
- H4. W15: `bare.py`'s opening lists the lines its process says, and their one reader is
  `window.py:PlayerWindow._bare_said`. None traced.
- H5. W17: `Lateness`, whose docstring argues why it is here and not in the probe. None traced.
- H6. M05 for S8, by way of M24: the decoder keeps a table of frame times in the store and learns
  where the store is from a module global, `decoder.py:STORE`, which only
  `window.py:PlayerWindow._open_video` assigns. `bare.py`, `smoke.py` and `bench.py` never do, so a
  `Decoder` there keeps no table and reads none kept. F07 is the table's class (`023c46ce`); that
  the bare walk pays for it is this session's reading of the code and was not measured.
- H7. M03 for M06, M09 and M24: `inband`, `banded` and `gated`, what a band keeps, and `nbytes`,
  imported by `walk.py` and `window.py` and handed to `held.Runs` by the window. F06: "the memo
  counted a table at its pointers" (`e9142899`).
- H8. M03 for S9: `Graph.progress` assembles every store's counters into an event, and four
  methods pass a call through to the `Emitter`. F20 has `graph.py` among where it landed, eight
  times.
- H9. M01 for S2: six readers of a tool's facets, there because the document imports nothing of
  the player, and beside them raw `getattr` in five more modules (A2). F17.
- H10. M36 for M10 and M37: `recent.py:app_folder`, read by `store.py` and `dev/console.py`.
- H11. M09 for M33 and a tool: `held.py:in_units`, bytes as text, imported by `storecontrol.py` and
  `tools/region.py`.
- H12. M20 for M24 and M22: `pace.py:clock`, a duration as text.
- H13. M25 for M22: `canvas.py:type_color`, imported by `dev/timeview.py`.

H10 to H13 are a helper living where it was first needed; none has a class.

## 5. What was built by attrition

The player's half. A place under `tools/` or `utilities/` is cited where a search found it and is
the next session's to read; the count of settings lines against computing lines over `tools/` is
that session's too. Attrition, by the spec, is a thing written more than twice whose copies have
drifted or which a fix in the ledger had to reach in more than one place.

### Attrition

- A1. A file written whole or not at all. With a part file and a replace: `document.py:save`,
  `held.py:File.write`, `recent.py:note`, `decoder.py:_keep_times`, `tools/_csvfile.py:replace`,
  `tools/_cutfile.py:_land`. Written in place: `store.py:choose`, `ledger.py:save`,
  `utilities/geometry/document.py:save`. Both tests hold. `929f1614` (F18, F10) took the leftover
  part file out of two copies, `document.save` and `_csvfile.replace`. And they have drifted:
  `recent.py:note` still passes on `OSError` and leaves its `.part`; `_keep_times` makes its part
  by `mkstemp` and the rest by a suffix; `File.write` clears in a `finally` and the rest in an
  `except`; and the geometry file, the one of these the user draws by hand, is opened for writing
  where it lies, so a write that fails leaves it cut short.
- A2. Reading what a tool declares. The registry's `probe` is used by the registry alone. The rest:
  `document.py`'s six readers; `plan.py:plan` (`cut_file`, `key_params`, `step`) and
  `plan.py:shared_fold` (`fold`); `walk.py:_Walk.step` and `walk.py:run_chain` (`fold`);
  `graph.py:Graph._named` (`cut_files`) and `Graph.drawing` (`draw`); `window.py:PlayerWindow.sync`
  (`draw`), `Display.mousePressEvent` (`pick`) and `PlayerWindow._note_selectors` (`matches`);
  `canvas.py:Canvas._joins` (`PRODUCES`), `Canvas._landing` (`PATHS`) and `Canvas.place`
  (`DEFAULTS`, as `document.py:Document.resolve` and `from_tools` also read it). Drift: `EXPECTS`,
  a string or a tuple, is made a tuple in four places by four pieces of code, `document.py:expects`
  and `registry:category`, `signature` and `types`. Ledger: F17, "bg_subtract's own MODES constant
  was read as the facet" (`64ce8f59`), in a commit that changed `canvas.py`, `document.py`,
  `graph.py`, `pane.py` and the registry together.
- A3. Saying a failure. A site chooses its own channel: the transport's line (7 writes in
  `window.py`, `progress\.setText\(`), the header's note (7, `\.note\.setText\(`), `canvas.errors`
  (3), `Pane.note` (4), the video card's `show_none` and `show_error` (3), a node's standing by
  `Graph.note` (6 calls in `walk.py`, 2 in `graph.py`, 1 in `window.py`), and stderr (`decoder.py`
  3, `window.py` 3, `ledger.py` 2, `worker.py` 1, `file=sys\.stderr`). No function takes a failure
  and decides where it is said. F04 is the class, 27 commits and 13 coming back, landing in
  `window.py` 13 times, `graph.py` 11, `worker.py` 10 and `pane.py` 5: fixed apart, by the ledger's
  own count. Whether the channels have drifted in what each says was not read.
- A4. A store bounded by bytes: `graph.py:Memo`, the decoder's cache (`decoder.py:Decoder._put`,
  `_trim`), `held.py:Runs.hold`, and a walk's stack (`walk.py:_fits`). What each lets go first
  differs on purpose and is no drift. What was fixed apart is the counting: F06's four commits
  coming back are the decoder's (`75212615`), the memo's (`e9142899`, `a639e63e`) and the stack's
  (`982ea14d`).

### Copies left alone

- A5. An optional method looked for on a settings widget, by `hasattr` at ten sites:
  `pane.py:Pane._build` (3), `Pane.set_cut_files_in_use`, `Pane.set_source`,
  `window.py:PlayerWindow._pick_paths` (2), `_note_selectors`, `goto`, `_series_ready`. It was
  attrition, and `997700a3` (F17) answered it by writing the eight names once, as
  `registry:WIDGET_FACETS`; the sites stand as they were and the names agree.
- A6. Whether a result is a series result, `isinstance(r, dict) and "signal" in r`: four times in
  `window.py` (`_series_ready`, `_whole`, `_clip_result`, `_show_pinned`), three in `held.py`
  (`good`, `Runs.hold`, `per_row`), once in `graph.py:gated`. No drift found, no fix traced.
- A7. The tools as a mapping of name to module: `document.py:_by_name`,
  `graph.py:Graph.__init__`, `window.py:catalogue`. The same line three times.
- A8. A line on stderr that opens `SIEVE` and the time, formatted where it is printed:
  `window.py` 3, `ledger.py` 2, `dev/timeview.py` 1. `dev/console.py` owns where stderr goes and
  not what a line of it looks like.
- A9. Whether two paths are one file: `window.py:_same`, `recent.py:note`,
  `tools/_cutfile.py` and `tools/file.py`, each by `normcase`.
- A10. A thread with its own handoff, six ways: `worker.py:Worker` on a condition,
  `trace.py:Dump` on a list taken each period, the window's writer of the held file as a thread a
  write, `machine.py:Watch` on a period, `decoder.py:read_frame_times_ahead` as a daemon, and the
  ledger's queue drained by whoever reads. These are not copies, and F02 and F03 were not read
  against them by hash; they are listed so that the candidates' session does.

Written twice and so not listed: a series as min and max a column (`plot.py:Plot._columns`,
`timeline.py:envelope`); naming a read as a seek, a decode or a cache's (`graph.py:Graph._compute`,
for the video and for a served file); a drawer's or a loader's params put through the widget when
there is one and to `_params_changed` when there is not (`window.py:PlayerWindow._picked`,
`_pick_paths`).

Two things the reading met that are neither. The string under `window.py:Display`'s two signals
is written as a docstring and is not one, the signals coming first, so `Display.__doc__` is None.
And `window.py:catalogue` is a function named as the module `catalogue.py` is, which `window.py`
also imports from.
