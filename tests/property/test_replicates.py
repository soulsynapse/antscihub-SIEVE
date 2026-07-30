"""`next_default_name` against name sets no example test would think to write.

The generator has to hold against names the user typed, not just against the
`Replicate N` series it produces itself — a replicate renamed to "Replicate 3"
by hand is indistinguishable from one that was born that way, and the next
default must not collide with it.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from sieve.core.replicates import DEFAULT_NAME_STEM, Replicate, ReplicateSet
from sieve.core.types import ROI

ROIS = st.builds(
    ROI,
    x=st.integers(min_value=0, max_value=4096),
    y=st.integers(min_value=0, max_value=4096),
    width=st.integers(min_value=1, max_value=4096),
    height=st.integers(min_value=1, max_value=4096),
)

#: Deliberately weighted towards names that look like generated ones, including
#: the near misses the regex has to reject: leading zeros, extra whitespace,
#: a different stem. Uniform text would almost never collide and would test
#: nothing.
NAMES = st.one_of(
    st.integers(min_value=1, max_value=20).map(lambda n: f"{DEFAULT_NAME_STEM} {n}"),
    st.sampled_from(
        [
            f"{DEFAULT_NAME_STEM} 01",
            f"{DEFAULT_NAME_STEM}  2",
            f"{DEFAULT_NAME_STEM} 3 ",
            f"{DEFAULT_NAME_STEM}",
            "replicate 4",
            "Dish 1",
            "",
        ]
    ),
    st.text(max_size=20),
)

REPLICATE_LISTS = st.lists(st.builds(Replicate, roi=ROIS, name=NAMES), max_size=30)


@given(replicates=REPLICATE_LISTS)
def test_next_default_name_never_collides(replicates: list[Replicate]) -> None:
    """Whatever is in the set, the proposed name is not already in it."""
    candidate = ReplicateSet(replicates).next_default_name()

    assert candidate not in {item.name for item in replicates}


@given(replicates=REPLICATE_LISTS, draws=st.integers(min_value=1, max_value=10))
def test_repeated_draws_never_collide_with_each_other(
    replicates: list[Replicate], draws: int
) -> None:
    """Drawing several boxes in a row is the path that actually runs.

    Each name is asked for after the previous one has been appended, which is
    what `replicate_tab` does, so a generator that ignored its own output would
    hand two boxes the same label.
    """
    replicate_set = ReplicateSet(replicates)
    issued: list[str] = []
    for _ in range(draws):
        name = replicate_set.next_default_name()
        issued.append(name)
        replicate_set.append(Replicate(roi=ROI(x=0, y=0, width=1, height=1), name=name))

    assert len(set(issued)) == draws
    assert len(issued) + len(replicates) == len(replicate_set)


@given(replicates=REPLICATE_LISTS)
def test_next_default_name_takes_the_lowest_free_number(replicates: list[Replicate]) -> None:
    """Gaps get reused — the reason this is not a monotonic counter.

    Stated as the minimality of the chosen number rather than as a scripted
    delete-then-redraw, so it holds for sets that were never built by drawing.
    """
    candidate = ReplicateSet(replicates).next_default_name()
    number = int(candidate.removeprefix(f"{DEFAULT_NAME_STEM} "))
    taken = {item.name for item in replicates}

    assert number >= 1
    assert all(f"{DEFAULT_NAME_STEM} {lower}" in taken for lower in range(1, number))
