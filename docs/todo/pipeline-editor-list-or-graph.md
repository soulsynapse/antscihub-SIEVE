---
title: A pipeline editor, and whether it is a list or a graph
status: deferred
after: [kernel-protocol-beyond-one-frame]
gated_on: >
  a graph that is not a chain — which means a multi-upstream filter, which
  means the named-port change to `Edge` in
  docs/todo/kernel-protocol-beyond-one-frame.md
reads:
  - src/sieve/core/pipeline_model.py
  - src/sieve/pipeline/dag.py
  - docs/VISION.md
  - docs/SCAFFOLD.md
---

# A pipeline editor, and whether it is a list or a graph

**Why not now.** One filter exists. Every graph anybody can currently build is a
chain of one node, and a visual editor for that is a label.

**The design question that has no answer yet, and is the actual reason to
wait.** VISION step 4 describes the user-facing object as an *operations
history* — an ordered list you add to, with the current operation selected and
its controls beside it. ARCHITECTURE and `core/pipeline_model.py` say the model
is a DAG, and `dag.py` enforces it. Both are right: a linear chain is a
degenerate DAG, and the linear presentation is what makes the tool legible to
someone who is not thinking in graphs. What is undecided is whether they are one
widget that degrades to a list or two views over one model, and that cannot be
settled by argument — it is settled by watching what a user does the first time
a graph branches.

**What would make it the right time.** A graph that is not a chain, which means
a multi-upstream filter, which means the named-port change to `Edge` in the
deferred **A kernel protocol that is not one frame in, one frame out** item,
docs/todo/kernel-protocol-beyond-one-frame.md. Until then the operations list
VISION asks for is buildable as an ordinary list widget over `Dag.order` and
does not need this question answered.

Read: `src/sieve/core/pipeline_model.py`, `src/sieve/pipeline/dag.py`,
`docs/VISION.md` step 4, `docs/SCAFFOLD.md` `gui/pipeline_editor.py`.
