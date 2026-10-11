"""Run this tool on its own, after rescale: `uv run python poc/tools/normalize/standalone.py [video]`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sieve_tool import play  # noqa: E402
from tools.normalize import tool  # noqa: E402
from tools.rescale import tool as rescale  # noqa: E402

if __name__ == "__main__":
    sys.exit(play([rescale, tool]))
