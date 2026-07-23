# Headless scientific identity is not GUI lifecycle state

Status: accepted on 2026-07-23 after working-window implementation validation.

## Context

The current Isolate player uses `IsolateSession._generation` to reject late
results from its display decode thread. That value belongs to one live Qt
session. It changes when GUI media lifecycle changes and cannot be reproduced by
a headless process, CLI invocation, test fixture, or later distributed job.

The asset sidecar already records durable identity:

```text
asset_id
media.content_sha256
```

At proposal time, the GUI-facing `ActiveAsset` snapshot was immutable but did
not contain the active media's `content_sha256`. It still shares a module with
the PyQt `ActiveAssetController`.

Using the GUI generation as scientific identity would couple reusable source
contracts to Qt lifecycle and would not establish which asset bytes a request
intended to process. Importing the current `ActiveAsset` module into a headless
source would also import PyQt.

## Decision

Reusable headless scientific contracts identify their intended asset using the
existing stable asset/content identity:

```text
registered asset reference
expected asset_id
expected content_sha256
```

They do not use GUI controller generations, display request ids, or widget
lifecycle as asset identity.

A GUI adapter may wrap a headless request in transient orchestration state:

```text
GUI generation
publication request id
cancellation ownership
latest-result policy
```

That envelope decides whether a result is still publishable in the live
application. It does not change what asset or frame span the headless request
means.

Headless request and source types must be importable without importing PyQt. A
thin GUI adapter may translate the current active-asset snapshot and local
Isolate window into the headless request.

The sidecar hash is recorded content identity, not proof that the current media
bytes were rehashed during request resolution. Ordinary small-window resolution
must report that distinction honestly rather than imposing full-file hashing on
interactive open latency.

## Implementation evidence

The working-window implementation demonstrated:

- `application.working_window` imports without importing PyQt.
- `WorkingWindowRequest` retains expected `asset_id` and
  `content_sha256`.
- Resolution rejects a sidecar whose recorded identity no longer matches the
  immutable request.
- `ActiveAssetController` now copies the existing sidecar content hash into its
  immutable snapshot.
- `IsolateSession.snapshot_working_window_request()` copies stable identity and
  the local half-open window without opening the scientific source.
- Changing the private GUI generation or later window values does not mutate an
  existing request.
- Existing display-generation rejection remains in `IsolateSession`; the
  reusable source imports no GUI module.
- Headless source and diagnostic tests construct and resolve requests without a
  Qt application.
- The implementation reuses `AssetService` identity resolution rather than
  creating a competing identity system.
- The complete offscreen regression suite passed with `93` tests.

## Consequences

- Scientific requests remain portable across GUI, test, CLI, and later
  distributed execution surfaces.
- Qt generations remain free to change with display lifecycle without
  invalidating durable scientific identity.
- GUI publication policy and source correctness remain separate concerns.
- The implementation needs a small Qt-free request/reference type and a GUI
  snapshot adapter.
- Content verification remains explicit; recorded sidecar identity must not be
  mislabeled as freshly verified bytes.

## Relationship to current handoff

This decision records the implemented identity and import boundary required by
`docs/handoffs/3-Working-window.md`.
