"""Two cursors on one file: the walk's only steps, the scrub's takes the jumps; a short jump reads
through; a seek lands a row short so row - 1 after row is a step, not a second seek."""
import cv2
import numpy as np
import pytest

from sieve_player.decoder import SLICE, Decoder, footage_print


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


def test_a_row_by_a_seek_is_the_row_a_walk_reads_where_the_plugin_says_another(video, tmp_path, monkeypatch):
    """A transport stream with B-frames: no seek lands before its second keyframe, and the plugin
    says of one to row 0 that it did. Then a file with twenty frames gone and their times kept, where
    a frame's time at the container's rate is another row than its place among the frames: a seek
    is numbered by that place, and the rows are the walk's. With a store set the table is kept
    there under the file's print, and is the table a process that has read no packet takes."""
    import shutil
    import subprocess
    ffmpeg = shutil.which("ffmpeg") or pytest.skip("no ffmpeg to write a transport stream")
    ts = tmp_path / "v.ts"
    subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "90", "-pix_fmt", "yuv420p",
                          "-c:v", "libx264", "-g", "30", "-bf", "2", "-f", "mpegts", str(ts)])
    walk = Decoder(ts)
    in_order = [walk.read(r) for r in range(90)]
    assert walk.seeks == 0
    walk.close()
    d = Decoder(ts, cache_bytes=1)                    # the last row only, so every row behind is a seek
    d.read(80)
    for r in (61, 45, 31, 30, 20, 5, 1, 0):
        assert np.array_equal(d.read(r), in_order[r]), r
    assert d.seeks == 9
    d.close()
    gap = tmp_path / "gap.mp4"
    subprocess.check_call([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "120", "-pix_fmt", "yuv420p",
                          "-vf", r"select=not(between(n\,20\,39))", "-fps_mode", "passthrough", "-c:v", "libx264", "-g", "30", str(gap)])
    import sieve_player.decoder as decoder
    monkeypatch.setattr(decoder, "STORE", lambda: str(tmp_path / "store"))
    walk = Decoder(gap)
    in_order = [walk.read(r) for r in range(100)]
    walk.close()
    d = Decoder(gap, cache_bytes=1)
    for r in (90, 70, 45, 21, 60, 5):
        assert np.array_equal(d.read(r), in_order[r]), r
    assert d.seeks == 6 and not d._counts_only
    kept = tmp_path / "store" / decoder.TIMES_DIR / f"{d.footage_print}.npy"
    assert np.array_equal(np.load(kept), d._times) and len(d._times) == 120
    np.save(kept, d._times[:7])
    decoder._times.clear()
    assert len(decoder.frame_times(gap)) == 7       # the kept table, and no reading of the packets
    decoder._times.clear()
    d.close()


def test_a_files_print_is_its_footages_wherever_it_lies_and_however_its_path_is_spelled(tmp_path):
    """The video node's key is of this and of no path, so a held run made of a file is found from
    a copy of it, on another machine and under another spelling."""
    body = bytes(range(256)) * (3 * SLICE // 256)
    a, b, c = tmp_path / "a.mp4", tmp_path / "sub" / "b.mp4", tmp_path / "c.mp4"
    b.parent.mkdir()
    a.write_bytes(body)
    b.write_bytes(body)
    c.write_bytes(body[:-1] + b"x")
    assert footage_print(a) == footage_print(b) == footage_print(str(a).replace("\\", "/")) == footage_print(tmp_path / "sub" / ".." / "a.mp4")
    assert footage_print(c) != footage_print(a) and footage_print(a) != footage_print(tmp_path / "absent.mp4")
