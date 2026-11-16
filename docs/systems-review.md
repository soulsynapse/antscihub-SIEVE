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
