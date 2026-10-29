"""flow, speed, agreement: a blob moved one column right reads u = +1 and v = 0 where it is, in px/s by the
fps, agreeing with itself in its cell; where nothing moved the solve is degenerate and reads zero, not measured."""
import numpy as np

from tools import agreement, flow, speed

yy, xx = np.mgrid[:32, :32]
blob = lambda cx: 100.0 * np.exp(-((xx - cx) ** 2 + (yy - 16) ** 2) / 18.0)  # noqa: E731
D = np.stack([blob(14), blob(15)]).astype(np.float32)
frames = lambda r: D[r]  # noqa: E731


def test_a_blob_moved_one_column_reads_u_one_and_zero_where_nothing_moved():
    f = flow.run(frames, 1, {"sigma": 2.0})
    assert f.shape == (32, 32, 2) and f.dtype == np.float32
    u, v = f[12:20, 11:19, 0], f[12:20, 11:19, 1]          # inside the blob
    assert abs(u.mean() - 1.0) < 0.15 and abs(v).max() < 0.15
    assert not f[:4, :4].any() and not flow.run(frames, 0, {"sigma": 2.0}).any()


class Fed:
    """What a frame tool gets: callable by row, with the fps on it."""
    fps = 30.0

    def __init__(self, a):
        self.a = a

    def __call__(self, r):
        return self.a


def test_speed_is_the_magnitude_by_the_fps():
    field = np.zeros((4, 4, 2), np.float32)
    field[1, 1] = (3.0, 4.0)
    out = speed.run(Fed(field), 1, {})
    assert out.dtype == np.float32 and out[1, 1] == 150.0 and out.sum() == 150.0


def test_agreement_is_one_where_the_blob_moved_as_one_and_zero_where_nothing_was_measured():
    f = flow.run(frames, 1, {"sigma": 2.0})
    out = agreement.run(lambda r: f, 1, {"block": 16})
    assert out.shape == (2, 2) and out.dtype == np.float32 and out.max() > 0.9   # the blob's cell
    field = np.zeros((4, 4, 2), np.float32)
    field[0, 0], field[0, 1] = (1.0, 0.0), (-2.0, 0.0)      # two pixels moving opposite ways cancel
    field[2, 2] = (0.0, 5.0)                                 # one pixel agrees with itself
    out = agreement.run(lambda r: field, 1, {"block": 2})
    assert out.tolist() == [[0.0, 0.0], [0.0, 1.0]]
    assert 0.0 <= out.min() and out.max() <= 1.0
