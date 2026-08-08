"""How a frame is asked for and how it arrives: request, decode, cache, pace.

The package is drawn where v2's history drew it: over 438 commits
`decode_worker`, `coalescer`, `proxy_cache` and `scrub_policy` were never
edited in a commit that did not also touch `player.py`. Things that change
together belong together, and the boundary is a package rather than a naming
convention because files that must be edited in lockstep are worse than one
file when nothing declares the coupling.

**The transport is handed its work; it never reaches for the project.** A
request names a frame and an intent, and that is the whole input. Nothing here
imports `session`, `timeline`, or the window — the direction is the point:
widgets above may reach down into this package, and a reach back up is the
defect. The layers contract cannot say it (`timeline` and `transport` are one
package to import-linter), so it is said here and kept by the imports.

`RequestKind` lives here rather than in `core`, which is where v2 put it once
`bench/retention_trace.py` needed to read it. v3 has no such reader —
`pipeline/preview.py` states outright that it does not coalesce — so the
vocabulary stays with its only consumer until a second one exists.
"""
