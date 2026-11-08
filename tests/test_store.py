"""The store: where its folder is resolved from and that the choice outlives the call, the sidecar's fields reading back, and what the display reads of a folder that can and cannot be written."""
import os

from sieve_player import document, store


def test_the_folder_is_chosen_else_the_environment_else_the_default(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "CHOICE", str(tmp_path / "app" / "store.txt"))
    monkeypatch.delenv(store.STORE_ENV, raising=False)
    assert store.folder() == os.path.join(store.app_folder(), "store")
    monkeypatch.setenv(store.STORE_ENV, str(tmp_path / "env"))
    assert store.folder() == str(tmp_path / "env") and store.current() == store.Store(str(tmp_path / "env"))
    assert store.choose(tmp_path / "picked") == ""
    assert store.folder() == str(tmp_path / "picked") and (tmp_path / "picked").is_dir()
    (tmp_path / "picked" / "a-file").write_bytes(b"")
    assert store.choose(tmp_path / "picked" / "a-file" / "under") and store.folder() == str(tmp_path / "picked")


def test_the_sidecar_reads_every_field_back(tmp_path):
    key = "0123456789abcdef"
    s, none = store.Store(str(tmp_path)), store.Store(str(tmp_path / "none"))
    (tmp_path / (key + ".mp4")).write_bytes(b"clip")
    side = store.Sidecar(key, "gray", "ants.json", "bake", [0, 589], 1, 59.94, 59.94, [540, 960], "standard")
    wrote = s.write_sidecar(side)
    back = s.sidecar(key)
    assert back == wrote and back != side and back.written and back.commit == store.commit()
    assert back.bake(590) == document.Bake(key, "gray", False, (0, 589), 1, 59.94, 59.94, (540, 960), 590) and back.bake(590).aligned
    assert s.sidecar("none") is None and not list(tmp_path.glob("*.part"))
    assert s.absent(back.bake(590)) == "" and none.absent(back.bake(590)).startswith(f"bake {key} is not in the store")
    doc = document.Document(nodes=[document.Node("bake", "bake", mode=document.BAKED, baked=back.bake(590))])
    assert s.missing(doc) == {} and list(none.missing(doc)) == ["bake"]
    assert s.place(key, ".mp4") == str(tmp_path / (key + ".mp4"))
    assert s.held() == 4 + os.path.getsize(s.sidecar_path(key))
    (tmp_path / "bad.sieve.json").write_text("{}", encoding="utf-8")
    assert s.sidecar("bad") is None


def test_status_reads_without_writing_and_probe_refuses_a_folder_that_cannot_be_written(tmp_path):
    s = store.Store(str(tmp_path))
    (tmp_path / "f").write_bytes(b"12345")
    held, free = s.status()
    assert held == 5 and free > 0
    (tmp_path / "k.mp4.ab12.part").write_bytes(b"1234567")
    assert s.strays() == (1, 7) and s.held() == 12
    unborn = store.Store(str(tmp_path / "not" / "yet"))
    assert unborn.status()[0] == 0 and unborn.free() > 0 and unborn.strays() == (0, 0) and not (tmp_path / "not").exists()
    under = store.Store(str(tmp_path / "f" / "under"))
    assert under.probe().startswith(str(tmp_path / "f" / "under")) and s.probe() == ""
    assert store.fmt_bytes(0) == "0 B" and store.fmt_bytes(1536) == "1.5 KB" and store.fmt_bytes(3 << 30) == "3.0 GB"
