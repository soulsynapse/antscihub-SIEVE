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
        f = np.full((48, 64, 3), i % 256, np.uint8)
        f[40:] = np.linspace(0, 255, 64, dtype=np.uint8)[None, :, None]   # a ramp the range fit can read; [0, 0] stays i
        w.write(f)
    w.release()
    return path


def test_gray_output_is_converted_before_the_cache_and_a_switch_empties_it(video, monkeypatch):
    import sieve_player.decoder as decoder
    monkeypatch.setattr(decoder, "QUIET", True)
    d = Decoder(video)
    assert d.read(3).shape == (48, 64, 3) and d.cached(3) is not None
    d.output = "gray"
    assert d.cached(3) is None and d.cache_bytes == 0
    f = d.read(3)
    assert f.shape == (48, 64) and f.dtype == np.uint8 and d.cached(3) is f
    assert d.luma and not d.limited and abs(int(f[0, 0]) - 3) <= 1   # the luma plane itself; MJPEG is full range
    assert 0 < d.cache_bytes <= 2 * 48 * 64                  # gray rows only: the seek landed a row short and read through
    d.output = "bgr"
    assert d.cached(3) is None and d.read(3).shape == (48, 64, 3)
    with pytest.raises(ValueError):
        d.output = "hsv"
    d.scale = 0.5
    assert d.cached(3) is None and d.read(3).shape == (24, 32, 3) and d.cached(3).shape == (24, 32, 3)
    d.output = "gray"
    assert d.read(3).shape == (24, 32)
    with pytest.raises(ValueError):
        d.scale = 1.5


def test_a_raw_stream_is_counted_by_packet_and_seeks_from_the_top(video, tmp_path, monkeypatch):
    import shutil
    import subprocess
    import sieve_player.decoder as decoder
    from sieve_player.decoder import probe
    monkeypatch.setattr(decoder, "QUIET", True)
    ffmpeg = shutil.which("ffmpeg") or pytest.skip("no ffmpeg to write a raw stream")
    raw = tmp_path / "v.h264"
    subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "10",
                          "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv",   # as a camera writes it
                          "-c:v", "libx264", "-g", "4", "-f", "h264", str(raw)])
    d = Decoder(raw)
    assert not d.indexed and d.count == 10 and probe(raw)[3] == 10
    assert d.read(7).shape[:2] == (48, 64) and d.decodes == 8 and d.seeks == 0
    d.output = "gray"                                  # empties the cache, so row 2 is behind the cursor
    g = d.read(2)
    assert g.shape == (48, 64) and d.seeks == 1 and d.decodes == 11   # back means from the top
    assert d.luma and d.limited                        # libx264 writes limited range: the plane is expanded to full
    assert abs(int(g[0, 0]) - 2) <= 3                  # row 2 was written as 2 everywhere
    d.output = "luma"
    y = d.read(2)
    assert y.shape == (48, 64) and 14 <= y[0, 0] <= 19 # the plane as is: 2 sits at 16 + 2 * 219 / 255
    with pytest.raises(IndexError):
        d.read(10)
    assert d.count == 10


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
