"""The store: where its folder is resolved from and that the choice outlives the call, the sidecar's fields reading back, and what the display reads of a folder that can and cannot be written."""
import os

from sieve_player import store


def test_the_folder_is_chosen_else_the_environment_else_the_default(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "CHOICE", str(tmp_path / "app" / "store.txt"))
    monkeypatch.delenv(store.STORE_ENV, raising=False)
    assert store.folder() == os.path.join(store.app_folder(), "store")
    monkeypatch.setenv(store.STORE_ENV, str(tmp_path / "env"))
    assert store.folder() == str(tmp_path / "env")
    assert store.choose(tmp_path / "picked") == ""
    assert store.folder() == str(tmp_path / "picked") and (tmp_path / "picked").is_dir()
    (tmp_path / "picked" / "a-file").write_bytes(b"")
    assert store.choose(tmp_path / "picked" / "a-file" / "under") and store.folder() == str(tmp_path / "picked")


def test_the_sidecar_reads_every_field_back(tmp_path):
    key = "0123456789abcdef"
    (tmp_path / (key + ".mp4")).write_bytes(b"clip")
    fields = dict(kind="gray", document="ants.json", node="bake", rows=[0, 589], increment=1, fps=59.94, written_fps=59.94,
                  shape=[540, 960], quality="standard")
    wrote = store.write_sidecar(key, str(tmp_path), **fields)
    back = store.sidecar(key, str(tmp_path))
    assert back == wrote and tuple(back) == store.FIELDS and all(back[k] == v for k, v in fields.items())
    assert back["key"] == key and back["written"] and back["commit"] == store.commit()
    assert store.sidecar("none", str(tmp_path)) is None and not list(tmp_path.glob("*.part"))
    assert store.place(key, ".mp4", str(tmp_path)) == str(tmp_path / (key + ".mp4"))
    assert store.held(str(tmp_path)) == 4 + os.path.getsize(store.sidecar_path(key, str(tmp_path)))


def test_status_says_what_a_folder_holds_and_refuses_one_that_cannot_be_written(tmp_path):
    (tmp_path / "f").write_bytes(b"12345")
    path, held, free, why = store.status(str(tmp_path))
    assert (path, held, why) == (str(tmp_path), 5, "") and free > 0
    path, held, free, why = store.status(str(tmp_path / "f" / "under"))
    assert held == free == 0 and why.startswith(str(tmp_path / "f" / "under"))
    assert store.fmt_bytes(0) == "0 B" and store.fmt_bytes(1536) == "1.5 KB" and store.fmt_bytes(3 << 30) == "3.0 GB"
