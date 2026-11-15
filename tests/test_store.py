"""The store: where its folder is resolved from, that a choice outlives the call and a refused one changes nothing, and what is read of a folder."""
import os

from sieve_player import store


def test_the_folder_is_chosen_else_the_environment_else_the_default(tmp_path, monkeypatch):
    monkeypatch.delenv(store.STORE_ENV)
    assert store.folder() == os.path.join(store.app_folder(), "store")
    monkeypatch.setenv(store.STORE_ENV, str(tmp_path / "env"))
    assert store.folder() == str(tmp_path / "env") and not (tmp_path / "env").exists()
    assert store.choose(tmp_path / "picked") == ""
    assert store.folder() == str(tmp_path / "picked") and (tmp_path / "picked").is_dir()
    (tmp_path / "picked" / "a-file").write_bytes(b"12345")
    assert store.choose(tmp_path / "picked" / "a-file" / "under") and store.folder() == str(tmp_path / "picked")
    (tmp_path / "picked" / "footage").mkdir()
    (tmp_path / "picked" / "footage" / ("clip" + store.PART)).write_bytes(b"1234567")
    total, free = store.disk(str(tmp_path / "not" / "yet"))
    assert store.held(store.folder()) == (12, 1, 7) and store.held(str(tmp_path / "not")) == (0, 0, 0) and 0 < free <= total
