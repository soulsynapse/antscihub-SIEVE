import sys
from pathlib import Path

# `tools/` is not a package and must not become one — it holds repo machinery,
# not product code. The tests reach it by path instead.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
