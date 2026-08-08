---
name: q
description: Queue a prompt into the agent-orchestrator window from this repo, instead of doing the work in this session. Use when Kendrick says to queue something, add it to the queue, send it to the orchestrator, or hand it to a run — with /q or in his own words.
---

# Queue it, don't do it

The orchestrator window drains a queue of unattended runs. This puts one entry
in it against **this** repo and stops there: the work is the queued run's, not
this session's. Do not also start doing it.

```bash
uv run --project ~/Documents/Code/agent-orchestrator orchestrator add "…"
```

Run it from the working tree the entry belongs to — the current directory is
what decides which project the row is queued against, and `--project <path>`
overrides it. The command prints the window's own answer: the label the row got
and how much is waiting in front of it.

## Writing the entry

Write the outcome in a few sentences — what should be different when it is done,
and anything the run could not work out for itself. Not a plan, not a file list,
not steps. The run starts later against a tree that has moved on, and
over-specifying is the usual way a queued entry fails.

If `/q` came with text, that text is the subject; work it up into an outcome
rather than queueing it verbatim. If it came with nothing, queue what this
conversation has just settled on, and say back what you queued.

## The rest of it

| | |
|---|---|
| `--next` | in front of everything waiting. Only for work the next run would trip over or build on top of — a broken build, a wrong assumption something queued behind it depends on |
| `--label "…"` | what the row is called; defaults to the prompt's first line |
| `-` or no message | reads the prompt from stdin, which is how a long one avoids shell quoting |
| `orchestrator list` | what this project's queue holds, and how the last few runs ended — use it to check the row landed, or before queueing so the same work is not queued twice |

The window has to be open: the command reaches it over a socket whose address is
published while it runs. "No orchestrator window has said where to reach it"
means the app is closed — say so and stop rather than retrying or editing the
queue's stored state by hand.

Queueing a saved library prompt by name is not something this command does —
that goes through the window, or through a session's own `queue_prompt` tool.
