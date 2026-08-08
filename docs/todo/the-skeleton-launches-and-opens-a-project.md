---
title: The skeleton launches and opens a project
step: "07.4"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui/test_skeleton.py -q -k opens_a_project_and_walks_to_a_step"
opened: 2026-08-08
---

# The skeleton launches and opens a project

The spike's `gui/` — app, layout, the control rail, project select, hotkeys —
adopted over 07.2's session (`adr/gui-base-is-the-v25-spike.md`): the app
launches, opens a project that exists, and walks project → pipeline → step
with the hotkey scheme, the rail rendering the pipeline's nodes as read from
the document. Up/down walking a spanning tree over the DAG is the GUI's
choice, not a fact the pipeline holds (same ADR).

PySide6 enters `pyproject.toml` here — the first Qt dependency the tree has —
and the GUI tests run offscreen so CI keeps its say. CI is ubuntu-latest, so
whatever system libraries offscreen Qt needs there enter `ci.yml` with the
dependency: a red from a missing libEGL is this item's to fix, not to
discover. Rendering only: no param
widgets, no canvas playback, no graphs; those are the steps behind this one.
The `gui-computes-nothing` exception list is empty at the start of this item
and empty at the end of it, which from here on every Phase 7 item inherits as
a standing clause rather than restating.
