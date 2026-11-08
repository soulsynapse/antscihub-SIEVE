import pytest

from sieve_player import store
from sieve_player.worker import Worker


@pytest.fixture
def in_store(tmp_path, monkeypatch):
    """The store's folder under tmp_path for the test, so no bake lands in the user's."""
    folder = tmp_path / "store"
    monkeypatch.setattr(store, "folder", lambda: str(folder))
    return folder


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
