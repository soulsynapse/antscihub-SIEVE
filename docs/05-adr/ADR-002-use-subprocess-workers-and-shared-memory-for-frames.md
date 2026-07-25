# ADR-002: Use subprocess workers and shared memory for frames

Reference: https://docs.arc42.org/section-9/

## Context

SIEVE must keep its Qt event loop responsive while filters process video
frames. Moving frame arrays through a queue or pipe would serialize and copy
large payloads across the process boundary. At video rates, that overhead
would compete with the scientific computation and make interactive previews
less responsive.

Qt provides `QSharedMemory`, but its locking, attachment, and Python buffer
handling are awkward for NumPy-based processing. Python's
`multiprocessing.shared_memory.SharedMemory` exposes a named shared-memory
buffer directly and works naturally with NumPy array views.

## Decision

Run compute in a long-lived subprocess, not in the Qt process or a Qt worker
thread.

Move frames between the compute subprocess and the Qt process through named
shared memory. Use Python's
`multiprocessing.shared_memory.SharedMemory` as the default implementation.
A POSIX-specific implementation such as `posix_ipc` may be used when required,
provided it preserves the same transport contract.

The IPC control channel carries only lightweight descriptors: the shared
memory name or handle plus the array metadata required to reconstruct the
view, including shape, dtype, strides or layout, and frame/generation
identity. It must not carry frame bytes.

On receipt, the Qt side attaches to the named segment and constructs an
`np.ndarray` view over its buffer. It passes that array to
`pyqtgraph.ImageItem.setImage(..., autoLevels=False)`. The shared-memory
segment and its backing object must remain alive until the GUI has finished
using the frame.

The worker-to-GUI array transfer is zero-copy. Rendering may still require a
library- or device-level conversion, copy, or texture upload inside
pyqtgraph/Qt; the transport contract does not claim control over those
renderer internals.

## Alternatives considered

### Qt `QSharedMemory`

Rejected as the default because its API adds Qt-specific attachment and
locking machinery at a boundary otherwise expressed cleanly with Python
buffers and NumPy arrays.

### Pickled arrays through a queue or pipe

Rejected because serialization and payload copies scale with every frame and
undermine interactive throughput.

### Threads in the Qt process

Rejected because compute would share the GUI process, complicate failure
isolation, and allow Python or native-library contention to interfere with the
event loop.

## Status

Accepted.

## Consequences

- The Qt main thread orchestrates work and presents completed frames; it does
  not run filters.
- Frame payloads are not serialized through IPC, reducing transport copies and
  CPU overhead.
- The worker protocol must define descriptor metadata, ownership, lifetime,
  acknowledgement, cancellation, and stale-generation handling.
- A segment cannot be reused or unlinked until every consumer has stopped
  viewing it. Cleanup must also handle worker crashes and GUI shutdown.
- `autoLevels=False` keeps display levels stable and avoids an implicit
  per-frame level scan; level selection must be managed explicitly elsewhere.
- Shared-memory capacity and buffer reuse require bounded allocation and
  backpressure rather than unbounded segment creation.
- Tests must cover array shape, dtype, channel/layout interpretation, segment
  lifetime, cancellation, stale results, and cleanup after abnormal exits.
- POSIX-specific transports reduce portability and therefore remain optional;
  `multiprocessing.shared_memory.SharedMemory` is the cross-platform default.

## References

- [Python documentation: `multiprocessing.shared_memory`](https://docs.python.org/3/library/multiprocessing.shared_memory.html)
- [pyqtgraph documentation: `ImageItem.setImage`](https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/imageitem.html#pyqtgraph.ImageItem.setImage)
