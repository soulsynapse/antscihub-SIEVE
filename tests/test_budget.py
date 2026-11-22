"""The limits shared out of a machine's memory, the machine handed in, and what the holders a player
and a bare walk build take together against them."""
import json
import os
import subprocess
import sys
from pathlib import Path

from sieve_player.budget import CEILINGS, HELD_AT_ONCE, SHARE, TOTAL_ENV, limits

GB = 2**30
ROOT = Path(__file__).resolve().parents[1]


def _total(got):
    return sum(got[k] * HELD_AT_ONCE[k] for k in got)


def test_a_machine_with_room_gets_the_ceilings():
    assert limits(64 * GB, {}) == CEILINGS


def test_a_small_machine_shares_half_in_the_ceilings_proportions():
    got = limits(4 * GB, {})
    assert _total(got) <= 2 * GB
    scale = got["memo"] / CEILINGS["memo"]
    assert scale < 1
    assert all(abs(got[k] - CEILINGS[k] * scale) <= 1 for k in CEILINGS)


def test_the_variables_win():
    got = limits(4 * GB, {"SIEVE_MEMO_GB": "3", "SIEVE_CACHE_GB": "0"})
    assert got["memo"] == 3 * GB and got["cache"] == limits(4 * GB, {})["cache"]
    assert limits(4 * GB, {"SIEVE_MEMORY_GB": "64"}) == CEILINGS


def test_the_holders_a_player_and_a_bare_walk_build_take_no_more_than_the_plan(tmp_path):
    for ram in (4 * GB, 64 * GB):
        env = {k: v for k, v in os.environ.items() if not k.startswith("SIEVE_")}
        env.update({TOTAL_ENV: str(ram * SHARE / GB), "QT_QPA_PLATFORM": "offscreen", "SIEVE_STORE": str(tmp_path / "store")})
        out = tmp_path / f"{ram}.json"
        ran = subprocess.run([sys.executable, "-X", "utf8", "-m", "tests.test_budget", str(tmp_path), str(out)],
                             env=env, cwd=ROOT, capture_output=True, text=True, timeout=300)
        assert ran.returncode == 0, ran.stderr
        built = json.loads(out.read_text(encoding="utf-8"))
        plan = min(SHARE * ram, _total(CEILINGS))
        assert sum(n for _, _, n in built) <= plan, (ram // GB, sorted(built, key=lambda b: -b[2]))


def _built(folder, out):
    """Opens a player window over a small clip and walks it bare, and leaves at `out` [class, where
    it was built, bytes] of each results holder built: a Memo, a Decoder's cache, a held.Runs, a
    result_keeper.Keeper that has a limit, a walk's stack, a display's proxies. The bare walk's
    Runs is the walk's output, sized 0 a run, and is left out."""
    from PySide6.QtWidgets import QApplication

    from sieve_player import bare, decoder, graph, held, store, walk, window
    from sieve_player import document as D
    from sieve_player import result_keeper
    from tests.test_crop import clip
    from tools import count, detect, gray, threshold

    store.CHOICE = os.path.join(folder, "store.txt")
    decoder.read_frame_times_ahead = lambda path, then=None: None
    window.PlayerWindow.ask_unsaved = lambda self: "discard"
    built = []
    of = {graph.Memo: lambda o: o.limit, decoder.Decoder: lambda o: o.cache_limit, held.Runs: lambda o: o.limit,
          result_keeper.Keeper: lambda o: getattr(o, "limit", None), walk._Walk: lambda o: walk.STACK_BYTES,
          window.Display: lambda o: window.PROXY_BYTES}
    for cls, limit in of.items():
        def recorded(self, *args, _init=cls.__init__, _limit=limit, **kwargs):
            _init(self, *args, **kwargs)
            where = os.path.basename(sys._getframe(1).f_code.co_filename)
            if (n := _limit(self)) is not None and not (type(self) is held.Runs and where == "bare.py"):
                built.append((type(self).__name__, where, n))
        cls.__init__ = recorded

    tools = [gray, threshold, detect, count]
    doc = D.from_tools(tools, clip(os.path.join(folder, "v.avi")))
    D.save(doc, os.path.join(folder, "doc.json"))
    QApplication.instance() or QApplication([])
    win = window.PlayerWindow(os.path.join(folder, "doc.json"), "t", tools)
    win.worker.stop()
    win.timer.stop()
    job = os.path.join(folder, "job.json")
    with open(job, "w", encoding="utf-8") as f:
        json.dump(bare.job(win.doc, doc.video, {t.__name__.rsplit(".", 1)[-1]: t for t in tools}, os.path.join(folder, "bare.pkl")), f)
    win.close()
    assert bare.main(job) == 0
    with open(out, "w", encoding="utf-8") as f:
        json.dump(built, f)


if __name__ == "__main__":
    _built(*sys.argv[1:])
