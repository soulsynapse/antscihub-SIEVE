---
title: Process isolation for filter execution
status: deferred
priority: unassessed
gated_on: >
  a kernel that can take the process down rather than raise — most likely the
  first OpenCV-heavy filter or GPU work. Cooperative cancellation is the other
  trigger and the more likely one in practice: a full-video run the user wants
  to stop mid-frame cannot be interrupted in-process short of checking a flag
  between frames, which is fine until a single frame is slow.
reads:
  - docs/SCAFFOLD.md
  - .importlinter
  - src/sieve/pipeline/executor.py
---

# Process isolation for filter execution

`execute` runs in the calling process, and today's kernels fail by raising,
which a `try`/`except` already contains.

**The cost is not one module, so the size is not a surprise later.** SCAFFOLD
reserves four, because a process boundary is a serialization boundary: frames
are ~47 MB on the reference source, so the transport has to be shared memory
rather than pickle — a named-segment lifecycle and a versioned protocol
negotiated at startup. `shm_transport.py` and `protocol.py` are not incidental
to `manager.py`.

**The thing to not get wrong when it lands:** the GUI reaches `workers/` only
through `pipeline/`, per `.importlinter`. A worker handle surfacing in `gui/`
is how rule 1 fails quietly.
