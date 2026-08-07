import sys
from pathlib import Path

# `scripts/` is not a package and must not become one — it holds repo
# machinery, not product code ("tools" is the product's word for pipeline
# steps). The tests reach it by path instead.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
