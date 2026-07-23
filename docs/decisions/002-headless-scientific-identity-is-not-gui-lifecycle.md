# Headless scientific identity is not GUI lifecycle state

Status: proposed on 2026-07-23. Validate during implementation of the
working-window handoff before accepting.

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

The GUI-facing `ActiveAsset` snapshot is immutable, but it currently shares a
module with the PyQt `ActiveAssetController` and does not contain the active
media's `content_sha256`.

Using the GUI generation as scientific identity would couple reusable source
contracts to Qt lifecycle and would not establish which asset bytes a request
intended to process. Importing the current `ActiveAsset` module into a headless
source would also import PyQt.

## Proposed decision

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

## Required implementation evidence

Accept this decision only after the working-window implementation demonstrates:

- Importing the headless request and source does not import PyQt.
- A request retains expected `asset_id` and `content_sha256`.
- Resolution rejects a sidecar whose recorded identity no longer matches the
  immutable request.
- Changing `IsolateSession._generation` does not change an existing headless
  request's meaning.
- A later GUI state change does not mutate an already-created request.
- GUI stale-result rejection can remain outside the reusable source contract.
- Headless tests can construct and resolve requests without a Qt application.

If those checks require broad duplication of asset identity logic, revise this
proposal before acceptance rather than creating a competing identity system.

## Consequences if accepted

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

This proposal records the identity and import boundary required by
`docs/handoffs/3-Working-window.md`. That handoff remains the implementation
specification. Successful implementation supplies the evidence needed to move
this decision from Proposed to Accepted.
