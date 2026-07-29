







from __future__ import annotations

from pathlib import Path

from sieve.core.machine import (
    available_cpu_ids,
    available_cpus,
    available_memory,
    cpu_classes,
    linux_cpu_classes,
    physical_memory,
    process_memory_bytes,
)

GIB = 1024**3
MIB = 1024**2


def _v2_fixture(tmp_path: Path, *, leaf: str | None, root: str | None) -> tuple[Path, Path]:

    mount = tmp_path / "cgroup"
    (mount / "job").mkdir(parents=True)
    if leaf is not None:
        (mount / "job" / "memory.max").write_text(leaf, encoding="utf-8")
    if root is not None:
        (mount / "memory.max").write_text(root, encoding="utf-8")
    proc = tmp_path / "proc_cgroup"
    proc.write_text("0::/job\n", encoding="utf-8")
    return mount, proc


def test_a_cgroup_v2_limit_wins_over_everything(tmp_path: Path) -> None:








    limit = 16 * GIB + 4096
    mount, proc = _v2_fixture(tmp_path, leaf=str(limit), root="max")
    resolved = available_memory(
        cgroup_mount=mount, proc_cgroup=proc, environ={"SLURM_MEM_PER_NODE": "262144"}
    )
    assert resolved == limit
    assert resolved != physical_memory()


def test_an_ancestor_limit_binds_even_when_the_leaf_says_max(tmp_path: Path) -> None:



    mount, proc = _v2_fixture(tmp_path, leaf="max", root=str(8 * GIB))
    assert available_memory(cgroup_mount=mount, proc_cgroup=proc, environ={}) == 8 * GIB


def test_a_cgroup_v1_sentinel_is_no_limit_not_a_huge_allocation(tmp_path: Path) -> None:







    mount = tmp_path / "cgroup"
    (mount / "memory" / "job").mkdir(parents=True)
    proc = tmp_path / "proc_cgroup"
    proc.write_text("3:memory:/job\n", encoding="utf-8")

    limit_file = mount / "memory" / "job" / "memory.limit_in_bytes"
    limit_file.write_text(str(9223372036854771712), encoding="utf-8")
    unlimited = available_memory(cgroup_mount=mount, proc_cgroup=proc, environ={})
    assert unlimited == physical_memory()

    limit_file.write_text(str(4 * GIB), encoding="utf-8")
    assert available_memory(cgroup_mount=mount, proc_cgroup=proc, environ={}) == 4 * GIB


def test_the_scheduler_is_consulted_only_when_no_cgroup_answers(tmp_path: Path) -> None:



    missing = tmp_path / "does-not-exist"
    per_node = available_memory(
        cgroup_mount=missing, proc_cgroup=missing, environ={"SLURM_MEM_PER_NODE": "16000"}
    )
    assert per_node == 16000 * MIB

    per_cpu = available_memory(
        cgroup_mount=missing, proc_cgroup=missing, environ={"SLURM_MEM_PER_CPU": "4G"}
    )
    assert per_cpu == 4 * GIB * available_cpus()


def test_the_desktop_answer_is_physical_memory_and_it_is_a_real_number(tmp_path: Path) -> None:



    missing = tmp_path / "does-not-exist"
    resolved = available_memory(cgroup_mount=missing, proc_cgroup=missing, environ={})
    assert resolved == physical_memory()
    assert resolved >= 1 * GIB


def test_the_session_rss_reading_is_real_and_monotone_in_allocation() -> None:








    before = process_memory_bytes()
    assert before > 64 * MIB

    slab = bytearray(64 * MIB)
    slab[::4096] = b"x" * len(slab[::4096])
    after = process_memory_bytes()
    assert after - before > 32 * MIB
    del slab


def test_the_class_map_covers_the_allocation_and_nothing_outside_it() -> None:







    assert tuple(cpu_classes()) == available_cpu_ids()
    assert available_cpus() == len(available_cpu_ids())


def test_an_os_that_publishes_nothing_reports_one_class_rather_than_no_map() -> None:






    assert set(cpu_classes().values()) != set()


def test_linux_capacities_become_ordinal_classes_keeping_only_the_ordering(
    tmp_path: Path,
) -> None:







    for cpu, capacity in ((0, "460"), (1, "1024"), (2, "460"), (3, "1024")):
        node = tmp_path / f"cpu{cpu}"
        node.mkdir()
        (node / "cpu_capacity").write_text(capacity, encoding="utf-8")
    (tmp_path / "cpufreq").mkdir()

    assert dict(linux_cpu_classes(tmp_path)) == {0: 0, 1: 1, 2: 0, 3: 1}
