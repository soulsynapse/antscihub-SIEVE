# Findings

The spike's actual output. Three lists, appended as they happen.

## Prior proofs that had to be edited

*(A chunk forcing an edit to an earlier chunk's test is a leaked boundary.
Record which chunk, which test, and what it had to accommodate.)*

- **None through chunk 4.** Chunk 4 added the cache and `tests/test_render.py`
  was not touched: `render(node, bound)` kept its signature, callers do not
  create or pass caches, and no result changed. So materialization behaves as
  a secret, which is the answer the load-bearing chunk was asked for.
  **Caveat:** nothing is committed, so this is not verifiable from the tree —
  see `STATUS.md`.

## Halts

*(A chunk needed something a neighbour did not expose. Record what was needed,
from whom, and whether it turned out to be a missing interface item or a
leaked secret.)*

- **Chunk 8 needed to know when a slide has settled; `Control` does not say.**
  `app.py` builds a `VideoPlayer` and calls `canvas.open()` synchronously
  inside `_render_workspace`, which blocks the event loop for the first
  frames of the project→workspace slide `Control.show_workspace` starts in
  the same call. Deferring the open until the track comes to rest needs a
  "slide finished" signal, or the duration; `Control` exposes neither
  (`_SLIDE_DURATION_MS` is private, and rightly so — how long a slide takes
  is the module's own secret). Worked around by leaving the stutter in.
  **A missing interface item, not a leaked secret**: the fact wanted is
  "the transition is over", which is `Control`'s to announce, and announcing
  it would not tell `app.py` anything about how the transition is done.
  Recorded retroactively — this predates chunk 8 existing as a chunk, and is
  the concrete case that showed the old "the GUI is not a chunk" wording was
  suppressing findings rather than just proofs.

## Co-touches

*(Anticipated changes absorbed by two modules instead of one. Also: commits
touching the same pair of files repeatedly. Three or four on the same pair is
a signal; one is noise.)*

- **Twelve files carry the same repo-root walk.** Eleven `gui/` files
  (`app.py`, `layout.py`, `control.py`, `pipeline.py`, `rail.py`, `step.py`,
  `project_select.py`, `video_player.py`, `hotkeys.py`, `windows/history.py`,
  `windows/preferences.py`) each define a private `_find_repo_root` and
  prepend the result to `sys.path`; `store/store.py` defines the twelfth as
  its public `repo_root`. Not an anticipated change absorbed by two modules —
  the reverse, one unanticipated fact spread across twelve. The fact is
  *where the tree's root is*, and it is not a GUI concern at all; `store/`
  already owns it and the eleven copies exist only because absolute imports
  rooted at `proto_sieve.src.sieve.*` cannot resolve until someone patches
  `sys.path`, which every file with a `__main__` smoke block has to do for
  itself. Root cause is the import root, not the duplication: installing the
  package (or rooting imports at `sieve.*`) deletes all eleven at once.
  Worth noting the copies are *not* identical to `store/`'s — the gui ones
  walk from `Path(__file__)` and take a `start` argument, `store/`'s walks
  from itself — so a naive dedupe to the existing `repo_root` would not
  have been a pure move.

## Things learned that were not on any list

- **A result's address is `(recipe, input content)`, not the recipe alone.**
  The recipe hash addresses the *graph*; it says nothing about what was bound
  to its sources. A cache keyed on the recipe alone serves frame 0's answer for
  every frame after it. This is the same failure as two computations sharing
  one address, arriving one layer down, and it was not on the expensive list.
  Pinned by `tests/test_cache.py::test_a_different_input_is_a_different_result`.

- **Content-addressing costs a full input hash per call.** `_bound_digest`
  hashes every bound frame on every `render`. Correct, and for video obviously
  unaffordable — a real cost the design had not accounted for. The likely exit
  is that frames carry an identity from upstream (a decode-time digest, or a
  source-plus-index token) rather than being hashed at use. That is a decision,
  not an optimisation, and it belongs on the expensive list.

- **`Blur` and `Sharpen` have no implementation and that is deliberate.** They
  exist so identity has two ops with the same field shape to separate. Giving
  them behaviour would be scope the decomposition does not need proving.
