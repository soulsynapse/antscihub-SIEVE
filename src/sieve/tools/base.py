"""The Tool contract: what every tool is (ARCHITECTURE.md "Tools").

A tool is a pure front-end -- a nested Params model, lower(), view() --
in one file, holding no runtime handle, no I/O, no state outside Params
(DESIGN-SESSION.md, Exchange 5, "The rebuilt version"). The signatures
below are quotations from the settled record; nothing else is. How a
tool declares what it consumes is an open question recorded in
DEFERRED.md, due at this class's first real code.
"""

from sieve.debt import Owed


class Tool:
    """Base every tool subclasses; the contract, quoted, not invented."""

    def lower(self, p):
        raise Owed(
            "Tool.lower(p): params to an op graph in the five-shape algebra;"
            " ARCHITECTURE.md 'Tools', DESIGN-SESSION.md Exchange 5"
        )

    def view(self, p, out):
        raise Owed(
            "Tool.view(p, out): declared view over the closed vocabulary;"
            " ARCHITECTURE.md 'The GUI', DESIGN-SESSION.md Exchange 5"
        )
