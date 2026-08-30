# explorer-logs

Sessions the orchestrator explorer wrote, hand-driven and scripted alike.
Ground truth for how the thing behaves; read the newest before trusting any
recollection of it.

**Several logs here predate fixes made the same day and are not usable for
every claim.** Nothing in a log says which build wrote it, so check the
fields the fixes added rather than the timestamp. A log is downstream of a
fix when:

| fix | fingerprint |
|---|---|
| duration bars attributed to the dispatcher, not to the node that asked | `duration_bars` keys begin `dispatch:` |
| `--window-seconds` knob | `topology.window_is_full_size` present |
| `_land_at` declares before releasing (overlapping windows reuse) | `pool.refetched` present |
| the three preemption policies, flagged and off by default | `topology.preemption` present |

The transport spin was fixed alongside the bar attribution, so the same
fingerprint covers both; a log carrying it also has any leg with
`events_capped: true` as evidence of the spin rather than of real work.

The re-decode bug only fires when two landings overlap, so a log that
predates the fingerprint may still be sound — derive the window starts from
the `window@N` run labels and check. `pool.decodes` equal to
*(windows x window_frames)* on the nose is the tell that nothing was reused.


**A log carrying `topology.preemption` states which arm wrote it.** All three
flags off is the control; anything else is a policy run and its walls are not
comparable to a control's. Under `--live-playhead` the control's own wall is
wide -- leg 4 spans 7.8 to 33.3 s over six runs of the identical script,
because the count of times the GUI wins the queue mid-run is a race and not
a property of the script. Read a control against a control, at n greater
than one, or read `fill:seek` out of `dispatch_trace` instead, which is
deterministic where the wall is not.
Which logs each published finding used is stated in that finding's `where:`
field, in `docs/findings/`.
