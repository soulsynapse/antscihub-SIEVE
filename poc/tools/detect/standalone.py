"""Run the detector on its own, with the v2 chain in front of it producing its series."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sieve_tool import play  # noqa: E402
from tools.background_ema import tool as background_ema  # noqa: E402
from tools.block_signal import tool as block_signal  # noqa: E402
from tools.detect import tool  # noqa: E402
from tools.normalize import tool as normalize  # noqa: E402
from tools.rescale import tool as rescale  # noqa: E402

if __name__ == "__main__":
    sys.exit(play([rescale, normalize, background_ema, block_signal, tool]))
