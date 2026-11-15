import pytest

from sieve_player import store
from sieve_player.worker import Worker


@pytest.fixture(autouse=True)
def in_store(tmp_path, monkeypatch):
    """The store's folder and the file its choice is kept in are under tmp_path for the test, so
    none reads or writes the user's."""
    monkeypatch.setattr(store, "CHOICE", str(tmp_path / "app" / "store.txt"))
    monkeypatch.setenv(store.STORE_ENV, str(tmp_path / "store"))
    return tmp_path / "store"


@pytest.fixture(autouse=True)
def unasked(monkeypatch):
    """No player window a test leaves changed waits on a dialog: the answer is "discard" unless the
    test sets its own."""
    from sieve_player.window import PlayerWindow
    monkeypatch.setattr(PlayerWindow, "ask_unsaved", lambda self: "discard")


@pytest.fixture(autouse=True)
def reaped(monkeypatch):
    """Every worker a test made is stopped at teardown and its graph closed with its decoder, so an
    assertion failing between a start and the test's own stop() leaves no thread reading a clip the
    next test's tmp_path cleanup would then fail to remove on Windows."""
    made = []
    init = Worker.__init__

    def register(self, *args, **kwargs):
        init(self, *args, **kwargs)
        made.append(self)
    monkeypatch.setattr(Worker, "__init__", register)
    yield
    for w in made:
        if w.isRunning():
            w.stop()
        w.graph.close()
        close = getattr(w.graph.decoder, "close", None)
        if close is not None:
            close()
