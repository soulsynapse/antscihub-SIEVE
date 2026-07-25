"""Orchestration: the DAG, the executor, cache keys, preview policy.

A directed acyclic graph from day one; a linear pipeline is the degenerate
case. Never imports Qt, which is what lets the CLI and an HPC run drive the
same executor the GUI drives.
"""
