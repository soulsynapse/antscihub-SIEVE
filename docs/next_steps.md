# Next steps

Last reviewed: `2026-07-23 15:16:37 -07:00`.

This file records unfinished work that is justified by the current checkout.
It is not an authorization to continue automatically into later Isolate
milestones.

## Current priority

### Validate and accept the implemented working-window milestone

Source:

- `docs/handoffs/3-Working-window.md`
- `docs/handoffs/3-Working-window-review.md`
- Accepted decision
  `docs/decisions/002-headless-scientific-identity-is-not-gui-lifecycle.md`

Implementation now provides:

- Qt-free stable request, resolution, plane, batch, stream, and outcome types.
- Registered sidecar identity checks and explicit extent provenance.
- Request-local synchronous native `rgb24` delivery.
- Bounded batching, cancellation, cleanup, and accessible final outcomes.
- Structured clean-EOF versus decoder-error reasons.
- An immutable GUI request snapshot that starts no scientific decode.
- A development diagnostic at `scripts/inspect_working_window.py`.
- Focused headless and offscreen GUI regression coverage.

Automated validation:

```text
93 passed in 23.12s
```

Remaining:

1. Review the implementation and automated validation result.
2. Optionally run the diagnostic on a registered source and derived child:

   ```powershell
   .\.venv\Scripts\python.exe scripts\inspect_working_window.py `
     PATH\TO\video.asset.json 2 5 --batch-size 2
   ```

3. Confirm the existing Isolate player still behaves normally in a visible
   manual session if desired.
4. Accept the milestone before unblocking the working grid.

Do not begin grid or channel implementation during this validation step.

## Queued work — blocked on the current priority

### Define and implement the working grid

The fourth handoff and review have now been assessed against the implemented
milestone-3 seams. The dated post-milestone-3 refresh is recorded in
`docs/handoffs/.isolate-state-divergence.md`.

Milestone 4 remains blocked until:

- The implemented working-window milestone is accepted.
- The user approves corrections to the handoff and review so their stale
  `4b09232` checkout description matches the current repository.
- The user chooses whether downsample and block intent persist or reset across
  active-asset switches.

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
