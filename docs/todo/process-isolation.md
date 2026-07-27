---
title: Process isolation for filter execution
status: deferred
gated_on: >
  a kernel that can take the process down rather than raise — most likely the
  first OpenCV-heavy filter or the GPU work; cooperative cancellation is the
  other and more likely trigger
reads:
  - docs/SCAFFOLD.md
  - .importlinter
  - src/sieve/pipeline/executor.py
---

# Process isolation for filter execution

**Why not now.** `execute` runs in the calling process. One filter exists, it is
NumPy over a decoded array, and the failure modes it has are exceptions a
`try`/`except` already contains. `workers/` buys crash isolation, and there is
nothing yet whose crash would take anything down.

The cost is not one module: SCAFFOLD reserves four, and the reason is that a
process boundary is a serialization boundary. Frames are ~47 MB on the reference
source, so the transport has to be shared memory rather than pickle, which means
a named-segment lifecycle and a versioned protocol with negotiation at startup —
`shm_transport.py` and `protocol.py` are not incidental to `manager.py`.

**What would make it the right time.** A kernel that can take the process down
rather than raise: `cv2` can segfault on malformed input and a CuPy kernel can
wedge a context, so the trigger is most likely the first OpenCV-heavy filter or
the deferred **GPU execution** item, docs/todo/gpu-execution.md. Cooperative
cancellation is the other trigger and the more likely one in practice — a
full-video run the user wants to stop mid-frame cannot be interrupted by
anything in-process short of checking a flag between frames, which is fine until
a single frame is slow.

**The thing to not get wrong when it lands:** the GUI reaches `workers/` only
through `pipeline/`, per `.importlinter`. A worker handle that surfaces in `gui/`
is how the "GUI is a view over the executor, never a second execution path" rule
fails quietly.

Read: `docs/SCAFFOLD.md` `workers/`, `.importlinter` layers contract,
`src/sieve/pipeline/executor.py`.
