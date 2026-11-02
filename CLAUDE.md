# CLAUDE.md


## Comments and docstrings
- Write no comment by default. When one is needed, one line stating a why the
  code cannot; prefer a clearer name to a comment.
- A docstring states the contract: what goes in, what comes out, and the
  constraints a caller cannot see from the signature. Prose, no section
  headings. It never narrates what the body does.
- A module docstring says what the module is and where its seams are, in about
  ten lines or fewer. It is not a changelog: a feature's story lives in the
  commit message that added it, beside the diff it explains.
- A comment or docstring that contradicts the code is reported in the reply,
  never silently fixed or cut; it may be a bug's only witness.
- Before calling a diff done, run /comment-check over it.
