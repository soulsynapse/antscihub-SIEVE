"""Toolhood: what a tool is, whatever it does.

This package is the whole of what a tool may import, and it is deliberately
small: edge kinds, the frame vocabulary, the node contracts, and the record
below. Finding and loading tools is `sieve.registry`, on the substrate side —
it needs the settings, and a contract that dragged the settings in behind it
would put every tool one import from the application. The import-linter
contract in `pyproject.toml` is what noticed, and what keeps it noticing.

**SIEVE names tool types, never tools.** A type is a contract and contracts
are the substrate's job. A tool's type is the role it fills, held rather than
inherited — a `nodes.Source` today and a step tomorrow, in the same slot — so
nothing subclasses anything and SIEVE never holds an instance of a tool's own
class. The slot is `nodes.ROLES`, and it is the table that has to be
consulted rather than a class that gets named: this file once annotated the
slot as `Source` and the registry gated on it, so the second role the
docstring promised would have been dropped at load and reported as a
malformed tool.

A tool's version is the author's to bump: a key over its output folds it
(ADR-0010), and nothing at run time can tell that an edit changed the answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from typing import Any

from sieve.contract.nodes import ROLES, role_kind


@dataclass(frozen=True)
class Tool:
    """A tool, whatever it does. The role says which contract it satisfies."""

    name: str
    version: int
    #: any role in `nodes.ROLES`; checked below rather than annotated, so
    #: adding a role is an edit to that table and not to this line
    role: Any

    @property
    def kind(self) -> str:
        """The name of the contract this tool's role satisfies."""
        found = role_kind(self.role)
        if found is None:      # unreachable: __post_init__ refuses first
            raise ValueError(f"{self.name} has no role")
        return found

    def __post_init__(self) -> None:
        if role_kind(self.role) is None:
            raise ValueError(
                f"{type(self.role).__name__} is not a role; "
                f"SIEVE contracts {', '.join(sorted(ROLES))}")
