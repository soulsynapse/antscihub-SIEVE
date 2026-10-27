"""`python -m sieve_player document.json [root ...]`: open a saved document against the tools the
registry finds under the roots (default: tools/)."""
import sys

from . import play
from .registry import discover


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    doc, roots = argv[0], argv[1:] or ["tools"]
    return play(doc, tools=[e.module for e in discover(*roots) if e.ok])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
