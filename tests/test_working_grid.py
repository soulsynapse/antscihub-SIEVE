from __future__ import annotations

import subprocess
import sys

import pytest

from antscihub_sieve.application.working_grid import (
    BlockIntent,
    WorkingGridSettings,
    resolve_working_grid,
)


def test_working_grid_contract_imports_without_qt() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import antscihub_sieve.application.working_grid; "
                "assert not any(n == 'PyQt6' or n.startswith('PyQt6.') "
                "for n in sys.modules)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_native_auto_grid_covers_partial_edges_exactly() -> None:
    grid = resolve_working_grid(411, 428)
    assert grid.requested_downsample == 1.0
    assert (grid.work_width, grid.work_height) == (411, 428)
    assert grid.block_intent is BlockIntent.AUTO
    assert grid.base_source_block == 64
    assert grid.requested_block_size is None
    assert grid.resolved_block_size == 64
    assert (grid.rows, grid.columns) == (7, 7)
    assert (grid.right_edge_width, grid.bottom_edge_height) == (27, 44)

    bottom_right = grid.block_bounds(6, 6)
    assert (
        bottom_right.x0,
        bottom_right.y0,
        bottom_right.x1,
        bottom_right.y1,
    ) == (384, 384, 411, 428)
    assert grid.block_area(6, 6) == 27 * 44
    assert grid.block_area_weight(6, 6) == pytest.approx(
        (27 * 44) / (64 * 64)
    )
    assert grid.block_area_weight(0, 0) == 1.0


def test_downsample_resolution_and_auto_source_footprint() -> None:
    grid = resolve_working_grid(
        411,
        428,
        WorkingGridSettings(downsample=0.5),
    )
    assert (grid.work_width, grid.work_height) == (206, 214)
    assert grid.resolved_block_size == 32
    assert (grid.rows, grid.columns) == (7, 7)
    assert (grid.right_edge_width, grid.bottom_edge_height) == (14, 22)
    assert grid.working_to_source_boundary(206, 214) == (411.0, 428.0)
    assert grid.working_to_source_boundary(32, 32) == pytest.approx(
        (32 * 411 / 206, 64.0)
    )


def test_python_half_ties_and_minimum_extent_are_pinned() -> None:
    half = resolve_working_grid(
        5,
        7,
        WorkingGridSettings(downsample=0.5),
    )
    assert (half.work_width, half.work_height) == (2, 4)

    tiny = resolve_working_grid(
        1,
        1,
        WorkingGridSettings(downsample=0.001),
    )
    assert (tiny.work_width, tiny.work_height) == (1, 1)
    assert tiny.resolved_block_size == 1
    assert (tiny.rows, tiny.columns) == (1, 1)


def test_explicit_block_is_fixed_in_working_pixels() -> None:
    grid = resolve_working_grid(
        100,
        50,
        WorkingGridSettings.explicit(80, downsample=0.5),
    )
    assert grid.block_intent is BlockIntent.EXPLICIT
    assert grid.requested_block_size == 80
    assert grid.base_source_block is None
    assert grid.resolved_block_size == 80
    assert (grid.rows, grid.columns) == (1, 1)
    assert grid.block_area_weight(0, 0) == pytest.approx(
        (50 * 25) / (80 * 80)
    )


@pytest.mark.parametrize(
    "settings",
    [
        WorkingGridSettings(downsample=0),
        WorkingGridSettings(downsample=-0.1),
        WorkingGridSettings(downsample=1.01),
        WorkingGridSettings(downsample=float("nan")),
        WorkingGridSettings(downsample=True),
        WorkingGridSettings(
            block_intent=BlockIntent.AUTO,
            explicit_block_size=2,
        ),
        WorkingGridSettings(
            block_intent=BlockIntent.EXPLICIT,
            explicit_block_size=None,
        ),
        WorkingGridSettings.explicit(0),
        WorkingGridSettings.explicit(-1),
        WorkingGridSettings.explicit(True),
    ],
)
def test_invalid_settings_fail(settings: WorkingGridSettings) -> None:
    with pytest.raises(ValueError):
        resolve_working_grid(10, 10, settings)


@pytest.mark.parametrize(("width", "height"), [(0, 1), (1, 0), (-1, 1), (True, 1)])
def test_invalid_source_extent_fails(width: int, height: int) -> None:
    with pytest.raises(ValueError):
        resolve_working_grid(width, height)


def test_block_and_boundary_access_reject_out_of_range_values() -> None:
    grid = resolve_working_grid(100, 100)
    with pytest.raises(IndexError):
        grid.block_bounds(-1, 0)
    with pytest.raises(IndexError):
        grid.block_bounds(0, grid.columns)
    with pytest.raises(ValueError):
        grid.working_to_source_boundary(101, 0)
