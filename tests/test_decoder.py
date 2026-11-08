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
    bgr = d.read(3)
    assert bgr.shape == (48, 64, 3) and d.cached(3) is not None
    d.output = "gray"
    assert d.cached(3) is None and d.cache_bytes == 0
    f = d.read(3)
    assert f.shape == (48, 64) and f.dtype == np.uint8 and d.cached(3) is f
    assert d.luma and not d.limited and abs(int(f[0, 0]) - 3) <= 1   # the luma plane itself; MJPEG is full range
    assert np.abs(f.astype(int) - cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)).max() <= 2   # the ramp too: a switch mid-stream garbles columns
    assert d.cache_bytes == 4 * 48 * 64                      # gray rows only: the switch reopened at row 0 and read through
    d.output = "bgr"
    assert d.cached(3) is None and np.abs(d.read(3).astype(int) - bgr).max() <= 2
    with pytest.raises(ValueError):
        d.output = "hsv"


def test_a_raw_stream_is_refused_and_its_remux_opens_with_limited_range_luma(video, tmp_path, monkeypatch):
    import shutil
    import subprocess
    import sieve_player.decoder as decoder
    from sieve_player.decoder import probe
    monkeypatch.setattr(decoder, "QUIET", True)
    ffmpeg = shutil.which("ffmpeg") or pytest.skip("no ffmpeg to write a raw stream")
    raw, mp4 = tmp_path / "v.h264", tmp_path / "v.mp4"
    subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "10",
                          "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv",   # as a camera writes it
                          "-c:v", "libx264", "-g", "4", "-bf", "0", "-f", "h264", str(raw)])   # no B-frames, as the Pi 4 encoder writes; see docs/findings/2026-11-04-raw-remux.md
    with pytest.raises(IOError, match="no index.*remux.*v.mp4"):
        Decoder(raw)
    with pytest.raises(IOError, match="no index"):
        probe(raw)
    subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-framerate", "30", "-i", str(raw), "-c", "copy", str(mp4)])
    d = Decoder(mp4, cache_bytes=1)                    # the last row only, so a row behind is a decode
    assert d.count == 10 and probe(mp4)[3] == 10 and abs(d.fps - 30.0) < 0.01   # the framerate given to the remux, on mp4's timescale
    assert d.read(7).shape[:2] == (48, 64) and d.decodes == 8 and d.seeks == 0
    d.output = "gray"                                  # reopens at the top, so row 2 is a step
    g = d.read(2)
    assert g.shape == (48, 64) and d.seeks == 0 and d.decodes == 11
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
    assert d.count == 300 and d.read(0)[0, 0, 0] == 0 and d.count == 300   # a read after the end seeks; it never steps the dead capture and reads its failure as row -1
    d.close()


def test_a_stream_ending_short_of_the_container_is_said_once_on_stderr(video, tmp_path, capsys):
    """The header's claim stands until a read fails; the correction is the one line that says where
    and when, since C-level stderr is hushed; a container that seeks exactly is never called inexact."""
    short = tmp_path / "short.avi"
    short.write_bytes(video.read_bytes()[: video.stat().st_size // 2])
    d = Decoder(short, cache_bytes=64 * 48 * 3)       # one frame: a read after the failure seeks rather than hits
    claimed = d.count
    with pytest.raises(IndexError):
        for r in range(claimed):
            d.read(r)
    err = capsys.readouterr().err
    assert 0 < d.count < claimed and f"ended at row {d.count} of the container's {claimed}" in err and " s; the count is now" in err
    d.read(0)
    assert "inexactly" not in capsys.readouterr().err and d.seeks == 1
    d.close()
