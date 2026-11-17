# Systems review

Built a part a session by `docs/spec/systems-review.md`, which says what each part holds and the
order they are written in; a part not yet here is not yet written. The evidence it argues from is
`docs/findings/2026-11-16-what-came-back.md`, cited by class as F01 to F25, of which F09 is not
used, F01 holding it; the classes are as that finding has them after they were read with
Kendrick, and its last section has how he holds each. A figure here is of the
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

It is made for speed. Kendrick, reading this part: "It is a race with trex. SIEVE is made for
speed." `v5-runs`, which measured SIEVE against a port of TRex and added a decoder that reads
ahead, is parked two commits off v5 and unmerged (`c0b417f4`); that is where the measuring lies
and no sign the race was left.

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
Kendrick, reading the ledger's classes: sessions writing the code and helping him assess it is how
SIEVE got where it is and is "a non issue", so the sixth row is how the tree is written and no
friction of his. What the second row then argues for is a surface a tool declares and the player
checks, and nothing of one that is held still or given versions.

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
reading, and nothing in part 4 checks it. On the wire it stands with Bonsai, frames and what is
measured of them in one graph, and apart from Houdini, Nuke and VapourSynth, each of which carries
one kind. And in what it is for it stands nearest Raven, a band over a signal that leaves a table
of where things were, while Houdini, Raven, SLEAP and ImageJ each have a second form that runs
over many files, and SIEVE has none.

### Where it is headed

Direction, none of it in the tree. Kendrick, reading this part: a direction is no strong ground
for what SIEVE needs later, and the main things are what it needs now. So no candidate of part 3
rests on a line of this list but the one that is his own word, the first.

- A pipeline run over pieces of footage, replicates cut in space and bouts cut in time, and the
  results brought back to the footage: Kendrick, 2026-11-14, "Periods to bouts follows regions to
  crop", as the ledger and a session's note record it. The spatial half has begun: a region serves
  the clip it cut (`README.md`, `cut_file`; `07dd9830`).
- From one file to an experiment's data. It was read from the four videos beside one document,
  and Kendrick, reading this part, has it right and says data where this said files.
- Identity over finished tracks: `tools/resolve.py` is in the tree since `57b02e09` and in none of
  the nine documents. Kendrick, reading this part: correct.
- Names. A pass over the tools' and the regions' names is his to make after a conversation
  (2026-11-09, as the ledger records it; `09094ef1` cancelled two renames).
- More of pull. Kendrick, reading the ledger's classes: "pull is probably one of the most
  important things to build out", and what is asked for is in places made out where it should be
  said (F08).
- A tool named period, which cuts bouts out of a clip for further work, the next he means to
  build, and one that leans on a key being right (F05).

The monitor is not headed for less. What `46899a83` records as largely not needed is one reader
of it that has since gone, as the ledger's finding says under What this could not see; Kendrick
calls the monitor extremely helpful and finds a hang by it.

## 2. What a seasoned user of the neighbouring programs expects to find

A list to learn from, written after the candidates were settled. It scores nothing and makes
nothing a candidate. What another program has is from memory throughout and was not fetched,
but where a number in brackets follows, which is part 1's or part 3's. Where SIEVE stands is
from a search of `sieve_player/` for the thing's names and from part 4.

| a user reaches for | expected from | delivered there by | SIEVE |
| --- | --- | --- | --- |
| A node placed by typing its name | Houdini, Nuke | a Tab menu over the registered node types | Has it: `menu.py:TabMenu`. |
| A flag that says which node is shown | Houdini | the display flag, which is what asks for a cook [1] | Has it: the display and the overlay flags of a document, and the pins. |
| A look at any node while it runs | Bonsai | a visualizer opened on an operator | Has it: the flag for a frame, a pin for a signal. |
| The distribution of what is shown | Nuke, ImageJ | the Viewer's scopes; a histogram of the image | Has it, over time: `density.py:fold`, drawn by `plot.py`. |
| A band dragged on a view, and a table of what fell in it | Raven | a selection drawn on a spectrogram, kept as a row of a selection table [5] | Has it in its own form: a node's band, and a csv of the rows inside. |
| A result kept on disk and served in place of computing | Nuke, Houdini | a DiskCache node keyed by the hash [11]; a File Cache node | Has it: a region's cut clip, and the held series. E1 for what each is good under. |
| Many kinds of video opened | ImageJ, VapourSynth | Bio-Formats; source plugins | Has it: one decoder over libav, `decoder.py`. |
| Undo of an edit to the network | Houdini, Blender, Nuke | one stack every edit goes through | Not yet. The geometry utility has one (M52) and the player none. It becomes a candidate when a band or a node's settings are lost to a slip and could not be set again from memory. |
| The last session back after a crash | Blender, Houdini, Nuke | a copy saved on a timer, offered at the next launch | Not yet. The player has died once in use, by `docs/findings/2026-11-16-the-player-died-on-a-click.md`, which does not say what was lost; it becomes a candidate when something was. E4 has the mark of such a launch as a fix. |
| A node switched off without unwiring it | Houdini, Nuke | a bypass flag; a disable knob | Not yet. It would be seen as a document saved twice, with a node and without, to compare the two. |
| Nodes copied, and pasted into another file | Houdini, Nuke | the clipboard holding nodes as the file's own text | Not yet. It would be seen as a chain built again by hand in a second document. |
| A chain folded into one node and used again | Houdini, Nuke, Bonsai | a digital asset; a Group or Gizmo; a nested workflow [14] | Not yet. It would be seen as one run of nodes copied into a third document. E2's pieces are not this: they run one chain over many, where this names one chain. |
| A setting that varies over the clip | Houdini, Blender, Nuke | a channel or an expression on any parameter | Not yet, but a setting a wire drives (`registry:WIDGET_FACETS`, `set_driven`). It would be seen as a threshold that must differ between two stretches, which E2's pieces in time may answer first. |
| A row of the table clicked, and the view goes there | Raven | the selection table and the views being one selection [5] | Not yet. It would be seen as a csv opened in another program to find a row to look at in the player. |
| Marks made by hand and kept with the footage | Raven, SLEAP | annotation columns of a selection table; labelled frames in the `.slp` [7] | Not yet as truth to judge by, and it has been seen once: a day of linker variants dropped for want of ground truth (`4d8f513e`). Out of scope as labels to train on: part 1, a learner. |
| Identities mended by hand after tracking | SLEAP | proofreading in `sleap-label` [7] | Out of scope: part 1, a tracker that holds identity through a pile. |
| The same work over a folder, with no window | ImageJ, SLEAP, Raven, Houdini | a macro over a folder [8]; `sleap-track` [7]; a batch detector; TOPs [13] | E2. |
| The program driven from a script | ImageJ, Houdini, Blender, VapourSynth | a macro recorder [8]; a Python module that is the whole interface | E2 in part, its command being the first. A document is JSON and a tool a module that runs alone. |
| What is shown written out as video | VapourSynth, Nuke | the script piped to an encoder; a Write node | Not yet: a region's cut is the one video the player writes. It would be seen as a clip of an overlay wanted to show someone. |
| Frames from a camera, live | Bonsai | sources that are devices [6] | Out of scope: part 1's aim, a video, and its footage, files. |
| Tools installed from elsewhere | ImageJ, Houdini, VapourSynth | update sites; packages; a plugin folder | Out of scope: part 1's first row. `registry:discover` takes any folder. |

Two of the lines marked not yet say they have been seen. Neither is made a candidate by it,
the list being cut; they are where this part bears on the next reading of the list.

## 3. The candidates

The list, before any is read against a reference; an entry is written for each that Kendrick
leaves on it. A candidate's commits are told as prevented, where the problem would not have been
written had the system been there, or as made cheaper, where it would still have come and been
found or settled in one place. Both are what might have been, judged by the session that puts the
system forward and from each message's opening lines; a hash is filed in the ledger under the
class its line names, and that much can be checked.

### Systems the evidence argues for

- C1. What a run read, recorded, and its key made of that. F05's work done again, A11, and F22 by
  way of it. Prevented: none claimed. Made cheaper: `d30bd9f0`, `7f0a645d`, `4079a72d`. Most of
  its evidence is in no commit: Kendrick, that a setting which changes no result empties a cache
  and that he feels it all the time; and `key_params`, which one tool of thirty-eight has. What
  it would save is unknown until a one-off runs each tool and lists the params no `run` read.
- C2. One answer to what a kept thing is good under. A19, and F05's stale result served.
  Prevented: none claimed. Made cheaper: `391bddd9`, `eb973068`, `00fd8c19`, `be59a820`.
- C3. A clip walked bare, compared with what the player holds for the same keys and rows. It
  finds and prevents nothing. F02's silent kind, F05 and the half of F07 that is a tool's result.
  Made cheaper to find: `54ad1445`, `88a413f1`. Kendrick's case under F07, an identity made anew
  by a walk begun part way, is in no commit.
- C4. The kind on a wire, said in one place the player and the tools both read. F17's first part,
  H17. Prevented: `cd887844`, `cce7cb8e`. Made cheaper: `e9142899` (also F06), `2216f272`.
- C5. One reader of what a tool declares. F17's second part, A2, H9, and A11 where a param is
  read with a fallback. Prevented: `64ce8f59`, in the part of it that read a tool's own constant
  as a facet. Made cheaper: `997700a3`, `ba71e6f5`.
- C6. What is asked for, said by what asks. F08's first clause. Prevented: `98e65cac`,
  `3bd2d8d1`. Made cheaper: `5c095255`, `e9142899`, `fbf4fab7`. Kendrick, of a draw on the video
  that is hard to make known as needed, is in no commit.
- C7. One function that writes a file whole or not at all. F18, A1. Prevented: `929f1614`. Made
  cheaper: `e4c08b3a`, `2060fbfe`. It does not reach the larger half of F18, a file replaced or
  deleted while a reader held it (`a603747b`, `eb973068`, `07dd9830`).
- C8. One place a failure is said, and a mark of a launch that did not end cleanly. F04, A3.
  Prevented: none claimed. Made cheaper: `c6de1d12`, `59ec9351`, `b588358c`, `81854fd6`,
  `3216eb59`. The mark's evidence is `docs/findings/2026-11-16-the-player-died-on-a-click.md`.
- C9. A job stopped when its own key moves and by nothing else, with a way to tell a long call
  and a child process. F22, and the three ways a child is held under A10. The rule is in the
  tree for a read, a walk and a cut (`18c2010a`, `36e3565e`, `a603747b`), and those are what it
  settled. What is left has `020ccd0a`, made cheaper, and Kendrick's word that a bare walk is
  dropped by changes that do not concern it (H4).
- C10. The walk named on each signal of its progress. F21's one case that stands. Prevented:
  `b5c5e8f5`. Made cheaper: `5ceb287a`.

### Named by Kendrick

- C11. A pipeline run over pieces of footage, replicates cut in space and bouts cut in time, the
  results brought back to the footage. His, 2026-11-14, as the largest thing missing; the ledger
  has it under what it could not see. No commit, by its nature. C1 and C2 are what it leans on,
  by his word of the tool named period.

### Held by the tree, for shrinking

Lines are part 4's or `wc -l`. Callers are from `grep -rlE` over `sieve_player`, `tools`,
`utilities` and the three scripts for an import of the module or a call of the name; `tests/` is
not read, so a caller there is not counted.

- C12. The stream and its readers, S9: 4,412 lines to the 3,590 of S1 to S8. Of what it found,
  four commits of v5 say in their opening lines that a report or a figure of it named the
  problem (`aaca3f7e`, `98e65cac`, `5c095255`, `687f37b0`), of nine whose message matches
  `git log v5 --no-merges -i -E --grep="monitor (report|found|named|read)|reports? of
  2026|the monitor found"`; F20 is 29 commits spent on the monitor itself. Kendrick finds a hang
  by it and calls it extremely helpful, so the candidate is its parts with few readers and not
  the whole: `catalogue.py:cold` and `Projection`, 52 lines and no caller found;
  `ledger.py:saved`, no caller found, and `replay`, called by `report.py`'s command line alone;
  `trace.py:to_trace`, 27 lines, called by its own command line alone; `stats.py`, 71 lines, read
  by `bench.py` alone.
- C13. The icon reference, S12: 387 lines, one caller, the Dev menu (`dev/__init__.py`).
- C14. `tools/retired/`, M50: 185 lines, no importer found; the registry does not list them.

### Traced to none

Classes. F01: no system; part 4's list of what a module holds for another is to watch. F03 and
F06: handled, by Kendrick's word, or the monitor's to find. F08's second clause, the rule a store
keeps or lets go by: each store's own, and H2 is where it is watched. F07's footage: the decoder is the
system and its fixes are in. F10 and F11: by design. F12: a document lifted on load is fine by
him. F13, F14, F24, F25: how the tree is written, and no friction of his. F15, F16: fine as they
stand. F19: fact, with trust in the suite mattering and one test still failing some runs
(`023c46ce`). F17's third part, the names of the stream's records: settled by `d5381dad`. F20: the
monitor being set, and C12 is where its size is asked of. F23: the monitor shows a slow tool.

Attritions. A4, a store bounded by bytes: its class is F06. A12, a bound typed as text: a third
copy stands and is a fix. A10's threads, which part 5 left for this reading: of the openings of
F02's and F03's commits, the threads met over the plan (`54ad1445`, `6bf747b6`, `b33be8d5`), the
document (`e2a0191d`), the dump's file (`84d53ce1`, `efd1fe10`), the decoder's locks
(`75212615`, `ce9e6b0b`), the worker's wait (`119391c9`, `ccb805a4`) and an object's life
(`687f37b0`), and none tells of one handoff fixed in two of the six; the rest were not read past
their filing.

Fixes and no system, from part 5 and the ledger: five tools draw by an `outline` param nothing
declares; `recent.py:note` leaves its part file; the geometry file is written where it lies; a
document is written CRLF.

### The cut

Kendrick's, on reading the list. Seven are written up, in four entries: C1, C2, C4 and C5 as one,
E1, at his word that they are one shape and the most valuable of the list; C6, which he holds as
important as those and which reads what E1 declares; C8, very important by his word and needing
talk before it is written; C11 last. Not written up: C3, a check and no system, which E1 takes as
the check its key marks are held to; C7 and C10, each a fix; C9, whose rule the tree has and
whose remainder is E1's; C12 to C14, deletions that wait on a search of `tests/`.

### E1. What a tool declares, and the key the player makes of it (C1, C2, C4, C5)

The job: a tool says once what its settings are, what it reads and what it hands out, and the
player makes of that alone the key of each result, whether a kept result is still good, and what
may be wired to what.

The evidence. A setting that changes no result empties a cache: `outline` is read by nine `draw`s
and by no `run` (A11), lies in a node's params, and `plan.py:plan` keys a node by the whole of
them unless its tool has `key_params`, which `tools/region.py` alone has; Kendrick feels it all
the time, and how many settings are so is not counted. Six places answer what a kept thing is
good under (A19; `391bddd9`, `eb973068`, `00fd8c19`, `be59a820`). What lies on a `blobs` wire is
defined under `tools/` and known to the player by its shape (H17; `cd887844`, `cce7cb8e`,
`e9142899`, `2216f272`). A tool's facets are read by `getattr` in six modules beside the registry
(A2, H9; `64ce8f59`, `997700a3`, `ba71e6f5`), and a setting is said in up to four places (A11):
in `tools/top_hat.py` the default in `DEFAULTS`, the range in `settings` and in a constant, the
check in `top_hat`. F05's work done again: `d30bd9f0`, `7f0a645d`, `4079a72d`.

The reference is Nuke's Op. It is the best fit because it is a pull by the row over image planes,
as SIEVE's frame nodes are, and because it holds the four jobs as one contract in a fixed order,
where Houdini spreads them over parms, data ids and interests. A node declares its knobs; its
hash is by default "the hashes of all its inputs" and "the hashes of all the knob values at that
frame/view" [11]; a knob flagged `NO_RERENDER` "doesn't contribute towards the hash" [11]; the
Viewer and the DiskCache node "use the Op hash as a key directly" [11]; `_validate` sets what the
node will hand out, its format, channels and frame range, before any pixel; `_request` tells it
"the region and channels of interest"; then `engine` computes [4]. The structure is the Op and
its knobs, the owner is Nuke, and every cache goes through the hash.

The pressure it answers: plugin authors who have not read Nuke, and a disk cache that outlives
the session and is shared by a studio. SIEVE is under the first by part 1's second row, and under
the second on one machine only, by its third and fourth: a held file, a csv and a cut clip
outlive a session, and a recompute is long because the footage is.

| program | a setting is declared | what keys a result | who records a dependency | what a node says of its output | the key reaches |
| --- | --- | --- | --- | --- | --- |
| Nuke | once, as a knob | inputs' hashes and every knob but those flagged out [11] | the node, by a flag or `append` | `_validate`, before computing [4] | memory, Viewer and disk caches alike [11] |
| VapourSynth | as arguments of the script's call (m) | nothing: a cache holds frames by number for a node that lives as long as the script (m) | the filter, at creation: "An array of nodes the filter requests frames from and the access pattern" [9] | "The output format of the filter", at creation [9] | no store past the process (m) |
| Houdini | once, as a parm template (m) | no key: a node is dirty or not, and its own parms are "marked as used for cooking by default" [12] | the node, calling `addExtraInput` "upon every cook" for what it read of another [12] | geometry with its attributes, known by cooking (m) | file caches are a node the user places (m) |
| Blender | as RNA properties (m) | no key: a change tags what depends on it [3] | the relations builder, "at a dependency graph construction time" [3] | a datablock's type | evaluated copies in memory [3] |
| Shake, a build system | in the rule | what the rule read, recorded as it ran and checked on the next run (m) | the system, by watching | a file | a store shared between machines (m) |
| SIEVE | in up to four places (A11) | the upstream key, the tool's name and all its params, or `key_params` (`plan.py:plan`) | the tool, by `key_params`, in one of thirty-eight | `PRODUCES`, a name; what the name holds is the tools' (H17) | the memo and the held file by `plan.py:_key`; five places more by their own (A19) |

None of the three programs of SIEVE's family records what a run read: each keys or dirties by
every setting and lets the declaration take one out. Recording is Shake's, and its price is that
a key is not known until the rule has run once, where `plan.py` makes every key before anything
runs and is pure for it. C1 was put as recording; the references argue for the mark.

The smallest thing that answers the evidence is three, sharing a place:

- A setting declared once: its default, its kind of row, its range or choices, and whether it
  changes the result. `DEFAULTS`, the rows of a plain `settings`, a check of a choice and the key
  are read off it. The three cards with a state of their own keep their `settings`.
- The kinds a wire carries in one table that `sieve_player` holds and a tool imports: the name,
  whether it is rows, how its bytes are counted, whether it can be overlaid. Today those are
  `tools/_table.py`, `graph.py:nbytes` and `gated`, and `document.py:OVERLAYABLE`.
- The registry as the one reader of a facet, with `EXPECTS` made a tuple once.

And one rule beside them: a store of a node's result is named by the plan's key and the
footage's print and by nothing of its own. Which of A19's six that is true of is not known, the
six not having been read whole, and reading them is the first step of building.

What of Nuke it leaves out: the frame, view and proxy in a hash, SIEVE keying by row beside the
key; Ops unified by hash; `_request`, which is C6's; a class a tool inherits, a tool staying a
module of attributes; and a surface held still across versions, part 1 arguing for one that is
checked and not for one that is kept.

What it takes: every tool is touched, the 237 lines of plain `settings` in 35 tools become
declarations, and `document.py`'s six readers, `plan.py`'s and `canvas.py`'s go through the
registry. It replaces `key_params` as a function where a mark says as much, the fallbacks of A11
and the four makings of a tuple. SIEVE gives up a `settings` that is a tool's own code in the
plain case, and a held file made under a key that a mark then changes is found by nothing, as
`391bddd9` records of the last such change.

How it is shown right, the change being large. Three of its four steps change no key: the
registry as the one reader, the settings declared once, and the wire kinds moved. For each,
`python -m sieve_player <document> --plan` over the nine documents prints the same table before
and after, the plan being pure. The fourth, the marks, changes keys on purpose and is held to
two checks: a one-off that runs each tool under two values of each setting marked as changing
nothing and compares what `run` hands out, and C3, a clip walked bare compared with what the
player holds under the same keys.

The case for leaving it alone: every bug cited is fixed; `key_params` exists and could be
written for the tools whose settings are worst; the saving of the marks is unknown until the
settings no `run` reads are counted; and a tool is one file on purpose, which a declaration read
by the player makes less so.

Verdict: build, the three steps that change no key first, and the marks after the count.

A senior developer of Nuke, reading SIEVE: the hash is right and already yours, but a knob is
not a thing here, so nothing can hang on one, and five of your caches do not use the hash you
have. What they would not build again at this size: the knob flags, some dozens of them, where
SIEVE needs one, and the hash's context of frame, view and proxy (the count of flags is from
memory).

(m) is from memory and was not fetched. [3], [4] and [9] are part 1's.
[11] learn.foundry.com/nuke/developers/80/ndkdevguide/advanced/hashing.html
[12] sidefx.com/docs/hdk/_h_d_k__op_basics__overview__dependencies.html. Fetched on 2026-11-16
through a summarising fetch, so a quotation is as that reader gave it.

### E2. A pipeline run over pieces of footage (C11)

The job: the chain tuned on one piece of the footage, a region of the plate or a stretch of its
rows, is run over every such piece, and what each run found comes back in the footage's own
pixels and rows.

The evidence is Kendrick's word and no commit: the largest thing missing (2026-11-14), and, on
reading this list, that it "is going to have to exist" and is "definitely what it is reaching for
right now". In the tree the half in space has begun and stops at one piece: a `region` serves the
clip it cut, `plan.py:Entry.piece` says which piece a node's inputs are of, and a node that reads
across two is refused. No tool cuts in time, nothing runs a document over each choice of a
piece, `tools/file.py` picks one video where the experiment's folder holds four, and
`bare.py` walks one clip, started by the window.

The reference is Houdini's TOPs. It is the best fit because its unit is no file but a work item,
which "contains attributes" that "are passed down to work items created from 'parent' work
items" [13], so a piece cut from a piece carries how it was cut, and because it has both halves:
a node "can generate multiple new work items based on previous work items ('fan-out')", a wedge
making "the number of wedges, multiplied by the number of incoming work items", and a partition
"doesn't continue processing until all the work items in the group are done", Wait for All
grouping "all incoming work items into a single partition" [13]. The structure is the work item
and its attributes, the owner is the TOP network beside the network that computes, and every run
of a piece goes through it. A changed parameter dirties the node that made the items, and "any
work item whose attributes have changed since the last cook are considered dirty" [2].

The pressure it answers: thousands of items on a farm of machines, and work that outlives the
session that asked for it. SIEVE is under neither by part 1's last row; it is under the count of
files in a study, which part 1 has as headed for and Kendrick now has as where it is.

| program | what a piece is | who makes the pieces | state across pieces | how results come back | where it runs |
| --- | --- | --- | --- | --- | --- |
| Houdini TOPs | a work item with attributes [13] | a node, from parameters or from the items above it [13] | none: an item is a job of its own [13] | a partition holds "the merged information of the grouped work items" [13] | a scheduler, the machine or a farm [2] |
| Bonsai | a sequence within a sequence: `CreateObservable` "creates a new observable sequence controlled by the operators inside the group" [14] | an operator on the canvas | none carried, each being a new sequence, by this session's reading of [14] | an operator "collecting all the items from each sequence", `Concat` "one at a time" [14] | live, in the one workflow |
| ImageJ | a file of a folder [8] | the folder | whatever the macro leaves set (m) | a results table, or a file a piece in the output folder [8] | the one process |
| SLEAP | a video given to `sleap-track` [7] | the command line | none (m) | a `.slp` a video [7] | a second program [7] |
| VapourSynth | whatever the script's own loop says, the script being Python [10] | the user's code | the user's | the user's | the script |
| SIEVE | a region's shape, one chosen in a node's params; no piece in time | the geometry file, drawn by hand | does not arise, one piece being walked | a csv named by its rows, in the cut clip's own pixels (`tools/csv.py`) | the player, or `bare.py` for the piece chosen |

Both programs that have pieces within a file run each as a thing of its own, with no state of a
walk carried in. The ledger leaves that open for SIEVE as Kendrick's: whether a bout walked
alone is to equal the same rows cut from a walk of the whole clip (F05). The references answer
alone, and a tracker's identities then begin anew in each bout.

The smallest thing that answers his word is four, and the for-each is a wedge:

- A piece's record: the steps that cut it, rows or a rectangle, each relative to the piece
  above, and their sum on the footage. `tools/region.py:origin` is the step in space.
- A tool that cuts in time as `region` cuts in space, the one he calls period.
- A command that walks a document with no window under a named choice of each cutting node, and
  writes what its `csv` nodes write. `bare.py` is this for the choice the document holds.
- The command run once a choice, each a process, the choices being the product of what each
  cutting node offers. A piece's results are keyed apart by the params that chose it, which is
  why E1's key comes first.

Lifting back is then arithmetic on a table by the record's sum, done where the table is written.

What of TOPs it leaves out: the scheduler and the farm; items generated while the work runs,
SIEVE's pieces being known from the document before a walk; attributes as a general store, the
record being the one thing a piece carries; partitions other than all; and a second network,
the cutting nodes lying in the one document.

What it takes is not sized here: the half in time needs a node that is no served file to set
the rows a document is walked over, which the tree has for a served clip alone, and how far
that reaches into `plan.py` and `walk.py` was not read. It replaces a hand's loop of choose,
walk, write. SIEVE gives up nothing it has; what it takes on is a second way a document is run
that must give what the window gives, which the bare walk already is and which H6 says differs
today in its decoder.

The case for leaving it alone: the loop by hand is short at four regions and four videos; part 1
has Kendrick's own word that a direction is weak ground; and built before the keys are right it
multiplies every stale result by the count of pieces.

Verdict: build, after E1's steps and after the question of a bout walked alone is answered.

A senior developer of TOPs, reading SIEVE: you have the item already, a node's params that
choose a piece, and you have the job, the bare walk; what is missing is the thing that makes
one from the other and waits. What they would not build again at this size: the scheduler, and
dynamic generation, which is most of what makes a TOP network hard to reason about (the last
clause is this session's and no developer's).

(m) is from memory and was not fetched. [2], [7], [8] and [10] are part 1's.
[13] sidefx.com/docs/houdini/tops/intro.html [14] bonsai-rx.org/docs/articles/higher-order.html.
Fetched on 2026-11-16 through a summarising fetch, so a quotation is as that reader gave it.
Bonsai's windows by time were looked for on [14] and are not on that page.

### E3. What is asked for, said by what asks (C6)

The job: each thing that shows or writes a result says which node it reads, over which rows and
what of it, and the worker computes what is said and nothing else.

The evidence. F08's first clause, with Kendrick's word that pull is "one of the most important
things to build out" and that "sometimes I want a draw on the video that is hard to surface as
something needing it". The tree has both ways side by side: what the plot reads is said, by
`graph.py:Graph.watch`, and what the frame's overlay reads is taken, by `graph.py:Graph.drawing`,
to be every fed frame node whose tool has a `draw`. The display itself asks nothing: it reads
`Graph.peek`, which never computes, and what is there to be read is what the worker's ladder
chose to make (`worker.py:Worker._turn`). Work done for nothing that asked: `98e65cac`, the
window walk folding a density for every fed frame node, shown or not, and `3bd2d8d1`; done
oftener than anything read it, `e9142899` and `5c095255`; not done for something that asked,
`fbf4fab7`.

The reference is Houdini's interest. It is the best fit because SIEVE's readers are what
Houdini's are, a few elements of the interface with a standing wish and no single call to wait
on, where Nuke's and VapourSynth's reader is a render that asks for a frame and blocks or is
called back. The asker is "some UI element (such as the viewport) that observes the nodes whose
display flag are enabled", and "nodes are never cooked unless they are asked for their data" [1];
a UI element expresses an "interest on the nodes" and is told to recook when they are dirtied
[12]. The structure is the interest, the owner is the node graph, and a cook begins only at one.

The pressure it answers: networks of thousands of nodes of which a few are looked at. SIEVE is
under it by another measure, part 1's row of the length and size of footage: a chain is short
and a row of it is dear.

| program | who asks | what an ask names | work with no asker |
| --- | --- | --- | --- |
| Houdini | a UI element with an interest [12] | a node's data | none: "never cooked unless they are asked" [1] |
| Nuke | the Viewer or a write, and each node of the one above it | "the region and channels of interest" [4] | none, by the pull [4] |
| VapourSynth | the script's output, and each filter in `arInitial` [9] | frames by number [9] | none (m) |
| Blender | what is seen | nothing is named: a change is pushed, and "it is important to avoid updates of invisible objects" [3] | what a visibility flag does not stop |
| Bonsai | a subscriber: "the downstream operator ... subscribes" [6] | the whole sequence | none, a sequence with no subscriber not running, by [14]'s "no data actually flows" |
| SIEVE | the plot, by `Graph.watch`; for the frame and the walks, the worker's ladder | the plot's nodes; the window; the row under the playhead | the overlay's nodes whether drawn or not (`Graph.drawing`); the monitor names such work after it is done (`catalogue.py:unread`) |

The smallest thing that answers the evidence is the overlay's ask said as the plot's is: the
display tells the graph which drawers it draws. Beyond it, and wanted when E2 needs a walk with
no window to ask for a csv over a whole clip: an ask as a value, who, which node, which rows and
whether its result, its fold or its drawing, held as a set the ladder reads in place of
`Plan.walk`, `Graph.drawing` and `Graph.watch`.

What of Houdini it leaves out: dirtying, SIEVE knowing by a key what is good and needing no
flag; kinds of interest; and a cook on the asker's thread, the GUI thread here never computing.
Of Nuke, the region within a frame: a cut clip is SIEVE's region.

What it takes: the first is a method and its caller. The second is the ladder of
`worker.py:Worker._turn` and the three methods of `graph.py`, and was not sized. It replaces a
rule the worker holds of what is worth making. SIEVE gives up a ladder whose whole order is read
in one function, and an ask then needs a rank where a rung has a place.

The case for leaving it alone: every commit cited is fixed, the ladder has four rungs, and the
monitor already names work nothing read.

Verdict: build the first; watch the second, which E2 turns, a command that walks with no window
being a reader the ladder has no rung for.

A senior developer of Houdini, reading SIEVE: your viewport does not ask, it looks in a cache
and hopes, and a thread elsewhere guesses what it will look for. What they would not build
again at this size: interests of more than one kind.

### E4. One place a failure is said (C8)

The job: a failure is made a value where it is met, and one function decides where it is shown.

The evidence. F04, 27 commits and 13 coming back, over 35 days, fixed apart in `window.py`,
`graph.py`, `worker.py` and `pane.py`; A3, seven channels and a site choosing its own; and a
process that ends saying nothing, by `docs/findings/2026-11-16-the-player-died-on-a-click.md`.
None is claimed as prevented. Kendrick, on the list: an ideal to be worked towards, sites moved
into one thing as problems come up, the one thing needing a structure, and no priority.

The reference is Python's `logging`. It is the best fit because it is the structure he asks for
and nothing more, a record parted from where it goes, and is in the standard library, so its
price at SIEVE's size is known. "Log event information is passed between loggers, handlers,
filters and formatters in a LogRecord instance", "handlers send the log records ... to the
appropriate destination", and "the level set in each handler determines which messages that
handler will send on" [15]. The structure is the record, the owner is the application, which
alone configures handlers [15], and every message goes through a logger.

The pressure it answers: code of many authors writing to destinations none of them chose. SIEVE
is under it by part 1's row of who writes the code, a session choosing a channel at each site.

| program | a failure is | who decides where it shows | where |
| --- | --- | --- | --- |
| Python `logging` | a `LogRecord` [15] | the application's handlers [15] | wherever a handler sends |
| Houdini | an error or a warning added to the node that cooked (m) | the node graph | a badge on the node and its info (m) |
| A language server | a diagnostic: range, severity, source, message (m) | the editor | the line, a list, the status bar (m) |
| ImageJ | an exception in a window of its own, or a line in the Log (m) | the site | as written |
| SIEVE | a string, set where it was met | the site | one of seven channels (A3) |

The smallest thing is the record and a function of a dozen lines: what failed, a node or the
player; who is charged, the tool, the footage or the player; and the text. A node's goes to its
standing and its card, the player's to the header, each to stderr. No site moves until a fix
touches it. Whether the record is `logging`'s own is open.

What of `logging` it leaves out: the tree of loggers, formatters, configuration from a file,
and levels beyond what the record's two fields say.

What it takes: the function, and then nothing until a site is touched. It replaces nothing at
first. SIEVE gives up nothing. The mark of a launch that did not end cleanly is a fix apart, a
file written at launch and removed at a clean close.

The case for leaving it alone is Kendrick's and is the verdict.

Verdict: watch. What turns it: the next commit the ledger would file under F04, whose fix then
lands in the one place and brings its site with it; or E2, a walk with no window having no
header and no card to say a failure on.

A senior developer of `logging`, reading SIEVE: seven print statements with seven audiences.
What they would not build again at this size: the hierarchy of loggers and its configuration.

(m) is from memory and was not fetched. [1], [3], [4], [6], [9], [12] and [14] are above.
[15] docs.python.org/3/howto/logging.html, fetched on 2026-11-16 through a summarising fetch.

## 4. The systems SIEVE has, and what each module holds

Every Python file of the tree: 13,828 lines under `sieve_player/`, 3,771 under `tools/`, 2,010
under `utilities/` and 251 in the three scripts at the root, 19,860. The spans and the imports are
from `python -X utf8 docs/findings/experiments/2026-11-16-what-a-module-holds.py sieve_player tools
utilities`, with `--members` for a class's; what a name does is from reading it. Every file under
`tools/` and the three scripts were read whole; of the utility, `document.py`, `library.py`,
`look.py`, `video.py`, `table.py` and `window.py` past its `__init__` were, and `editor.py`,
`view.py` and `shapes.py` are told here by their names and docstrings. A count of sites is from a
`grep`, the pattern beside it.

### The systems

A system here is a job with one owner that others go through. Each row says where that holds and
where it does not.

| | system | modules | lines | what goes through it, and what goes round it |
| --- | --- | --- | --- | --- |
| S1 | The document | M01 | 546 | Every reader and writer of the pipeline: the canvas, the pane, the plan, the graph, the window, `bare.py`, `__main__.py`. Nothing writes a node but through `Document` or a node's fields. It has no history of its changes: the player holds no undo, and the one in the tree is the geometry utility's (M52). |
| S2 | The registry of tools | M11, M12 | 250 | Discovery (`main.py`, `__main__.py`, `bare.py`) and the menu's facts (`window.py:PlayerWindow.__init__`). The facets it declares are read round it: `registry:probe` has no caller outside its package (A2). E1: build. |
| S3 | The plan and the keys | M02 | 248 | `graph.py:Graph.sync` and `__main__.py:show_plan`; every key the memo, the held file and the ledger hold is `plan.py:_key`'s. Nothing goes round it for a node's result; what a kept file is good under is answered in five places more (A19). E1: build. |
| S4 | The runtime | M03, M04 | 822 | The worker, the walk, `bare.py`, the simulations and `bench.py` compute through `Graph`; the display reads `Graph.peek`. The memo is its own. E3: build its first part, watch its second. |
| S5 | The decoder | M05 | 586 | The graph alone reads rows of it. The window opens it, corrects its count and tells it where the store is (H6). |
| S6 | The walk and its thread | M06, M07, M08 | 714 | One `_Walk` under three drivers: the worker's window lane, its clip lane, and `bare.py`'s process. E2: build; E3: watch. |
| S7 | The held results | M09, and W14 of M24 | 337, and 103 counted in S10 | `held.py` holds the runs and the file; when a run is held, served or written is `window.py`'s (H2). |
| S8 | The store | M10 | 87 | Which folder, and what lies in it for whoever draws it. What a file in it is named is its writer's: a tool's and the decoder's. |
| S9 | The stream and its readers | M13 to M23 | 4,412 | Every run, read, turn and paint is an `Event` through one `Emitter`; the ledger, the catalogue, the report, the dump, the pace and the monitor's window read it. It is 4,412 lines to the 3,590 of S1 to S8 together. |
| S10 | The interface | M24 to M33 | 5,081 | Widgets that are told and report: by its module's own word each of the canvas, the pane, the plot and the strip knows nothing of the runtime, and `window.py` is the one place the two sides meet. E4: watch. |
| S11 | Launch and diagnostics | M34 to M37, M61 to M63 | 609 | `play`, the command line, the recent list, where stderr goes; `main.py`, and two scripts that drive the player with no screen, `smoke.py` and `bench.py`. |
| S12 | The icon reference | M38 | 387 | Nothing of the player reads it. |
| S13 | The tools | M44 to M50 | 3,099 | The registry finds a tool, and the graph, the walk, the pane and the display call what it declares; nothing else reaches one. A tool reaches the player through `ParamWidget`, `theme` and `play`, and three go past `sieve_player.__all__`: `background.py` (`decoder.EndOfStream`), `region.py` (`held.in_units`) and `bg_subtract.py`'s launcher (`document`). What a tool may import is `tests/test_seams.py`'s to say, by `sieve_player/__init__.py`'s word, and the tests are not read here. E1 and E2: build. |
| S14 | What tools share | M39 to M43 | 672 | A tool imports of these and of no other tool, by each file's own word. Two of the five were made by fixes the ledger files under F10: the table kind out of `blobs.py` and `blobs_to_mask.py` (`32bbc5a6`), its drawing out of `_table.py` (`d113c8bb`). `_cutfile.py` goes past `__all__` too (`store`, `decoder.footage_print_by_stamp`). |
| S15 | The geometry utility | M51 to M60 | 2,010 | A program of its own: it imports nothing of `sieve_player` or `tools`, and meets them at one file, the geometry JSON, and one command line (`tools/region.py:utility_command`). It has what the player has not: undo (M52), an ask before unsaved work is left (M57) for a file a hand drew, and a library of kept configurations (M54). |

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
| M08 | `bare.py` | 94 | The clip walked in a process of its own (`main`, `job`, `_Told`). By Kendrick's word it is his measure of how fast a chain can go, against how fast the player walks it, and a way to results; he leans on it often. |
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
| M39 | `tools/_table.py` | 106 | The table kind on a `blobs` or a `tracks` wire (`DTYPE`, `TRACKS_DTYPE`, `plane_dtype`, `plane`, `is_table`, `is_tables`, `with_column`). How a record meets a plane (`footprint`, `moments`). The ways a record is outlined (`OUTLINES`). A bound typed as text (`bound`). |
| M40 | `tools/_draw.py` | 62 | A table drawn on the frame (`contour`, `outline`, `draw`, `draw_tracks`). |
| M41 | `tools/_blocks.py` | 27 | A plane reduced over a grid of cells (`reduce_blocks`, `METHODS`). |
| M42 | `tools/_csvfile.py` | 177 | The key line of a csv (`key_line`, `parse_key`, `parse_kind`, `written_key`). The file written whole and read back (`replace`, `read`). The Write card (`widget`). |
| M43 | `tools/_cutfile.py` | 300 | Where a cut file lies in the store and what it is named (`folder_for`, `key`, `rect_key`, `file_for`, `landed`, `sidecar`, `whole`). One ffmpeg run and how its files land (`command`, `Cut`, `take_name`). What of the store nothing uses, and deleting it (`unused`, `delete`). |
| M44 | `tools/region.py` | 495 | The geometry file read and checked (`load_geometry`, `_shape`, `_number`). A shape's geometry (`contour_of`, `rect`, `inside`, `table`, `crops`, `served`, `origin`). The cut (`run`, `key_params`). The clip served in its place (`clip_of`, `cut_file`, `cut_files`). The click and the outlines (`pick`, `draw`). The utility started (`utility_command`, `launch`). The card: the chooser, Draw, Cut with its bar and its poll, the unused clips counted and deleted (`settings`, 175 lines). |
| M45 | `tools/file.py` | 114 | The rule that picks a file (`matches`, `select`, `names`, `rule_for`). The card: Browse and the list of matches (`settings`, 44 lines). |
| M46 | `tools/csv.py` | 121 | The rows handed on (`run`). The file's lines (`kind_of`, `fields`, `columns`, `lines`, `text`, `write`, `default_name`, `count`). Its card is M42's. |
| M47 | `tools/resolve.py` | 213 | The identity pass (`reads_of`, `contacts`, `resolve`, `signal`, `run`). The labels file read (`load_labels`). The same pass over a csv from a command line (`tables_of`, `rewrite`, `main`). |
| M48 | `tools/inrange.py` | 95 | The mask (`run`). A colour settings file read (`load_bounds`). The card: six sliders and Load (`settings`, 39 lines). |
| M49 | the other 33 tools | 1,876 | Each its facets, its computing, a `settings` of `ParamWidget` rows and, in 23, a launcher. A plane out: `gray`, `hsv`, `rescale`, `threshold`, `motion`, `morphology`, `combine`, `mask`, `background`, `bg_subtract`, `box_bandpass`, `top_hat`, `changeenergy`, `flow`, `speed`, `agreement`, `coarsegrain`. A table out: `blobs`, `detect`, `filter`, `attach`, `sample`, `decode`. Tracks out: `track`, `kinematics`, `tracks_filter`. A signal out: `reduce`, `count`, `size`, `spacing`, `travel`, `transitions`, `smooth`. |
| M50 | `tools/retired/` | 185 | Three tools set aside, which the registry does not list (`blobs_to_mask.py`, `crop.py`, `inside.py`). |
| M51 | `utilities/geometry/shapes.py` | 254 | The four kinds as values, each edited by returning another (`Circle`, `Rect`, `Polygon`, `form`, `placed`, `next_name`). |
| M52 | `utilities/geometry/editor.py` | 422 | The drawing's state and the gesture under way (`Editor.press`, `move`, `release`). Stamp groups (`Editor._regrouped`, `set_link`). A shape held within the plate (`Editor._clamp`, `_held`, `_limited`). Undo and redo, a stack of the shapes at each step's end (`Editor._commit`, `undo`, `redo`, `_step`). |
| M53 | `utilities/geometry/document.py` | 131 | The geometry file written and read (`save`, `load`, `to_json`, `Source`). A shape's kind inferred (`_rect`, `_inferred`, `_as_drawn`). |
| M54 | `utilities/geometry/library.py` | 73 | The kept configurations (`listed`, `keep`, `rename`, `remove`, `refusal`, `default_folder`). |
| M55 | `utilities/geometry/view.py` | 228 | The frame, zoomed and panned, with the shapes painted over it (`FrameView`). |
| M56 | `utilities/geometry/table.py` | 96 | The shapes' table (`ShapeTable`, `row_texts`, `size_text`). |
| M57 | `utilities/geometry/window.py` | 524 | Building the widgets (`GeometryWindow.__init__`, 184 lines). The file: open, save, what differs, the ask before leaving (`open_file`, `save`, `save_to`, `differs`, `ask_unsaved`, `_leaving`). The library's asks (`ask_keep`, `ask_rename_kept`, `ask_remove_kept`). The video opened and sought (`open_video`, `seek`, `clock`). |
| M58 | `utilities/geometry/look.py` | 185 | The grays, the sheet and the glyphs (`STYLE`, `styled`, `layer`, `gray`, `glyph`). Widgets (`GlyphButton`, `ElidedLabel`, `Panel`, `label`). |
| M59 | `utilities/geometry/video.py` | 57 | A video read a frame at a time by index (`Video`). |
| M60 | `utilities/__init__.py`, `utilities/geometry/__init__.py`, `__main__.py` | 40 | The command line (`__main__.py:main`, `parser`). |
| M61 | `main.py` | 16 | The player on the newest document noted, or on the example chain. |
| M62 | `smoke.py` | 159 | The player run with no screen and its state asserted, a graph and then a window (`run_graph`, `run_window`, `check`). |
| M63 | `bench.py` | 76 | A graph timed with no Qt (`fill`, `fresh`). |

### What a tool spends its lines on

From `python -X utf8 docs/findings/experiments/2026-11-16-what-a-tool-spends-its-lines-on.py`,
which gives each top-level statement's lines whole to one column: a function named `settings`, or
`widget` in `_csvfile.py`, is the settings widget, and every other function but `draw` computes.

| | files | lines | docstring | imports | facets and constants | settings | draw | launcher | computing | blank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| the tools | 38 | 2,914 | 356 | 90 | 177 | 495 | 39 | 193 | 1,101 | 463 |
| the median tool | | 54.5 | 8 | 2 | 4.5 | 7 | 0 | 7 | 18 | 10.5 |
| what they share | 5 | 672 | 43 | 20 | 21 | 94 | 14 | 0 | 392 | 88 |
| retired | 4 | 185 | 30 | 7 | 13 | 20 | 2 | 14 | 66 | 33 |

Over the tools, 495 lines build a settings widget and 1,101 compute; with the Write card in
`_csvfile.py`, 589 and 1,493. The 495 are not spread evenly. `region.py` has 175, `file.py` 44 and
`inrange.py` 39, each a card with buttons and a state of its own, and the other 35 have 237, a
median of 7: an import, a `ParamWidget` and a row a knob. In those a `settings` line holds what
nothing else in the file does, the knob's range and its kind of row, and reads its default from
`DEFAULTS`. The launcher is 193 lines in 28 of the 38.

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

None of these is put forward to be moved for lying where it does. Kendrick, of F01: such a thing
is usually no problem until it is, and what makes one hellish to undo is its being built upon. So
each is one to watch, and what turns it is a second thing built on top of it.

- H1. W12: the frame is the one painted surface with no module. None traced.
- H2. W14: `held.py`'s opening says "the window says when a run is held and written", and the
  window's eleven names are that rule. F08, the rule a result is kept or let go by (`b390c121`,
  `988d2530`).
- H3. W13: the loaders' memory (`_taken`, `_driven`) and a file watcher live on the window. F01:
  "the document named the second video and the player had the first open" (`8a08c367`).
- H4. W15: `bare.py`'s opening lists the lines its process says, and their one reader is
  `window.py:PlayerWindow._bare_said`. None traced.
- H5. W17: `Lateness`, whose docstring argues why it is here and not in the probe. None traced.
- H6. M05 for S8, by way of M24: the decoder keeps a table of frame times in the store and learns
  where the store is from a module global, `decoder.py:STORE`, which only
  `window.py:PlayerWindow._open_video` assigns. `bare.py`, `smoke.py` and `bench.py` never do, so a
  `Decoder` there keeps no table and reads none kept. F07 is the table's class (`023c46ce`); that
  the bare walk pays for it is this session's reading of the code and was not measured. The bare
  walk being what he measures the player against (M08), a decoder there that is not the player's
  in this weighs more than its place in this list says.
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
- H14. M43 for S8: how the store is laid out for cut files, which of them nothing uses and how one
  is deleted are a tool helper's (`_cutfile.py:folder_for`, `landed`, `unused`, `delete`), and
  every caller is in M44. F18, "the replace over a clip another region had open was
  refused and the whole encode lost" (`eb973068`); F22 has `_cutfile.py` twice among where it
  landed.
- H15. M44 for S8, S15 and no owner: 175 of `region.py`'s 495 lines are a card that shows a long
  job's progress and cancels it, sweeps the store and starts another program. F10, "file.py and
  region.py each carried the same forty lines of list set-up" (`50d07ce7`).
- H16. M44 and M53 for one file: the geometry JSON has two readers that share no code,
  `region.py:load_geometry`, which the utility's README calls the live statement of what the file
  may hold, and `utilities/geometry/document.py:load`. They differ: the utility takes a plate of
  `true`, a bool being an int to its check, and region refuses one. None traced.
- H17. M39 for S4 and S7: what lies on a `blobs` or a `tracks` wire is defined under `tools/`, and
  the player knows it by its shape, `graph.py:nbytes` walking a dtype's object columns and
  `graph.py:gated` and `walk.py` reading `"rows"`. F06, "the memo counted a table at its pointers"
  (`e9142899`); F17, "a table's rows of differing length read as the graph changing shape, and the
  walk started over forever" (`cd887844`).
- H18. M47 for no owner: `resolve.py:main` is a command that runs a tool's pass over a file with
  no player, the one such in the tree, and it reads the csv back through `_csvfile.py:read` to do
  it. None traced.
- H19. M59 for S5: `utilities/geometry/video.py:Video` is a second reader of video with its own
  answer to where a seek lands (`EXACT_DECODE_BELOW`), and `_cutfile.py:Cut.__init__` a third, for
  the container's count alone, which F07 found a container to misstate (`925f03fa`) and which
  here only scales a progress bar. None of F07's sixteen commits touched `video.py`, and of the
  two that touched `_cutfile.py`, `020ccd0a` wrote it and `27fb7e04` changed what it deletes
  (`git show --stat` of each). The utility's docstring says a seek "may land near the asked
  frame", which a shape drawn on a still plate does not mind.
- H20. M58 for M31: `look.py` copies the player's grays and `GlyphButton` by value, on purpose by
  its own docstring. The ledger read `c14271d9` back out of F10 as a copy made and not one found.
- H21. M62 and M63 for `tests/` and S9: `smoke.py` asserts on the window's state and reads
  `win.worker._gen` and `win.display._over`; `bench.py` reads `dec._cache`, and `stats.py` (M18) is
  there for it alone. Neither was run in the reading. None traced.

H10 to H13 are a helper living where it was first needed; none has a class.

## 5. What was built by attrition

Over the whole tree, each place read where it lies. Attrition, by the spec, is a thing written more
than twice whose copies have drifted or which a fix in the ledger had to reach in more than one
place. A1 and A6 were drawn and searched for over every Python file, the pattern beside each; the
search found four places of A1 and one of A6 that the list had not, and they are in it now.

### Attrition

- A1. A file written whole or not at all (`open\([^)]*"(w|wb)"|os\.replace|os\.rename|mkstemp|
  write_text|json\.dump\(`). With a part file and a replace: `document.py:save`,
  `held.py:File.write`, `recent.py:note`, `decoder.py:_keep_times`, `tools/_csvfile.py:replace`,
  and `tools/_cutfile.py:Cut._land` for a clip's sidecar, the clip itself taking its name by a
  rename that refuses a name already taken (`_cutfile.py:take_name`). Written in place:
  `store.py:choose`, `ledger.py:save`, `trace.py:to_trace`, `bare.py:main` for the walk's results,
  `window.py:PlayerWindow._start_bare` for its job, `dev/reference/icons.py`, and
  `utilities/geometry/document.py:save`; `trace.py:Dump` and the log of `dev/console.py` are
  streams and are neither. Both tests hold. `929f1614` (F18, F10) took the leftover
  part file out of two copies, `document.save` and `_csvfile.replace`. And they have drifted:
  `recent.py:note` still passes on `OSError` and leaves its `.part`; `_keep_times` and `Cut` make
  a part by `mkstemp` and the rest by a suffix; `File.write` clears in a `finally` and the rest in
  an `except`; `document.py:save` passes no `newline` where the recent list, the store's choice, a
  csv and a geometry file pass `"\n"`, and the eight documents lying directly in `video-tests/`
  are CRLF at every line and the five geometry files there LF, by a count of each file's bytes;
  and the geometry file, the one of these the user draws by hand, is opened for writing where it lies,
  so a write that fails leaves it cut short.
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
  own count. Whether the channels have drifted in what each says was not read. A tool adds two
  channels more: what its computing raises, which reaches a node's standing, and a readout on a
  card of its own, of which `region.py` has three (`status`, `launched`, `clip`) and `inrange.py`,
  `_csvfile.py:widget` and `file.py` one each.
- A4. A store bounded by bytes: `graph.py:Memo`, the decoder's cache (`decoder.py:Decoder._put`,
  `_trim`), `held.py:Runs.hold`, and a walk's stack (`walk.py:_fits`). What each lets go first
  differs on purpose and is no drift. What was fixed apart is the counting: F06's four commits
  coming back are the decoder's (`75212615`), the memo's (`e9142899`, `a639e63e`) and the stack's
  (`982ea14d`).
- A11. What a param is. A tool says it in up to four places: `DEFAULTS`, which the registry and
  the document read; its row in `settings`, where alone its range and its kind of row are; a check
  where it is computed; and a fallback where it is read. They have drifted. `outline` is read by
  nine `draw`s as `params.get("outline", "box")` and is declared and offered by four
  (`attach.py`, `blobs.py`, `filter.py`, `track.py`); in `decode.py`, `kinematics.py`,
  `resolve.py`, `sample.py` and `tracks_filter.py` nothing declares it, so no document holds it
  and those five draw the box whatever the table carries. Of seventeen checks of a choice
  (`raise ValueError\(f".*no (method|mode|stat|kernel|property|signal|dictionary|precision)`),
  fourteen name the tool and list the choices, `morphology.py:morph` and `combine.py:combine` do
  neither, and `_blocks.py:reduce_blocks` lists them and names no tool. A range is a number in a
  `settings` line that the computing does not hold: `top_hat.py:top_hat` checks its radius and
  `box_bandpass.py:bandpass` that `outer` exceeds `inner`, three clamp a number
  (`smooth.py:run`, `_blocks.py:reduce_blocks`, `retired/crop.py:rect`), and the rest take what
  they are handed. And three tools
  carry a fallback for a param a saved document may lack, two by restating the default
  (`box_bandpass.py:run`, `"16 bit"`, from `4685285c`; `track.py:_knobs`, `0.0`, from `06c60b5f`)
  and `region.py:clip_of` and `cut_file` by reading `DEFAULTS`, which is a job
  `document.py:Document.resolve` does for every param of every tool by laying a node's over
  `DEFAULTS`; which was written first was not looked up. Ledger: F17's `64ce8f59`, where a tool's
  own list of a param's choices, `MODES`, was read as a facet.
- A12. A bound typed as text, blank for none. `d113c8bb` (F10) made `filter.py`'s and
  `tracks_filter.py`'s identical `bound()` one, `_table.py:bound`. A third stands,
  `transitions.py:_value`, which answers None where `bound` answers a default.
- A19. What a kept thing is good under. Six places answer it: `plan.py:_key` for a node's
  result; `tools/_cutfile.py:key` for a cut clip; `tools/_csvfile.py:key_line` for a csv;
  `held.py:stamp` for the held file; `decoder.py`, for a table of frame times, by two prints of a
  file, `footage_print` and `footage_print_by_stamp`; and `window.py`'s memory of what a path
  loader last read, by path and mtime. One difference was met: the csv's line names its footage
  by the file's name where the others name it by its print. The six were found by a search while
  the ledger's classes were read with Kendrick and were not read whole, and what else differs
  among them was not looked for. F05 is the class, the one he feels most.

### Copies left alone

- A5. An optional method looked for on a settings widget, by `hasattr` at ten sites:
  `pane.py:Pane._build` (3), `Pane.set_cut_files_in_use`, `Pane.set_source`,
  `window.py:PlayerWindow._pick_paths` (2), `_note_selectors`, `goto`, `_series_ready`. It was
  attrition, and `997700a3` (F17) answered it by writing the eight names once, as
  `registry:WIDGET_FACETS`; the sites stand as they were and the names agree.
- A6. Whether a result is a series result, `isinstance(r, dict) and "signal" in r`: four times in
  `window.py` (`_series_ready`, `_whole`, `_clip_result`, `_show_pinned`), three in `held.py`
  (`good`, `Runs.hold`, `per_row`), once in `graph.py:gated`, and over two lines in
  `tools/csv.py:count` (`"signal" (not )?in`). No drift found, no fix traced.
- A7. The tools as a mapping of name to module: `document.py:_by_name`,
  `graph.py:Graph.__init__`, `window.py:catalogue`. The same line three times.
- A8. A line on stderr that opens `SIEVE` and the time, formatted where it is printed:
  `window.py` 3, `ledger.py` 2, `dev/timeview.py` 1. `dev/console.py` owns where stderr goes and
  not what a line of it looks like.
- A9. Whether two paths are one file, by `normcase`: `window.py:_same` and
  `tools/_cutfile.py:_same` over `abspath`, `recent.py:note` over paths it made absolute. The
  `normcase` in `tools/file.py:select` compares a name with the `choice` and is not this.
- A10. A thread with its own handoff, six ways: `worker.py:Worker` on a condition,
  `trace.py:Dump` on a list taken each period, the window's writer of the held file as a thread a
  write, `machine.py:Watch` on a period, `decoder.py:read_frame_times_ahead` as a daemon, and the
  ledger's queue drained by whoever reads. These are not copies, and F02 and F03 were not read
  against them by hash; they are listed so that the candidates' session does. A child process is
  held three ways beside them: the bare walk as a `QProcess` whose lines are read
  (`window.py:PlayerWindow._start_bare`), ffmpeg as a `Popen` polled by a card's timer and killed
  at exit (`tools/_cutfile.py:Cut`), and the utility as a `Popen` nothing waits on
  (`tools/region.py:launch`). F22 has `_cutfile.py` twice among where it landed.
- A13. A tool's launcher, an `if __name__ == "__main__"` block that plays the tool after the
  tools that feed it: 28 of the 38, 193 lines. Ten have none (`attach.py`, `combine.py`,
  `decode.py`, `hsv.py`, `kinematics.py`, `morphology.py`, `sample.py`, `spacing.py`,
  `tracks_filter.py`, `transitions.py`), and `resolve.py`'s is its csv command and plays nothing.
  No fix traced.
- A14. A comma-separated list of columns read from a text knob: `names(text)`, the same line in
  `attach.py`, `resolve.py` and `retired/inside.py`.
- A15. `run` as a loop over `step`: `count.py`, `size.py`, `transitions.py` and `travel.py`, the
  last two the same five lines. The registry's README names `run` the oracle a `step` is held to.
- A16. A card of its own: four subclasses of `ParamWidget` named `_Widget` (`file.py`,
  `inrange.py`, `region.py`, `_csvfile.py:widget`), each a button, a readout for what came of the
  press and, in three, a file dialog. It was attrition: `50d07ce7` (F10) took forty lines of list
  set-up out of `file.py` and `region.py` into `widgets.py:ChoiceList`. No drift read in what is
  left.
- A17. A time as text: `pace.py:clock` (m:ss), `timeline.py:timecode` (mm:ss.fff) and
  `utilities/geometry/window.py:clock` (m:ss.fff), three formats for three readouts.
- A18. The player's look, written again by value in `utilities/geometry/look.py` (H20).

Written twice and so not listed: a series as min and max a column (`plot.py:Plot._columns`,
`timeline.py:envelope`); naming a read as a seek, a decode or a cache's (`graph.py:Graph._compute`,
for the video and for a served file); a drawer's or a loader's params put through the widget when
there is one and to `_params_changed` when there is not (`window.py:PlayerWindow._picked`,
`_pick_paths`); the geometry file read (H16); the ask before unsaved work is left
(`window.py:PlayerWindow`, W10, and `utilities/geometry/window.py:GeometryWindow._leaving`); the
video files a dialog offers (`pane.py:VIDEO_FILTER` and `utilities/geometry/window.py:VIDEO_FILTER`,
which differ by `.m2ts`); an id's records in two consecutive tables, by `np.intersect1d`
(`travel.py:steps`, `transitions.py:changed`); a moment ellipse (`_table.py:moments`, and
`detect.py:find` over every region at once).

Three things the reading met that are neither. The string under `window.py:Display`'s two signals
is written as a docstring and is not one, the signals coming first, so `Display.__doc__` is None.
`window.py:catalogue` is a function named as the module `catalogue.py` is, which `window.py`
also imports from. And `README.md` says, beside `tools\motion.py [video]`, "any tool runs alone",
where ten of the 38 have no launcher (A13).

## 6. The assessment

### The systems SIEVE has

How sound is this session's reading of part 4 and of where the ledger's fixes landed. Built or
arrived at is read from the same and from the commits part 4 cites, and not from each module's
history, which was not read.

| | system | how sound | built or arrived at | verdict |
| --- | --- | --- | --- | --- |
| S1 | The document | Sound: one owner, nothing writes round it. It holds six readers of a tool's facets for the registry (H9), and no history of its changes. | Built. | Keep. |
| S2 | The registry of tools | Sound in what it finds; read round by six modules (A2). | Built, its README being its spec. | Build, E1: the one reader. |
| S3 | The plan and the keys | The soundest: pure, printed as a table, nothing round it for a node's result. Five places more answer what a kept thing is good under (A19). | Built. | Build, E1: it is what E1 builds on. |
| S4 | The runtime | Sound for a result; holds the band, the count of bytes and the stream's pass-throughs for others (H7, H8). What the overlay reads is taken and not said. | Arrived at, in part. | Keep; build E3's first part. |
| S5 | The decoder | Sound since `023c46ce`; learns where the store is from a global the window alone sets (H6). | Built, and built again. | Keep. |
| S6 | The walk and its thread | One walk under three drivers, after `59ce234f` made two copies one. F02, F03 and F21 are its classes. | Arrived at. | Keep; E2 adds a driver, and E3's second part is watched. |
| S7 | The held results | Split: the runs and the file in `held.py`, the rule of when in `window.py` (H2). | Arrived at. | Keep, and H2 is watched. |
| S8 | The store | Small and sound; what a file in it is named is its writers' (H14). | Built. | Keep. |
| S9 | The stream and its readers | Sound and large; Kendrick finds a hang by it. Four of its names have no caller found (C12). | Built, most of it in a day (F20). | Keep. The parts with no caller are a deletion that waits on a search of `tests/`. |
| S10 | The interface | The widgets sound, each knowing nothing of the runtime. `window.py` holds 553 lines of other owners' jobs. | Arrived at. | Keep; E4 watched. |
| S11 | Launch and diagnostics | Sound. A launch that did not end cleanly leaves no mark. | Arrived at. | Keep. |
| S12 | The icon reference | Read by nothing of the player. | Built. | Kendrick's: a deletion, cut from the entries. |
| S13 | The tools | Sound one by one; a setting is said in up to four places (A11). | Arrived at, tool by tool, by design. | Build, E1: a setting declared once. |
| S14 | What tools share | Sound; two of the five were made by fixes (F10). The table kind lies here and the player knows it by shape (H17). | Arrived at. | Build, E1: the wire kinds. |
| S15 | The geometry utility | Sound, and a program of its own. Its file has two readers that differ (H16), and is written where it lies (A1). | Built. | Keep; the write is a fix. |

### What to build

Sorted by the order argued below. A score is this session's, with its reason, and is the first
thing here to disagree with. Counts are of the candidates' commits in part 3, told apart by how
the ledger files each.

| | what | to Kendrick's work | to development | prevented | made cheaper | what it takes | its cost grows with |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | What a tool declares, and the key made of it | 7: a wrong result served is the worst a key can do and a result made again is felt daily, but no result is out of reach | 9: paid by every new tool, in the four places a setting is said, and by every new store | 3: `cce7cb8e` came back; `cd887844` and `64ce8f59`, in part, settling | 11: seven came back (`d30bd9f0`, `7f0a645d`, `4079a72d`, `391bddd9`, `be59a820`, `e9142899`, `ba71e6f5`), four settling (`eb973068`, `00fd8c19`, `2216f272`, `997700a3`) | Every tool touched and the readers of three modules moved: of the order of S14 and S2 together, by this session's guess and no count | The tools written; and, for the step that changes keys, the held files and documents saved |
| E2 | A pipeline run over pieces of footage | 9: results he now gets one piece at a time by hand; not 10, a hand's loop being possible | 3: it adds a way to run and removes no cost of writing a tool | none, by its nature | none | Not sized. At the least what the bare walk is, M08 and W15, 160 lines, again, and a tool; the half in time reaches the plan and the walk | The count of files in a study |
| E3, its first part | The overlay's ask said as the plot's is | 3: a draw he wants and cannot easily make wanted | 2 | none of its own; C6 whole has `98e65cac`, came back, and `3bd2d8d1`, which touched no earlier line | none of its own; C6 whole has three that came back (`5c095255`, `e9142899`, `fbf4fab7`) | A method and its caller | Nothing |

No entry's verdict is shrink, the three candidates for it having been cut to deletions.

### Watched

- E3's second part, an ask as a value in a set the ladder reads. Watched because the ladder has
  four rungs and its fixes are in. E2 turns it: a walk with no window is a reader with no rung.
- E4, one place a failure is said. Watched at Kendrick's word, an ideal worked towards and no
  priority. The next commit the ledger would file under F04 turns it, or E2, a run with no
  window having nowhere but stderr to say a failure.

No entry's verdict is leave. What was left is in part 3 under The cut and Traced to none.

### The order

First, E1's three steps that change no key: the registry as the one reader, a setting declared
once, the wire kinds in one table. They come first because everything else in the table reads
what they make, because development pays for their absence at every tool, and because they are
the one build here that can be shown right exactly, `--plan` printing the same table over the
nine documents before and after. Then the count of settings no `run` reads, and A19's six read
whole, which say whether E1's fourth step, the marks, is worth a change of keys. Then the
question that is Kendrick's, whether a bout walked alone is to equal the same rows cut from a
walk of the whole clip, and E2 after it, with E3's first part whenever a hand is near it. Left:
E4, and E3's second part, until E2 asks for them.

What would make E1 the wrong first. Not the count of settings no `run` reads: it sizes the marks
and nothing else of E1, and is three
(`docs/findings/2026-11-16-which-settings-no-run-reads.md`). E1's worth to his work is that one
key answers what is still good for every kept thing and every job, where the held file, a bare
walk and a csv each answer by a rule of their own, and a result let go for no reason he can see
is what he feels. That the experiment's data is wanted sooner than E1 can be shown right, which
is his to say and nothing here measures. Or that a step said to change no key cannot be made
without changing one, which the first run of `--plan` would show.
