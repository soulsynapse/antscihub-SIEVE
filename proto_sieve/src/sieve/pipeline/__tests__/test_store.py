"""Proof for pipeline/store.py's secret: a name resolves to one file under
the given directory, and save/load round-trips the pipeline value.
"""

from __future__ import annotations

import pytest

from proto_sieve.src.sieve.pipeline import Pipeline, Step
from proto_sieve.src.sieve.pipeline.store import list_pipelines, load, save


def _pipeline() -> Pipeline:
    return Pipeline(
        source="rep3_intermittent_crop",
        steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
    )


def test_save_then_load_round_trips_the_value(tmp_path):
    save("first_crop", _pipeline(), directory=tmp_path)
    assert load("first_crop", directory=tmp_path) == _pipeline()


def test_save_writes_one_json_file_named_for_the_pipeline(tmp_path):
    path = save("first_crop", _pipeline(), directory=tmp_path)
    assert path == tmp_path / "first_crop.json"
    assert path.is_file()


def test_list_pipelines_returns_saved_names_sorted(tmp_path):
    save("b_crop", _pipeline(), directory=tmp_path)
    save("a_crop", _pipeline(), directory=tmp_path)
    assert list_pipelines(directory=tmp_path) == ["a_crop", "b_crop"]


def test_list_pipelines_on_a_missing_directory_is_empty(tmp_path):
    assert list_pipelines(directory=tmp_path / "does_not_exist") == []


@pytest.mark.parametrize("name", ["../escape", "a/b", "a\\b"])
def test_a_name_cannot_escape_the_pipelines_directory(tmp_path, name):
    with pytest.raises(ValueError):
        save(name, _pipeline(), directory=tmp_path)
