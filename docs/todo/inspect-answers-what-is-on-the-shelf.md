---
title: inspect answers what is on the shelf
step: "05.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cli_inspect.py tests/integration/test_cli_help.py -q"
opened: 2026-08-07
---

# inspect answers what is on the shelf

`cli/inspect_cmd.py` port-with-rename: the command that reads the registry
and prints what a tool declares. In v2 it also printed the kernel table from
`backend/dispatch.py` and the guidance path for a per-tool document; the
first is dropped outright (`adr/no-kernel-apparatus.md`) and the second waits
on PLAN's per-tool-document question, so this command ships without it rather
than inventing a shape that question would overrule.

What it gains instead is the Phase-1 contract: a tool's window is two-sided
now (01.3), and its params declare a population kind (01.4). Both are spec
data a reader of `inspect` should see, and both are exactly the declarations
that would otherwise sit unread until Phase 7 — `inspect` is what makes them
falsifiable before a widget exists.

`detect_cmd` does not port. Detection is a node, so what it answered is now
`inspect` plus `run` (`adr/detector-is-a-node.md`).
