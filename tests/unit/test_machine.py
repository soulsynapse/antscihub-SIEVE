"""The memory resolver reports the allocation, never the machine.

The failure guarded throughout is the resource-ledger item's H1 kill case: a
resolver that silently falls through to "machine total" inside a 16 GB job
step on a 512 GB node — the difference between a bounded session and an OOM
kill. So every test is about *which* reading wins, not about numbers being big.
"""

from __future__ import annotations

from pathlib import Path

from sieve.mutual.machine import (
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
    """A unified-hierarchy cgroup tree: the process lives in `<mount>/job`."""
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
    """The kill number outranks the scheduler's word and the machine's total.

    The environment below also declares a (larger) Slurm allocation, so this
    fails if precedence ever inverts — the case where a session sizes itself
    against `--mem` while a tighter cgroup is what actually kills it.
    """
    # Deliberately not a round number, so a coincidental machine with exactly
    # this much RAM cannot make the fallthrough assertion pass by accident.
    limit = 16 * GIB + 4096
    mount, proc = _v2_fixture(tmp_path, leaf=str(limit), root="max")
    resolved = available_memory(
        cgroup_mount=mount, proc_cgroup=proc, environ={"SLURM_MEM_PER_NODE": "262144"}
    )
    assert resolved == limit
    assert resolved != physical_memory()


def test_an_ancestor_limit_binds_even_when_the_leaf_says_max(tmp_path: Path) -> None:
    """A job step's own cgroup often carries `max` while the job-level parent
    holds the real number; reading only the leaf is the silent-fallthrough bug
    wearing a subtler face."""
    mount, proc = _v2_fixture(tmp_path, leaf="max", root=str(8 * GIB))
    assert available_memory(cgroup_mount=mount, proc_cgroup=proc, environ={}) == 8 * GIB


def test_a_cgroup_v1_sentinel_is_no_limit_not_a_huge_allocation(tmp_path: Path) -> None:
    """v1 spells "unlimited" as a number near 2**63 rather than by omission.

    Taken literally it would size every share against nine exabytes, which is
    the mirror image of the fallthrough bug: not an OOM kill but a ledger that
    believes it may hold anything. A real v1 limit in the same tree must still
    be honoured.
    """
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
    """`SLURM_MEM_PER_NODE` is megabytes; per-CPU multiplies by the CPUs this
    process actually has, which is the same allocation-not-machine reading the
    CPU resolver already makes."""
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
    """With nothing binding, the allocation is the machine — the workstation
    case, asserted against the platform reading itself so the integration
    claim in the ledger item holds on the machine running this test."""
    missing = tmp_path / "does-not-exist"
    resolved = available_memory(cgroup_mount=missing, proc_cgroup=missing, environ={})
    assert resolved == physical_memory()
    assert resolved >= 1 * GIB


def test_the_session_rss_reading_is_real_and_monotone_in_allocation() -> None:
    """A live process reads its own memory, and holding more shows up.

    The second half is what distinguishes an actual reading from a constant:
    allocate 64 MB, touch it so it is resident, and the reading must move by
    at least most of it. The lower bound is deliberately loose — the interp
    may free other things meanwhile — but a sampler returning a cached or
    fabricated number fails it every time.
    """
    before = process_memory_bytes()
    assert before > 64 * MIB  # a Python process with numpy loaded holds more

    slab = bytearray(64 * MIB)
    slab[::4096] = b"x" * len(slab[::4096])  # touch every page
    after = process_memory_bytes()
    assert after - before > 32 * MIB
    del slab


def test_the_class_map_covers_the_allocation_and_nothing_outside_it() -> None:
    """Every CPU this process may use has a class, and no other CPU appears.

    A map naming cores outside the allocation is not a cosmetic error: its
    first consumer builds affinity masks out of these keys
    (`bench/sweep.py`), and a mask naming an unavailable core is refused by
    the OS rather than trimmed.
    """
    assert tuple(cpu_classes()) == available_cpu_ids()
    assert available_cpus() == len(available_cpu_ids())


def test_an_os_that_publishes_nothing_reports_one_class_rather_than_no_map() -> None:
    """The uniform-machine shape, which callers must be able to ask about.

    An empty map would make `len(set(...)) == 1` — the "are my cores
    fungible" question — raise or read as False on exactly the machines where
    the answer is "no evidence of difference".
    """
    assert set(cpu_classes().values()) != set()


def test_linux_capacities_become_ordinal_classes_keeping_only_the_ordering(
    tmp_path: Path,
) -> None:
    """Two big cores and two little ones, ranked, with the scale discarded.

    The kernel's capacity numbers are normalised per-machine, so 1024 and 460
    mean "fastest here" and "less than that" and nothing portable. Ranking is
    what makes two machines' readings comparable at all, and the assertion is
    on the ranks rather than on any arithmetic over the raw values.
    """
    for cpu, capacity in ((0, "460"), (1, "1024"), (2, "460"), (3, "1024")):
        node = tmp_path / f"cpu{cpu}"
        node.mkdir()
        (node / "cpu_capacity").write_text(capacity, encoding="utf-8")
    (tmp_path / "cpufreq").mkdir()  # a sibling entry with no capacity file

    assert dict(linux_cpu_classes(tmp_path)) == {0: 0, 1: 1, 2: 0, 3: 1}
