"""One structural check per ADR, each registered under the ADR's number.

The convention: a settled ADR that can be checked mechanically gets exactly
one contract, named for it and citing its number in every failure message,
registered in `pyproject.toml` under
`[tool.importlinter]` and run by `uv run lint-imports` — one registry, one
runner. An ADR whose subject is the import graph uses a built-in contract
type and needs no module here; one whose subject is not brings a custom
contract type in a module named `adrNNNN.py` in this package. Which ADRs
have contracts is `pyproject.toml`'s to say; an ADR absent there is
unchecked, not settled differently.
"""
