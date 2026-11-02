"""track's merge_ratio: two animals merging into one blob and parting are five ids, none shared across
the contact; with the ratio off the merged blob carries one of them on."""
from sieve_player.graph import Series
from tools import track
from tests.test_track import table


def meeting():
    """Two animals walk into each other at 4 px a row, are one blob of twice the area for three rows,
    and part."""
    rows = [table([(10 + 4 * r, 50), (90 - 4 * r, 50)]) for r in range(10)]
    for r in range(10, 13):
        t = table([(50, 50)])
        t["area"][0] = 32
        rows.append(t)
    rows += [table([(50 - 4 * (r - 12), 50), (50 + 4 * (r - 12), 50)]) for r in range(13, 21)]
    return rows


def ids(rows, lo, hi):
    return {int(i) for t in rows[lo:hi] for i in t["id"]}


def test_a_merge_and_a_split_each_start_new_ids_under_the_ratio_and_not_without_it():
    params = {**track.DEFAULTS, "max_step": 5.0, "lost_rows": 5, "min_rows": 1}
    rows = track.run(Series(meeting(), "k", 0, 30.0), {**params, "merge_ratio": 1.5})["rows"]
    before, during, after = ids(rows, 0, 10), ids(rows, 10, 13), ids(rows, 13, 21)
    assert len(before) == 2 and len(during) == 1 and len(after) == 2
    assert not (before & during) and not (during & after) and not (before & after)
    assert all(len(t) == 2 for t in rows[:10]) and all(len(t) == 2 for t in rows[13:])
    plain = track.run(Series(meeting(), "k", 0, 30.0), params)["rows"]
    assert ids(plain, 10, 13) <= ids(plain, 0, 10)
