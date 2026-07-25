"""Storage and decode boundaries: video read, Zarr store, project files.

``video_read`` is the sole decode boundary (ADR-018) and ``zarr_store`` the
sole store construction boundary (ADR-014). Callers go through the owner
rather than opening things themselves.
"""
