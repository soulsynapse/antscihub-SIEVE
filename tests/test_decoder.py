"""Two cursors on one file: the walk's only steps, the scrub's takes the jumps; a short jump reads
through; a seek lands a row short so row - 1 after row is a step, not a second seek."""
import cv2
import numpy as np
import pytest

from sieve_player.decoder import Decoder


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    path = tmp_path_factory.mktemp("v") / "v.avi"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (64, 48))
    for i in range(300):
        w.write(np.full((48, 64, 3), i % 256, np.uint8))
    w.release()
    return path


def test_gray_output_is_converted_before_the_cache_and_a_switch_empties_it(video):
    d = Decoder(video)
    assert d.read(3).shape == (48, 64, 3) and d.cached(3) is not None
    d.output = "gray"
    assert d.cached(3) is None and d.cache_bytes == 0
    f = d.read(3)
    assert f.shape == (48, 64) and f.dtype == np.uint8 and d.cached(3) is f
    assert 0 < d.cache_bytes <= 2 * 48 * 64                  # gray rows only: the seek landed a row short and read through
    d.output = "bgr"
    assert d.cached(3) is None and d.read(3).shape == (48, 64, 3)
    with pytest.raises(ValueError):
        d.output = "hsv"


def test_scrub_leaves_the_walk_cursor_alone(video):
    d = Decoder(video, cache_bytes=10 * 64 * 48 * 3)
    for r in range(5):
        d.read(r)
    assert d.seeks == 0
    with d.scrub():
        d.read(200)
        assert d.seeks == 1
        assert d.read(199)[0, 0, 0] == 199 and d.seeks == 1   # landed short: row - 1 was read through
    d.read(5)
    assert d.seeks == 1                                        # the walk stepped on from where it was
    k = 6 + int(d._read_through())                             # as far ahead as the measured seek still beats stepping
    assert d.read(k)[0, 0, 0] == k % 256 and d.seeks == 1
    d.read(250)
    assert d.seeks == 2
    assert d.cached(0) is None and d.cached(250) is not None   # bytes bound the cache, oldest out
    with pytest.raises(IndexError):
        d.read(10_000)
    d.close()
