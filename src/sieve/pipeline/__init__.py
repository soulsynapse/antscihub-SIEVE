"""Orchestration: what runs, in what order, and what may be reused.

Qt-free by contract (`.importlinter`), because the CLI, the GUI, and a batch job
on a cluster all execute through this package and only one of them has a
toolkit.
"""
