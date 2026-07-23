"""VS Code-friendly launcher for the SIEVE desktop application."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = REPOSITORY_ROOT / "src"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from antscihub_sieve.gui.main import main


if __name__ == "__main__":
    raise SystemExit(main())
