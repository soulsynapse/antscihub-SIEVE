# Repository instructions

## Python environment

This repository has its own virtual environment at `.venv`. Use its Python
executable for validation and tests instead of the system or Anaconda Python.
For PyQt GUI tests, also set `QT_QPA_PLATFORM=offscreen`.


When you make decisions off the docs, you should inform the user how that guided your behavior so that old documentation that no longer holds doesn't contaminate the current live implementation. You should also flag any that seem like they shouldn't be the case so the user can evaluate them.


## Commits
When you make a significant change, author a commit using conventional commits protocol and 