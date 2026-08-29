"""Toolhood: what a tool is, whatever it does.

This package is the whole of what a tool may import, and it is deliberately
small: edge kinds, the frame vocabulary, the node contracts, and the record
below. Finding and loading tools is `sieve.registry`, on the substrate side —
it needs the settings, and a contract that dragged the settings in behind it
would put every tool one import from the application. The import-linter
contract in `pyproject.toml` is what noticed, and what keeps it noticing.

**SIEVE names tool types, never tools.** A type is a contract and contracts
are the substrate's job. A tool's type is the role it fills, held rather than
inherited — `Tool.role` is a `nodes.Source` today and a step tomorrow, in the
same slot — so nothing subclasses anything and SIEVE never holds an instance
of a tool's own class.

A tool's version is the author's to bump: a key over its output folds it
(ADR-0010), and nothing at run time can tell that an edit changed the answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.contract.nodes import Source


@dataclass(frozen=True)
class Tool:
    """A tool, whatever it does. The role says which contract it satisfies."""

    name: str
    version: int
    role: Source
