"""The store: where its folder is resolved from and that the choice outlives the call, the sidecar's fields reading back, and what the display reads of a folder that can and cannot be written."""
import os

from sieve_player import document, store


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
    side = store.Sidecar(key, "gray", "ants.json", "bake", [0, 589], 1, 59.94, 59.94, [540, 960], "standard")
    wrote = store.write_sidecar(side, str(tmp_path))
    back = store.sidecar(key, str(tmp_path))
    assert back == wrote and back != side and back.written and back.commit == store.commit()
    assert back.bake(590) == document.Bake(key, "gray", False, (0, 589), 1, 59.94, 59.94, (540, 960), 590) and back.bake(590).aligned
    assert store.sidecar("none", str(tmp_path)) is None and not list(tmp_path.glob("*.part"))
    assert store.absent(back.bake(590), str(tmp_path)) == "" and store.absent(back.bake(590), str(tmp_path / "none")).startswith(f"bake {key} is not in the store")
    doc = document.Document(nodes=[document.Node("bake", "bake", mode=document.BAKED, baked=back.bake(590))])
    assert store.missing(doc, str(tmp_path)) == {} and list(store.missing(doc, str(tmp_path / "none"))) == ["bake"]
    assert store.place(key, ".mp4", str(tmp_path)) == str(tmp_path / (key + ".mp4"))
    assert store.held(str(tmp_path)) == 4 + os.path.getsize(store.sidecar_path(key, str(tmp_path)))
    (tmp_path / "bad.sieve.json").write_text("{}", encoding="utf-8")
    assert store.sidecar("bad", str(tmp_path)) is None


def test_status_says_what_a_folder_holds_and_refuses_one_that_cannot_be_written(tmp_path):
    (tmp_path / "f").write_bytes(b"12345")
    path, held, free, why = store.status(str(tmp_path))
    assert (path, held, why) == (str(tmp_path), 5, "") and free > 0 and store.free(str(tmp_path)) > 0
    (tmp_path / "k.mp4.ab12.part").write_bytes(b"1234567")
    assert store.strays(str(tmp_path)) == (1, 7) and store.held(str(tmp_path)) == 12 and store.strays(str(tmp_path / "none")) == (0, 0)
    path, held, free, why = store.status(str(tmp_path / "f" / "under"))
    assert held == free == 0 and why.startswith(str(tmp_path / "f" / "under"))
    assert store.fmt_bytes(0) == "0 B" and store.fmt_bytes(1536) == "1.5 KB" and store.fmt_bytes(3 << 30) == "3.0 GB"
