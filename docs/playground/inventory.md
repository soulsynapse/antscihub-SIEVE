# Inventory: what holds, keys and must be told of a result

Stage 1 of `docs/playground/JOURNAL.md`, read off the tree at `bbf29887` on `v5-playground-one-store`
(whose `sieve_player/` and `tools/` are `v5`'s at `b23ff2c4`). Every row was read from code; where
`docs/systems-review.md` says otherwise it is listed in the last section. "GUI" is the Qt main
thread; "worker" is `worker.py:Worker`'s thread.

## 1. What holds a computed or decoded thing past the call that made it

### In memory, gone with the process

| Where | Holds | Key, and who makes it | Writer | Reader | Size bound | Stale when, decided by |
|---|---|---|---|---|---|---|
| `graph.py:Memo` (`Graph.memo`) | a frame node's output at a row, or a `graph.py:Ref` to another store's array; a plane's density fold | `(raw_key, row or None, cut.read edges)` by `graph.py:_address` over `plan.py:Entry.raw_key`; a fold under `plan.py:_key(raw_key, "fold")` | `Graph._compute`, `Graph.density` (worker) | `Graph._compute`, `Graph.peek` (GUI), `Graph._held` | `memo_bytes`, counted by `wire.nbytes(produces)`; pinned entries count but are never evicted, so the limit can be passed | never per entry: a key the plan left is ranked to go first by `Graph._memo_order`; `Memo.unpin` at `Graph.sync` drops static entries whose owner left; `Graph.empty` at `window.py:_unload` |
| `graph.py:Memo._pinned` | a STATIC node's one value a cut | as above with row None | `Memo.put(owner=raw_key)` | as above | none of its own: outside eviction | its owner key absent at a sync (`Memo.unpin`) |
| `decoder.py:Decoder._cache` | the plate's decoded frames, read-only | row, by the caller; the output in force (`Decoder.output`) is not in the key, a change empties the cache | `Decoder._hand` (worker) | `Decoder.read`, `Decoder.cached` (GUI via `Graph.peek`) | `cache_bytes`; one frame stays whatever the limit (`Decoder.cache_limit` setter) | output change, `_TableRetaken`, `Graph.empty`; the Decoder is one file's |
| `graph.py:Readers._held` | a Decoder per served cut file, each with its own `_cache` | path, from `Entry.file` (the tool's `cut_file`) | `Readers.get` (worker) | `Graph._compute`, `Graph.peek`, `Graph._held` | the plate's `cache_limit` shared, latest-read file first (`Graph._reader`) | path no longer served at a sync (`Readers.keep`), closed by `Readers.reap` on the worker |
| `decoder.py:_probe` | (w, h, fps, count) | (path, mtime) | `lru_cache` | `decoder.probe` | 16 entries | mtime moves |
| `decoder.py:_times` | a file's frame-times table | path; stamp (size, mtime_ns) beside it | `decoder.frame_times` (any thread, per-path lock) | `frame_times`, `Decoder` seeks | nothing | stamp moves, or `anew` (the decoder's `_doubt`) |
| `decoder.py:_prints` | a file's footage print | path; stamp beside it | `footage_print_by_stamp` | `_cutfile`, `plan` via `Graph.cut_file`, `_times_file` | nothing | stamp moves |
| `registry/__init__.py:_FILES`, `_IMPORTED` | digests of tool files; the digest at first import | path + stamp; `id(module)` | `_file_print`, `discover` | `code_print`, `imported_print` | the count of tool files | stamp moves; `_IMPORTED` never |
| `walk.py:_Walk.stacks`, `.stepped`, `.dens`, `.folded` | a range's walked rows, stepped state and results, plane densities, each head's folding | walked node; fold by `id(fold)` with the buffer held | `_Walk.turn`/`step` (worker; `bare.py:main` on its own thread) | `run_chain`, the walk's own emits | `walk.py:STACK_BYTES` each, refused past it (`_Walk.refuse`) | `_Walk.begin`/`drop`; `stale_given`; a leg restarts when `worker.py:_stacked` moves |
| `worker.py:Worker._held_periods` | a `walk.py:HeldCut` per cut in time | (walked node, (first, end)), by `heldwalks.py:held_periods` | `Worker.give_periods` (GUI) | `Worker._held` → `_Legs._ask` | the count of cuts | replaced whole; checked against `walk.py:period_keys` |
| `held.py:Runs` (`window.py:PlayerWindow.runs`) | `Run`s: a walk's chain results over a range, inside a cut, with walked stacks | per node `result["key"]` (stamped by `walk.py:run_chain` from `Entry.key`) compared by `held.py:good`; the run's span and cut, read through `cut.read` with the node's reach | `PlayerWindow._hold_run` (window, clip, period and bare results) | `over`, `part`, `walked_rows`, `listed`, `spans`, `from_first_row`, `beside`; `heldwalks.py` (incl. `gate_result` for `plan`'s `cut_result`) | `window.py:HELD_BYTES` by `wire.result_bytes`; the last run held stays whatever it takes | a key mismatch is not served and is let go first under the limit (`Runs.hold`); a tool-code change is not stale here: `held.marked` only flags the card (`PlayerWindow._show_stale`) |
| `window.py:PlayerWindow.results`, `clip_results`, `window_periods`, `_of_cuts` | the last chain results shown, of the window, the clip, the periods the window overlaps | node; `clip_results` checked by `held.good` in `_clip_result` | `_series_ready`, `_clip_ready`, `_window_period_ready`, `_show_held` | the plot, cards, `_write_held` | nothing of their own | replaced on the next result; `_unload` |
| `window.py:PlayerWindow._taken`, `_driven` | which file a path loader last read, its mtime, the params it set | (node, path input) | `_pick_paths` | `_pick_paths`, `_watch_taken` | the count of path inputs | stamp moves; cleared on a new document |
| `ledger.py:Ledger` | the stream as buckets, walk records, discards | bucket index of `t // width`; `WalkId`; (key, row) | `Ledger.event`/`sample` queue, folded by `view()` or the emitter | `window.py` header, `pace.py`, `dev/timeview.py` | `history=2400` buckets of `width=0.25` s, `walks=64`, `discards=1<<17`, `BACKLOG=4096` | aged out; one Ledger per open video (`_open_video`) |
| `stats.py:Stats` | per-node last and mean ms, walk rate | node | `Stats.event` | `bench.py` | `WINDOW=64` | running |
| `tools/_table.py:_plane_dtype` | dtypes | (h, w, dtype, units) | `lru_cache` | tools | 64 | never |
| card widgets, e.g. `tools/_csvfile.py:widget._Widget.result` | the last result shown to a card | none | `show_result`/`show_listed` | the card | nothing | next show; not determined for every card |

### On disk

| Where | Holds | Key, and who makes it | Writer, and how it lands | Reader | Size bound | Stale when, decided by | If deleted while closed |
|---|---|---|---|---|---|---|---|
| `<document>.series`, `held.py:File` at `held.py:path_for` | the held runs, pickled, after `STAMP = (VERSION,)` | per run as `Runs`; the file is the document's path | `window.py:_save_held` on a thread named `held`, after `HOLD_MS` of rest, on save and at `_unload`; appends in place (`r+b`, truncate, dump) when the file holds only runs still held, else rebuilds at `{path}.part` and `os.replace` | `File.load` in `_open_video` | what `Runs` holds (in-memory count; pickled size differs, `held.per_row`) | `VERSION` differs → loads as none, silently; reading stops at the first bad record | runs gone, walked again; a `period` cut by a gate cuts nothing and "waits on" the gate's walk (`plan.py:cuts_of`) |
| `<store>/frame-times/<print>.npy` (`decoder.py:TIMES_DIR`) | a file's frame-times table | `footage_print_by_stamp`: size, first and last MB | `decoder.py:_keep_times`: `mkstemp` + `os.replace` | `frame_times` | nothing | never; taken on trust, retaken `anew` on disagreement | packets re-demuxed at next first seek (`read_frame_times_ahead`) |
| `<store>/<print>/<label>-<key>.mp4` and `.json` sidecar (`tools/_cutfile.py`) | a cut clip and what it holds, its byte size | `_cutfile.key(footage, extent, recipe)` | `_cutfile.Cut._land`: unique `mkstemp` `.part`, `take_name` (rename that refuses a taken name) | `tools/region.py:clip_of` → `cut_file` → `plan.file_of` → `Graph.Readers` | nothing; the user deletes from the region card (`_cutfile.unused`, `delete`) | never; `_cutfile.whole` checks size against the sidecar | `region` with `serve clip` on: `cut_file` raises FileNotFoundError, the node and all below are not fed (`Graph.cut_file`, `plan.py:file_of`); nothing recomputes them |
| `%TEMP%` `.progress` report and log of a Cut | ffmpeg progress | none | `Cut.__init__` | `Cut.progress` | one per Cut | — | removed by `Cut._clear` |
| a csv (`tools/csv.py:write`) | a series result as rows | its first line, `_csvfile.key_line`: plan key, rows, footage print, kind | the card's Write, `_csvfile.replace`: fixed `{path}.part` + `os.replace` | the card (`written_key`: "this graph's" or "stale"); `tools/resolve.py:rewrite` CLI | nothing | the card compares the line's key with the result's | nothing in the player reads it back |
| a periods JSON (`tools/period.py:periods_text`) | a gate's periods | none (no key line) | the period card's Write, `_csvfile.replace` | `period.load_periods` through a `file` selector | nothing | not determined | a `period` fed it has no file to read; standing not determined |
| `%TEMP%/sieve-bare-*/job.json`, `results.pkl` | a bare walk's job and chain results | the folder `mkdtemp` makes | `window.py:_start_bare`; `bare.py:main` (plain `open`) | `bare.main`; `PlayerWindow._bare_said` | nothing: no code removes the folder | `stands(_bare_keys)` at read | nothing |
| `SIEVE_DUMP` file (`trace.py:Dump`) | every stream event | the path the env names | `Dump` writer thread, `open("w")` | `trace.read_dump`, `ledger.replay`, `report.py` | nothing | overwritten at each video open | — |
| a saved ledger history (`ledger.py:save`) | a view's buckets and walks, JSON | the path chosen | `dev/timeview.py` alone | `ledger.saved` | nothing | none | — |
| `stderr.log`, `.prev.log` (`dev/console.py`) | stderr | `SIEVE_LOG` or `app_folder` | `log_stderr` | the user | one launch and the one before | — | — |
| `recent.txt`, `views.json`, `store.txt` under `recent.py:app_folder` | recent documents; each document's selection and window; the store's folder | path | `recent.note`, `recent.keep_view` (fixed `.part` + `os.replace`); `store.choose` (plain write) | `recent.entries`, `view_of`, `store.chosen` | `KEEP=10`, `KEEP_VIEWS=100` | — | the document opens at row 0 with no selection; the store falls back to `SIEVE_STORE` or the default |
| the document JSON (`document.py:save`) | params, wires, flags, `pinned` (the plot's list) | path | fixed `.part` + `os.replace` | `document.load` | — | — | — |

## 2. What decides how much memory, how many threads and processes, how much disk

| Rule | Value | What it knows of the machine |
|---|---|---|
| `decoder.py:Decoder(cache_bytes=)` | `4 << 30`; `window.py:CACHE_ENV` (`SIEVE_CACHE_GB`) overrides | nothing |
| `graph.py:Graph(memo_bytes=)` | `4 << 30`; `window.py:MEMO_ENV` (`SIEVE_MEMO_GB`) overrides | nothing |
| `graph.py:Graph._reader` | served files share the plate's `cache_limit`, the latest read may fill it | nothing |
| `walk.py:STACK_BYTES` | `512 << 20` per `_Walk`; `worker.py:Worker` makes four (`_win`, `_clip`, the two `_Legs` walks), each its own bound | nothing |
| `window.py:HELD_BYTES` | `512 << 20` for `Runs` | nothing |
| `bare.py:HOLD` | `64 << 20` each for the bare process's memo and cache; its walk under `STACK_BYTES` | nothing |
| `graph.py:NEAR`, `decoder.py:CLEAR` | 8 rows kept back; a sixteenth of a limit cleared at once | nothing |
| `held.py:COPY`, `held.py:SAMPLE` | 1 MB copy chunk; 256 rows pickled for `per_row` | nothing |
| `ledger.py` (`BACKLOG`, `history`, `walks`, `discards`) | 4096, 2400, 64, `1 << 17` | nothing |
| `tools/background.py:MAX_SAMPLES`, `tools/resolve.py:MAX_READS` | 200 frames composited; 1000 | nothing |
| tool threads: `worker.py:Worker` | one QThread runs every tool, scrub and walks in turn | nothing |
| decode threads: `decoder.py:_open` | `stream.thread_type = "AUTO"`: FFmpeg chooses its own count | FFmpeg's own core count |
| OpenCV, numpy/BLAS threads | not set anywhere in `sieve_player` or `tools` | their libraries' defaults |
| other threads | `machine.py:Watch` (1 s), `trace.py:Dump` writer, the `held` writer (one at a time, `_write_held`), one `frame-times` thread per open (`read_frame_times_ahead`) | nothing |
| processes | one bare walk at a time (`PlayerWindow._bare`); one ffmpeg per `_cutfile.Cut`, a Cut per region card, none capped across cards; ffmpeg gets no `-threads` (`_cutfile.command`) | nothing |
| disk | no rule bounds the store, the held file, frame-times or bare folders; `store.probe` checks writability only; `store.held`/`store.disk` are read for `storecontrol.py` to draw | `store.disk`: free and total of the store's disk, drawn, never used to decide |
| `machine.py:Machine.read` | psutil memory, cores, disk, GPU | read for the monitor alone; no limit reads it |

Defaults summed: 4 GB memo + 4 GB caches + 2 GB of stacks + 0.5 GB held, plus pinned memo entries and the last held run past their limits, with nothing read off the machine.

## 3. What a tool, or a new kind of result, must do or be registered with

| Obligation | Imposed by |
|---|---|
| `SIEVE_TOOL = True` and a string `NAME`, in a file `discover` reads, stem not beginning `_` | `registry/__init__.py:is_tool`, `discover` |
| imports only `wire`, `decoder`, `held`, `store`, `theme` and `ParamWidget`, `play`, `document` of the player, and no other tool | `tests/test_seams.py:TOOLS_MAY_IMPORT`, `test_a_tool_imports_what_tools_share_and_never_another_tool` |
| every type it expects or produces is a key of `wire.TYPES`; a new type is added there with `table`, `bytes`, `overlay` | `tests/test_seams.py:test_a_tool_names_types_of_the_wire_table`; `wire.py:TYPES` |
| a new facet is added to `registry._HINTS`/`FACETS` and read only through the registry | `tests/test_seams.py:test_the_registry_alone_reads_what_a_tool_declares` |
| run: `run(frames, row, params)` for a frame tool, `run(series, params)` for a series tool | `graph.py:Graph._compute`, `walk.py:run_chain` |
| run: never writes into its input (the frame is read-only) | `graph.py:Graph._compute` (`setflags(write=False)`); `decoder.py:Decoder._hand` |
| key: params JSON-serialisable; key = sha1 of what it reads, `NAME`, `computed` params or `key_params` | `plan.py:key_of`, `registry.computed`, `registry.key_params_of` |
| key: a param a draw alone reads says `"changes result": False`, or a change recomputes | `registry.computed`; `tests/test_seams.py:test_a_tools_computing_is_never_handed_a_param_declared_to_change_nothing` |
| key: tool code is in no key; an edit is seen only as a card's stale badge over held runs | `registry.code_print` ("no key holds it"); `held.marked`; `window.py:_show_stale` |
| key inside cuts in time: `reach_in_rows`, else both sides unbounded and keyed by both cut edges at every row | `registry.reach_of`, `plan.py:reach_of_node`, `graph.py:_address` |
| keep, frame tool: any value; the memo copies a view or shares a store's array by `Ref` | `graph.py:to_hold` |
| keep, series tool: a dict with `"signal"` of one entry a row, or it is not gated, held, drawn or written | `graph.py:gated`, `held.py:Runs.hold`, `held.good`, `window.py:_show_lines`, `_show_pinned`, `tools/csv.py` |
| keep: a per-row field is an array or list of `rows` items, or `held.rows_of` does not cut it | `held.py:rows_of` |
| keep: the result pickles, or the run is left out of the held file | `held.py:_dump` |
| keep: `key`, `code`, `gate` are the player's fields of a result | `walk.py:run_chain`, `heldwalks.py:as_given` |
| step: `step(state, row, i, params)` whose shares equal `run`, to be stepped | `registry` README; `tests/stepping.py` |
| fold: `fold(row)` shared by heads, else the stack holds rows as they are | `plan.py:shared_fold` |
| draw on the frame: a plane, BGR or (H, W, 2) flow; anything else needs `draw(painter, row, result, start, params)` | `window.py:imageable`, `registry.draws` |
| overlay: only a type whose `wire.TYPES` says `overlay` | `wire.overlaid`, `plan.py:plan` (`over`) |
| card: `settings` or the one built of `PARAMS`; a widget's optional methods named in `registry.WIDGET_FACETS` | `tests/test_seams.py:test_a_settings_widget_is_told_and_says_by_the_registrys_names_alone` |
| count bytes: `wire.TYPES[type].bytes`; a type not there, and any non-array field, counts 64 B | `wire.py:own_bytes`, `nbytes`, `result_bytes`; callers `graph.py:Graph._compute`, `walk.py:_Walk`, `window.py:_result_bytes` |
| table columns: made in `tools/_table.py` with a unit of `wire.UNITS` | `tests/test_seams.py:test_no_column_is_added_under_tools_with_its_unit_unsaid` |
| serve from a file: `cut_extents` and `cut_file(video, footage, params)` answering a path, None, or FileNotFoundError; `cut_files` to be listed; only on the video node or a served node | `plan.py:file_of`, `graph.py:Graph.cut_file`, `Graph._named` |
| serve from a file: written through `tools/_cutfile.py` into `store.folder()`, never over a file a reader has open | `tools/_cutfile.py` header; `graph.py:Readers` docstring |
| cut in time: `cut_extents` answering rows; a `CUT_BY` input reads a held run whole | `plan.py:cuts_of`, `window.py:_cut_result`, `heldwalks.py:gate_result` |
| cut in time: walked only by the worker's `_Legs`; `bare.py:main` walks `p.chain` and never `p.timed` | `worker.py:_Legs`, `bare.py:main` |
| monitor: a tool emits nothing; `Graph.probe`, `_Walk.step`, `run_chain` emit its spans with node, row, key, bytes | `graph.py:Graph._compute`, `walk.py` |
| monitor, a new store: `on_evict` wired to `stream.emit("evict"/"uncache")`, a place in `Graph.progress`'s `"caches"` facts | `graph.py:Graph.__init__`, `Graph._reader`, `Graph.progress` |
| monitor, a new event kind: in `stream.KINDS`, and taken or passed over by every reader | `tests/test_seams.py:test_a_reader_classifies_every_kind` |
| monitor: `Runs` and the held file emit nothing; no kind names them | `stream.py:KINDS`; `held.py` imports no stream |

## 4. Measured coupling: files outside `tools/` and `tests/` that tool additions changed

Chosen as: every first-parent commit on `v5` since 2026-11-01 whose diff against its first
parent adds a `tools/*.py` not beginning `_` and not under `retired/`. All seven are PR merges;
each is measured whole (`git diff M^1 M`), which counts everything its branch carried, not the
tool alone. No wire type was added since 2026-11-01 outside these but by the table's own creation
(`2d6460aa`, PR #31), not counted. PR #22 (region serves cut files, a new kind of result with no
new tool) is listed apart.

| PR (merge) | Tools added | Commits | `sieve_player` files changed | Else outside |
|---|---|---|---|---|
| #8 `5d51726b` | attach, background, bg_subtract, blobs, blobs_to_mask, combine, count, decode, filter, hsv, kinematics, morphology, resolve, sample, size, spacing, track, tracks_csv, tracks_filter, transitions, travel | 70 | `__init__`, `__main__`, `canvas`, `decoder`, `density`, `dev/` (4), `document`, `glyphs/` (2), `graph`, `pane`, `plan`, `registry/` (2), `theme`, `timeline`, `trace`, `widgets`, `window`, `worker` | README, CLAUDE.md, smoke.py, 20 docs |
| #9 `5b96276e` | bake | 19 | `__main__`, `canvas`, `decoder`, `dev/console`, `document`, `graph`, `pane`, `plan`, `registry/`, `store`, `window`, `worker`, `writers` | README, CLAUDE.md, smoke.py, 2 docs |
| #11 `e17fe0fc` | crop, inside, mask, region | 19 | `dev/monitor`, `plan`, `registry/`, `theme`, `widgets`, `window` | README, 4 docs |
| #16 `20d1998c` | crop2, detect | 3 | `bare`, `catalogue`, `dev/` (2), `document`, `ledger`, `registry/` (2), `store`, `window`, `worker`, `writers` | README, 6 docs |
| #26 `d5ee52aa` | box_bandpass | 2 | none | none |
| #27 `0ada0e3f` | top_hat | 2 | none | none |
| #33 `caed48ba` | period | 81 | `__main__`, `canvas`, `cut`, `decoder`, `dev/simulations`, `document`, `graph`, `held`, `heldwalks` (new), `pane`, `plan`, `plot`, `recent`, `registry/` (2), `theme`, `timeline`, `walk`, `window`, `worker` | README, CLAUDE.md, VISION.md, 30 docs |
| #22 `729bbead` (apart) | none; region serves a cut file | 14 | 27 files, among them `graph`, `plan`, `held`, `decoder`, `store`, `stream`, `ledger`, `window`, `worker`, `bare` | README, 11 docs |

Additions (of the seven) that touched each module: `window` 5, `registry/` 5, `dev/` 5, `worker` 4,
`plan` 4, `document` 4, `theme` 3, `pane` 3, `graph` 3, `decoder` 3, `canvas` 3, `__main__` 3,
`writers` 2 (since deleted), `widgets` 2, `timeline` 2, `store` 2, and 1 each `walk`, `trace`,
`recent`, `plot`, `ledger`, `heldwalks`, `held`, `density`, `cut`, `catalogue`, `bare`, `__init__`.

Inside #33, commits touching each module: `window` 26, `walk` 14, `worker` 12, `held` 12, `graph` 12,
`plan` 11, `heldwalks` 11, `registry/__init__` 7, `cut` 6, `registry/README` 4, `plot` 4,
`timeline` 2, `decoder` 2, and 1 each `theme`, `recent`, `pane`, `document`, `dev/simulations`,
`canvas`, `__main__`; its merge diff is 1621 lines added, 325 deleted under `sieve_player/`.

The commit that adds the tool file itself touches little: of the 22 such commits since
2026-11-01, `period.py`'s (`6453ce21`) touched only VISION.md and two docs outside `tools/` and
`tests/`; the runtime work rode the branch's other commits, so the per-commit figure understates.

## 5. The journal's invariants against the tree

| | Held as built? | By what, or why not |
|---|---|---|
| O1 | no | No key holds tool code (`plan.py:key_of`, `registry.code_print`), so held runs made under other code are served after a reopen and only badged (`held.marked`). The footage print reads size and the first and last MB (`decoder.py:footage_print`), so two files differing only between those share every key, frame-times table and clip. Within one process the memo is consistent with the code it imported; `tests/stepping.py` holds step against run, `tests/test_held.py:test_a_range_is_served_from_the_run_that_covers_it_under_the_chains_keys...` holds serving by key. A crash mid-append leaves a cut record that `File.load` stops at. |
| O2 | no | Memo, decoder caches and stacks: yes, a let-go array is recomputed (`graph.py:Graph._compute` on a `Ref` whose store let go; `tests/test_graph.py:test_the_memo_holds_no_view_and_names_another_stores_array_by_reference`). Held runs: no, a `period` cut by a gate cuts nothing once the run it read is let go (`plan.py:cuts_of` "waits on"), so results change, not only speed. Cut clips: no, a deleted clip leaves the node unfed (`tools/region.py:cut_file`, `plan.py:file_of`). |
| O3 | no | The tree has no pinned result: `document.py:Document.pinned` is the plot's list and `Memo._pinned` is a static node's in-process value. The held file's loss is silent: a `VERSION` mismatch loads as none and a bad record ends the read (`held.py:File.load`). |
| O4 | only for a frame tool of existing types and facets | #26 and #27 changed nothing outside `tools/` and `tests/`; a new type edits `wire.TYPES`, a new facet edits `registry/`, and a cutting tool edited `held`, `heldwalks`, `walk`, `worker`, `graph`, `plan`, `window` (#33). `tests/test_seams.py:test_a_tool_reaches_the_player_through_the_modules_named_here` holds what a tool may import, and lets it import `held` and `store`. |
| O5 | no | Each limit is a constant of its own module, none summed and none read off the machine (section 2); pinned memo entries, the one frame a cache keeps and the last held run pass their limits unsaid. A stack past `STACK_BYTES` is said and closes the walk (`walk.py:_Walk.refuse`; `tests/test_graph.py:test_a_window_stack_stops_at_the_byte_limit_as_the_clip_stack_does`); the memo and caches never refuse. |
| O6 | for frame-times and clips; not for the held file | Frame-times: unique `mkstemp`, `os.replace`, the last whole table wins. Clips: unique `.part`, `take_name` refuses a taken name (`tests/test_cut_file.py:test_a_cut_for_a_moved_shape_lands_while_two_nodes_read_their_clips_of_the_folder`); the check for a clip under way is this process's `_running` alone. The held file: two players on one document append in place to one file, or rebuild through one fixed `{path}.part` that each one's `finally` removes; the csv, recent, views and document writers use fixed `.part` names too. |

The journal's D2 says a saved file promises "pinned results"; the tree has no such thing to pin
(O3's row), so which results D2 means is the next stage's to say.

## Where `docs/systems-review.md` disagrees with the tree

- Line 37 puts a region's clips "in the folder" beside the document; they lie under `store.folder()` (`tools/_cutfile.py:folder_for`).
- A19 says the held file is good under `held.py:stamp`; `held.py:STAMP` is `(VERSION,)` alone and a run is good under its keys (`held.good`). A19 also omits `walk.py:stacked_key`, `period_keys` and the "code" digest of `held.marked` among what says a kept thing is good.
- M06 gives `walk.py` 384 lines; it has 525, with `Leg`, `HeldCut`, `window_legs`, `period_keys`.
- S6 says one `_Walk` under three drivers; `worker.py:Worker` makes four `_Walk`s, and the bare driver walks no cut in time.
- W16 names `_update_gate`, deleted in `8e58f608` for `_update_display`.
