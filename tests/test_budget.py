"""The limits shared out of a machine's memory, the machine handed in."""
from sieve_player.budget import CEILINGS, HELD_AT_ONCE, limits

GB = 2**30


def _total(got):
    return sum(got[k] * HELD_AT_ONCE[k] for k in got)


def test_a_machine_with_room_gets_the_ceilings():
    assert limits(64 * GB, {}) == CEILINGS


def test_a_small_machine_shares_half_in_the_ceilings_proportions():
    got = limits(4 * GB, {})
    assert _total(got) <= 2 * GB
    scale = got["memo"] / CEILINGS["memo"]
    assert scale < 1
    assert all(abs(got[k] - CEILINGS[k] * scale) <= 1 for k in CEILINGS)


def test_the_variables_win():
    got = limits(4 * GB, {"SIEVE_MEMO_GB": "3", "SIEVE_CACHE_GB": "0"})
    assert got["memo"] == 3 * GB and got["cache"] == limits(4 * GB, {})["cache"]
    assert limits(4 * GB, {"SIEVE_MEMORY_GB": "64"}) == CEILINGS
