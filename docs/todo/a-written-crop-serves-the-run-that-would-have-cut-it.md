---
title: A written crop serves the run that would have cut it
step: "05.2"
status: done
gated_on: nothing
done_when: "uv run pytest tests/integration/test_crop_serving.py tests/unit/test_crop_binding.py -q"
opened: 2026-08-07
---

# A written crop serves the run that would have cut it

The read-back path, re-derived against schema v1: `pipeline/resolve_source.py`
answers which file a run opens and in whose frame numbering, `source_home.py`
carries the three facts a record is unreadable without (the directory its
relative path resolves against, the identity its parentage is matched
against, the video a run falls back to), and `crop_binding.py` answers which
of the four states a reader is being shown when a record stops backing a box.

Without this, 05.1 writes files nothing reads and materialization is an
export feature. With it, a written crop is what the plan says it is: a faster
route to pixels the graph would have computed anyway.

One step, called by every front end, is the shape to keep — v2's docstring
argues it directly, and a second answer to "which file does this run open"
is how two front ends start disagreeing about what a project contains.

`crop_binding.py` is the reporting twin and lands with its subject rather
than with the GUI that displays it: the four states are facts about records,
and `gui-computes-nothing` means the widget may not derive them.

`test_crop_serving.py` holds **5 cases** and `test_crop_binding.py` **13**;
18 rows in the table. Cases whose subject is a v2 field name are *replaced
by* named v3 cases — the states survive the rename, the spellings do not.
