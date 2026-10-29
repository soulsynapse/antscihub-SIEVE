"""Run the player with the example chain: gray -> rescale -> threshold -> motion -> reduce. Every tool under
tools/ is in the Tab menu; file, the selector, is there to wire into the video node.

    .venv\\Scripts\\python main.py [video]
"""
import sys

from sieve_player import play
from sieve_player.registry import discover
from tools import gray, motion, reduce, rescale, threshold

if __name__ == "__main__":
    sys.exit(play([gray, rescale, threshold, motion, reduce], sys.argv[1] if len(sys.argv) > 1 else None,
                  tools=discover("tools")))
