"""The pipeline: the chain of steps in the open project.

The second position on the right pane's track (`frame/swipe.py`) — the chain in
the project you opened, between the library and the step you are standing on. It
is the chassis so far: a head, and a room saying there is nothing in it. The
chain itself is not built here yet, and nothing in this folder names the position
or the pane it stands in (ADR-0001).
"""

from __future__ import annotations

from sieve.gui.view.pipeline.view import Pipeline

__all__ = ["Pipeline"]
