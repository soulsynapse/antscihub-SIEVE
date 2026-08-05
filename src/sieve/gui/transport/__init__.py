"""How a frame is asked for and how it arrives: request, decode, cache, pace.

The package is drawn where the repository's own history drew it. Over 438
commits `decode_worker`, `coalescer`, `proxy_cache`, and `scrub_policy` were
never edited in a commit that did not also touch `player.py`, and `render_ring`
was edited without it once. That is CLAUDE.md's second rule — things that
change together belong together — and the reason the boundary is a package
rather than a naming convention: twelve stable files that must be edited in
lockstep are worse than one file, because nothing declares the coupling.

**The transport is handed its work; it never reaches for the project.** A
request names a frame, a consumer, and an intent, and that is the whole input.
Nothing here imports `document`, `filter_tab`, `main_window`, or `timeline` —
`.importlinter`'s `transport-is-handed-its-work` contract is that sentence made
checkable, and it is the property that lets a second tab drive the same
transport without either tab learning about the other. The direction is the
point: widgets above may reach down into this package, and a reach back up is
the defect the contract names.

What is deliberately *not* here: `video_view` and `crop_tools`, which co-change
with `document` roughly twice as often as with `player`. Pixels-and-pointer is
a different axis of change from frames-arriving, and a package holding both
would be named for a concept rather than for a reason to edit.
"""
