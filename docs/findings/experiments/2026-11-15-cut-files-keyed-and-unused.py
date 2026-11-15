"""One-off for docs/spec/cut-files.md: two regions on two seconds of a clip, cut by ffmpeg through an
offscreen PlayerWindow into a store under the work folder. Each serves its clip once the cut ends
with nothing else pressed; a moved shape is one clip more, cut while both nodes read theirs; the
footage's clips no node would serve are counted on the card and deleted by its button; the header's
control reads the store; another store chosen serves nothing, and the first chosen again serves as
before. Run from the repo root; the work folder is deleted and made again:
python docs/findings/experiments/2026-11-15-cut-files-keyed-and-unused.py <work folder> <clip> <geometry.json>"""
import os
import shutil
import subprocess
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.decoder import footage_print  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tools import _cutfile as C  # noqa: E402
from tools import gray, region  # noqa: E402

work, clip, geometry = (os.path.abspath(p) for p in sys.argv[1:4])
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
store.CHOICE = os.path.join(work, "store.txt")      # the user's own choice and store are left alone
assert store.choose(os.path.join(work, "store")) == ""
video = os.path.join(work, "plate.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-t", "2", "-c", "copy", video], check=True)
folder = C.folder_for(video, footage_print(video))

app = QApplication.instance() or QApplication([])
tools = [region, gray]
doc = D.from_tools(tools, video)
shapes = region.load_geometry(geometry)
names = [s["name"] for s in shapes["shapes"]]
doc.node("region").params.update(shapes, choice=names[0])
doc.add_node("region", id="other", params={**region.DEFAULTS, **shapes, "choice": names[1]})
doc.connect("video", "other")
doc.display = "gray"
D.save(doc, os.path.join(work, "doc.json"))
win = PlayerWindow(os.path.join(work, "doc.json"), "t", tools)


def spin(until, what, limit=20.0):
    t = time.perf_counter()
    while not until():
        if time.perf_counter() - t > limit:
            raise TimeoutError(what)
        app.processEvents()
        time.sleep(0.01)


def served():
    return {n: os.path.basename(e.file[0]) for n in ("region", "other") if (e := win.graph.entry(n)).file is not None}


def cut(card, what):
    t = time.perf_counter()
    card.button.click()
    assert card.cut is not None, card.status.text()
    wrote = [t[0] for t in card.cut.todo]
    spin(lambda: card.cut is None, what)
    print(f"{what}: wrote {wrote} in {time.perf_counter() - t:.1f} s; {card.status.text().split(' into ')[0]}")


try:
    spin(lambda: win.display._pix is not None, "the first frame")
    g, card = win.graph, win.pane.widget("region")
    assert served() == {} and "not cut at standard" in card.clip.text() and not card._unused(), card.clip.text()
    assert win.header.store.held == 0
    print("before a cut:", card.clip.text(), "| the store holds", win.header.store.held)

    cut(card, "the first cut")
    was = served()
    assert set(was) == {"region", "other"} and win.canvas.served == {"region", "other"}
    assert sorted(os.listdir(os.path.join(work, "store"))) == [footage_print(video)] and win.header.store.held > 0
    print("served with nothing else pressed:", was, "| the store holds", win.header.store.held, "bytes under", os.path.relpath(folder, work))
    for n in ("region", "other"):
        win.doc.display = n
        win.reflag()
        spin(lambda: g.peek(win.row) is not None, f"a row of {n}")
    assert all(g.readers.held(g.entry(n).file[0]) is not None for n in was)
    card.button.click()
    assert card.cut is None and card.status.text().startswith("nothing to cut"), card.status.text()
    print("pressed again:", card.status.text())

    moved = [dict(s) for s in shapes["shapes"]]
    moved[0] = {**moved[0], **({"circle": [moved[0]["circle"][0] - 4, *moved[0]["circle"][1:]]} if "circle" in moved[0]
                              else {"polygon": [[x - 4, y] for x, y in moved[0]["polygon"]]})}
    for n in ("region", "other"):       # both read one geometry file, so a shape moved in it moves in both
        win._picked(n, {"shapes": moved})
    app.processEvents()
    assert served() == {"other": was["other"]}, served()
    print("a shape moved:", card.clip.text(), "| other still serves", was["other"])
    cut(card, "the cut for the moved shape, both clips open")
    now = served()
    assert now["other"] == was["other"] and now["region"] != was["region"] and os.path.isfile(os.path.join(folder, was["region"]))
    print("served:", now)

    below = C.folder_for(os.path.join(folder, was["region"]), "")       # what a node below the region would have cut of the clip it had
    os.makedirs(below)
    shutil.copy(os.path.join(folder, was["other"]), os.path.join(below, C.file_for("below", "0" * 16)))
    listed = sorted(os.path.basename(p) for p, _, _ in card._unused())
    assert listed == [was["region"]], listed
    print("unused:", listed, "|", card.spare.text())
    held = store.held(store.folder())[0]
    card.sweep.click()
    app.processEvents()
    left = sorted(os.listdir(folder))
    win.header.store.set_store(store.folder())      # as the pointer coming over the control reads it
    print("after the press:", left, "|", card.status.text() or "all deleted", "| the store holds", win.header.store.held, "of", held)
    assert served() == now and all(n in left for n in now.values())
    assert (was["region"] in left) == bool(card.status.text())      # a clip a retired reader has yet to close stays, and the card says so
    assert was["region"] in left or not os.path.exists(below)         # what was cut of the clip went with it
    assert was["region"] in left or win.header.store.held < held
    key = C.rect_key(footage_print(video), dict(region.crops(g.doc.node("region").params))[names[0]], "standard")
    assert now["region"] == C.file_for(names[0], key)

    assert store.choose(os.path.join(work, "another")) == ""
    win.sync()
    app.processEvents()
    assert served() == {} and "not cut" in card.clip.text()
    print("another store chosen:", card.clip.text())
    assert store.choose(os.path.join(work, "store")) == ""
    win.sync()
    app.processEvents()
    assert served() == now
    print("the first chosen again:", served())
    print("ok")
finally:
    win.ask_unsaved = lambda: "discard"     # the document was edited above, and offscreen nobody answers the dialog
    win.close()
