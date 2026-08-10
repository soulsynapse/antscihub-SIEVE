"""Open SIEVE: `uv run SIEVE.py`.

Same entry point as `uv run sieve`; this exists so the app can be launched by
pointing at a file in the repo root, without the package being installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sieve.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
