"""A video read one frame at a time by index, through OpenCV's FFmpeg backend as the player's Decoder
opens it, so a frame here has the shape a region is later handed: the plate."""
import cv2

EXACT_DECODE_BELOW = 64   # an .MTS seek inside the first group of pictures lands most of it away; decode forward there
READ_THROUGH = 12         # frames ahead it is cheaper to step through than to seek over


class Video:
    """BGR frames at the native size; `plate` is (height, width), `count` what the container claims.
    Raises IOError on a file that will not open, whose container claims no frames, or whose first
    frame does not decode. A seek past the first group of pictures may land near the asked frame
    rather than on it."""

    def __init__(self, path):
        self.path = str(path)
        self._cap = self._open()
        n = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ok, first = self._cap.read()
        if n <= 0 or not ok:
            self._cap.release()
            raise IOError(f"{self.path} has no frames to draw over: a raw stream wants remuxing into a container")
        self.count, self.fps = n, self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.plate = first.shape[:2]
        self._pos, self._frame = 0, first

    def _open(self):
        cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            raise IOError(f"cannot open {self.path}")
        return cap

    def read(self, index):
        """The frame at `index`, clamped to the claimed count; IOError when it does not decode."""
        index = min(max(0, index), self.count - 1)
        if index == self._pos:
            return self._frame
        ahead = index - self._pos if self._pos is not None else -1
        if 0 < ahead <= READ_THROUGH:
            skip = ahead - 1
        elif index < EXACT_DECODE_BELOW:
            self._cap.release()
            self._cap, skip = self._open(), index
        else:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            skip = 0
        for _ in range(skip):
            self._cap.grab()
        ok, f = self._cap.read()
        if not ok:
            self._pos = None
            raise IOError(f"frame {index} of {self.path} does not decode")
        self._pos, self._frame = index, f
        return f

    def close(self):
        self._cap.release()
