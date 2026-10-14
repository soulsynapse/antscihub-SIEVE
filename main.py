"""Run the player with the example chain: gray -> rescale -> threshold -> motion.

    .venv\\Scripts\\python main.py [video]
"""
import sys

from sieve_player import play
from tools import gray, motion, rescale, threshold

if __name__ == "__main__":
    sys.exit(play([gray, rescale, threshold, motion], sys.argv[1] if len(sys.argv) > 1 else None))
