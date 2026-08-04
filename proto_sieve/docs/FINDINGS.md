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

- **Chunk 5's tool needed the resolver, and the import is circular.**
  `resolver.py` imports `Requirement` from `tools/base.py` at module level;
  `Tool.lower` imports `resolve` at line 32, *inside the method body*, because
  a module-level import would not resolve. That deferred import is the whole
  evidence. `DECISIONS.md` says a tool "declares a requirement; it does not
  construct a graph of named ops — because implementation choice belongs to
  the resolver", but `Tool.lower` calls `resolve` and builds the `Node`: the
  tool does construct the graph, it delegates one field of it. **A leaked
  secret, not a missing interface item** — what leaked is *which side owns the
  vocabulary*. `Requirement` is the thing both modules speak, so it belongs
  where both can see it (beside `Affine`, which it is made of), and the only
  caller of `lower` — `pipeline.lower` — is where `resolve` should be applied:
  `Node(resolve(tool.requirement(params)), (source,))`. Then `tools/` never
  imports `resolver` at all. Not worked around; recorded as it stands.
  Corollary from the same read: `Requirement(map, out_shape)` and
  `Resample(map, out_shape)` are field-for-field identical and `resolve`'s
  fallback branch is `Resample(req.map, req.out_shape)` — a rename. The
  requirement/op distinction carries information on exactly one branch (the
  `Slice` swap). That does not make the boundary wrong; it does mean the
  decision behind it is demonstrated by a single `if`.

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

- **Four files know the 2x3 affine is row-major with the translation in
  slots 2 and 5.** `kernel.py` declares it (`Affine.m`), `crop.requirement`
  constructs it positionally (`Affine((1.0, 0.0, x0, 0.0, 1.0, y0))`),
  `resolver._is_unit_translation` unpacks it (`a, b, c, d, e, f = m.m`) and
  tests slots 0/1/3/4 for identity and 2/5 for integrality, and
  `executor._resample` unpacks it again and indexes `a*ox + b*oy + c`. Same
  shape as the repo-root walk: one unanticipated fact spread across four
  modules rather than an anticipated change absorbed by two. Moving to a 3x3,
  to named fields, or to column-major edits all four, and nothing catches a
  missed site — `_canon` hashes whatever tuple it is handed. Note this sits
  directly against `kernel.py`'s own docstring ("nothing outside this module
  may depend on ... the field layout of an op"), which as written is
  indefensible for the ops themselves — `executor._apply` must read `op.y0`,
  `op.out_shape`, `op.name` to evaluate anything, and a value type whose
  fields nobody may read is not a value type. The docstring's claim is sound
  for the *canonical form and the digest*, and overclaims when it extends to
  field layout. The co-touch on `Affine.m` is real either way.

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
