"""Proof for store/store.py's secret: a name resolves to one guarded path
under a directory, text round-trips through it, and repo_root() finds the
real repo root.
"""

from __future__ import annotations

import pytest

from proto_sieve.src.sieve.store import list_names, load_text, repo_root, save_text


def test_repo_root_is_the_directory_containing_pyproject_toml():
    root = repo_root()
    assert (root / "pyproject.toml").is_file()


def test_save_text_then_load_text_round_trips(tmp_path):
    save_text("first_crop", '{"a": 1}', tmp_path)
    assert load_text("first_crop", tmp_path) == '{"a": 1}'


def test_save_text_writes_the_named_file(tmp_path):
    path = save_text("first_crop", "x", tmp_path)
    assert path == tmp_path / "first_crop.json"
    assert path.is_file()


def test_list_names_returns_stems_sorted(tmp_path):
    save_text("b", "x", tmp_path)
    save_text("a", "x", tmp_path)
    assert list_names(tmp_path) == ["a", "b"]


def test_list_names_on_a_missing_directory_is_empty(tmp_path):
    assert list_names(tmp_path / "does_not_exist") == []


@pytest.mark.parametrize("name", ["../escape", "a/b", "a\\b"])
def test_a_name_cannot_escape_the_directory(tmp_path, name):
    with pytest.raises(ValueError):
        save_text(name, "x", tmp_path)


def test_suffix_is_not_hardcoded_to_json(tmp_path):
    path = save_text("notes", "not json at all", tmp_path, suffix=".txt")
    assert path == tmp_path / "notes.txt"
    assert load_text("notes", tmp_path, suffix=".txt") == "not json at all"
    assert list_names(tmp_path, suffix=".txt") == ["notes"]
