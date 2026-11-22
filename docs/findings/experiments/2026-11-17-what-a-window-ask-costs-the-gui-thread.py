"""What the GUI thread pays, in a player offscreen, for the calls an edit or a window move makes:
Graph.sync, PlayerWindow._show_held and PlayerWindow._restate, the least of three means of 30.
The held file's write is put out, and the process leaves without closing, so nothing is written
beside the document. <tree> is a checkout of the repository, this one or another commit's.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-what-a-window-ask-costs-the-gui-thread.py <tree> <document>"""
import os, sys, time
tree, docpath = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
sys.path.insert(0, tree); os.chdir(tree)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from sieve_player import held
from sieve_player.registry import discover
from sieve_player.window import PlayerWindow
held.File.write = lambda self, *a: []
app = QApplication([])
win = PlayerWindow(docpath, "t", discover("tools"))
if win.playing:
    win.toggle_play()
t0 = time.perf_counter()
while time.perf_counter() - t0 < 3:
    app.processEvents(); time.sleep(0.01)
def ms(f, n=30):
    best = 1e9
    for _ in range(3):
        t = time.perf_counter()
        for _ in range(n):
            f()
        best = min(best, (time.perf_counter() - t) / n)
    return round(1000 * best, 3)
print(f"{os.path.basename(tree):<18} {os.path.basename(docpath)[:28]:<28} nodes {len(win.doc.nodes):>2} runs held {len(win.runs):>3}: "
      f"graph.sync {ms(win.graph.sync)} ms, _show_held {ms(win._show_held)} ms, _restate {ms(win._restate)} ms", flush=True)
os._exit(0)
