# Next steps

Last reviewed: `2026-07-23 14:57:15 -07:00`.

This file records unfinished work that is justified by the current checkout.
It is not an authorization to continue automatically into later Isolate
milestones.

## Current priority

### Implement the corrected working-window milestone

Source:

- `docs/handoffs/3-Working-window.md`
- `docs/handoffs/3-Working-window-review.md`
- Proposed decision
  `docs/decisions/002-headless-scientific-identity-is-not-gui-lifecycle.md`

Why now:

- The player and active-asset selection are implemented.
- The media-service performance pass preserved an independently requestable
  native decode path.
- The corrected handoff defines the next small boundary without beginning a
  grid, channel, or general processing executor.

Implement in this order:

1. Add Qt-free request and resolved-source types.
   - Require a registered asset reference.
   - Retain expected `asset_id` and recorded `content_sha256`.
   - Keep GUI generation and display request ids out of the headless request.
   - Verify that importing the headless contract does not import PyQt.

2. Resolve current asset and media facts.
   - Resolve through the existing `AssetService`.
   - Reject expected identity mismatches.
   - Compare cheap current facts such as file size, dimensions, and rational
     fps with the sidecar.
   - Record the sidecar identity as recorded, not freshly content-verified.
   - Preserve frame-extent provenance: decoded, packet, container, or duration
     estimate.

3. Implement a request-local native `rgb24` stream.
   - Open a separate `MediaSession`; never share the live player decoder.
   - Call `read_frame_rgb` without the Isolate display width cap.
   - Deliver absolute frame indices and immutable buffers in bounded,
     synchronous batches.
   - Make batch size an execution option that changes grouping only.
   - Do not retain previously yielded batches.

4. Make lifecycle and outcome behavior explicit.
   - Provide close/context-manager behavior.
   - Close request-local media on exhaustion, cancellation, failure, explicit
     close, and early consumer exit.
   - Keep the final outcome accessible after iteration.
   - Re-raise structured runtime decode errors after recording a failed
     outcome.
   - Check cancellation between bounded reads without adding a GUI worker.

5. Resolve the current EOF ambiguity with the smallest justified change.
   - Do not infer truncation from message text or empty FFmpeg stderr.
   - Report ambiguous current short reads as failure with the delivered prefix.
   - If practical, add a structured clean-EOF reason to `MediaSession` and
     cover it with focused tests.
   - Avoid a broad decoder redesign.

6. Add the pure GUI request-snapshot adapter.
   - Snapshot the current registered asset identity and Isolate
     `[window_start, window_stop)`.
   - Ensure later GUI changes cannot mutate an existing request.
   - Ensure snapshotting and window dragging do not start source decoding.
   - Do not add Prepare, Process, or Run controls.

7. Add the development validation surface.
   - Accept explicit asset, start, stop, `rgb24`, batch-size, and deterministic
     cancellation inputs.
   - Report identity status, extent provenance, rational timebase, native
     shape, batch indices, delivered span, and final outcome.
   - Keep it an implementation helper rather than a supported processing CLI.

8. Validate and return for user acceptance.
   - Use deterministic lossless fixtures for exact pixel assertions.
   - Cover half-open spans, one-frame requests, identity mismatch, extent
     provenance, child media, batch invariance, cleanup, cancellation, EOF, and
     failure.
   - Run GUI tests headlessly:

     ```powershell
     $env:QT_QPA_PLATFORM = "offscreen"
     .\.venv\Scripts\python.exe -m pytest -q
     ```

   - Run `git diff --check`.
   - Commit the functional change conventionally.
   - Stop and return the completed milestone for user validation.

Definition of complete:

- The corrected handoff's definition of done is satisfied.
- No grid, scientific channel, GUI processing worker, cache, recipe, result
  persistence, or general executor has been added.
- The user has accepted the milestone.

## Decision follow-up

### Evaluate the proposed headless scientific identity decision

After working-window implementation:

- Compare the implementation evidence with
  `docs/decisions/002-headless-scientific-identity-is-not-gui-lifecycle.md`.
- Move it to Accepted only if the headless import, stable identity, immutable
  request, and GUI-envelope separation checks pass.
- Revise or reject it if implementation reveals duplicated identity logic or a
  better existing boundary.

## Queued work — blocked on the current priority

### Define and implement the working grid

The working-grid divergence notes already identify likely current-checkout
corrections, but milestone 4 remains blocked until:

- The working-window milestone is implemented and accepted.
- The grid handoff and review are present in the checkout.
- Their assumptions are rechecked against the implemented headless request,
  resolved-source, stream, and GUI snapshot seams.
- The dated divergence record is refreshed against that implementation.

Do not implement the grid from divergence notes alone. When unblocked, keep
native working geometry separate from the capped display preview and preserve
the milestone's no-channel boundary.

## Deferred work — no current implementation authorization

Do not begin these merely because the working-window source or working grid is
complete:

- Implement the first scientific channel.
- Add a GUI computation worker, latest-only publication, or cross-thread queue.
- Add additional media planes or a plane registry.
- Add scientific result persistence, recipes, export, CLI/HPC processing, or a
  general graph executor.

The oracle handoff for each milestone must be reviewed against the then-current
checkout and recorded in `docs/handoffs/.isolate-state-divergence.md` before
implementation.
