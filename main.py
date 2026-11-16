"""Run the player on the document recent.FILE notes newest. With a video, or with no document
noted, on the example chain instead: gray -> motion -> reduce -> smooth. Every tool under tools/ is
in the Tab menu; file, the selector, is there to wire into the video node.

    .venv\\Scripts\\python main.py [video]
"""
import sys

from sieve_player import play, recent
from sieve_player.registry import discover
from tools import gray, motion, reduce, smooth

if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else None
    document = None if video else recent.last(recent.FILE)
    sys.exit(play(document or [gray, motion, reduce, smooth], video, tools=discover("tools")))
