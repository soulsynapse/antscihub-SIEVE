# Remux and re-encode: what each costs to make and what the decoder then pays per step and per seek

2026-11-04, on v5-blob-detection, this laptop (RTX 4060, the venv's cv2 and the system ffmpeg); the
script is docs/findings/experiments/2026-11-04-remux-encode-and-seek.py. The source is the crossings
clip, video-tests/00000_168-178.mp4, 1920×1080 at 59.94 fps, 590 rows, H.264 with B-frames as the
Sony wrote it, extracted to a raw stream of 26.5 MB and then remuxed or re-encoded each way with
`-framerate` given. For each result: wall time of the ffmpeg run, file size, the container's claimed
count against the rows cv2 decodes, the mean cost of a sequential read, and the mean cost of a seek
to a random row and the read after it, twenty seeks. One clip, ten seconds, so the encode times
carry ffmpeg's start-up and the small differences among them are noise.

| variant | encode s | MB | claimed | decoded | step ms | seek ms |
|---|---|---|---|---|---|---|
| copy, mp4 | 0.1 | 26.5 | 590 | 588 | 2.5 | 117 |
| copy, mkv | failed: unknown timestamps | | | | | |
| x264 ultrafast crf 18 | 0.7 | 12.7 | 590 | 590 | 3.0 | 40 |
| x264 medium crf 18 | 2.9 | 7.2 | 590 | 590 | 3.1 | 68 |
| x264 medium crf 18, g 10, no B | 2.1 | 11.9 | 590 | 590 | 2.9 | 23 |
| x264 all-intra crf 18 | 1.3 | 30.7 | 590 | 590 | 3.0 | 19 |
| h264_nvenc p4 cq 18 | 1.5 | 21.0 | 590 | 590 | 3.0 | 106 |
| h264_nvenc p4 cq 18, g 10, no B | 1.4 | 38.2 | 590 | 590 | 2.9 | 45 |
| hevc_nvenc cq 18 | 1.5 | 18.1 | 590 | 590 | 3.0 | 188 |
| mjpeg q 3, avi | 0.6 | 45.4 | 590 | 590 | 5.3 | 40 |
| ffv1 lossless, mkv | 4.4 | 351.9 | 590 | 590 | 5.3 | 235 |

Re-encoding is cheap on this machine: libx264 at its medium preset did ten seconds of 1080p60 in
under three, about 200 rows a second, so a thirty-hour Pi session at 1 fps, 108,000 rows, is nine
minutes, and ultrafast a quarter of that. The GPU encoders were no faster on a clip this short.

The step cost is the same for every H.264 and HEVC variant, 3 ms a row at 1080p, and nearly double
for MJPEG and FFV1, so an intra-only codec buys nothing on the sequential walk here. What the
format decides is the seek, which is a decode from the last keyframe: the camera's own keyframe
spacing costs 117 ms, a keyframe every ten rows 23 ms, every row 19 ms, and HEVC's long groups
188 ms. The decoder's own read-through rule weighs seek against step, so the keyframe spacing sets
how far ahead a jump still steps. Short groups cost size: a keyframe every ten rows is 12 MB
against 7 for the default spacing, and all-intra 31, more than the camera's file.

MP4 is the container: cv2 reads its exact row count from the index, where the raw stream claims
none and the mkv remux of a timestamp-less stream would not write at all without generated
timestamps. The copy's two missing rows are the B-frame tail docs/findings/2026-11-04-raw-remux.md
measured.

For the Pi cameras this says the lever is at capture, not after: `rpicam-vid --intra` sets the
keyframe spacing the recording script already exposes as the intra setting, and the hardware
encoder writes no B-frames, so a short intra period plus the upload worker's copy remux gives an
indexed, losslessly muxed file that seeks in about 20 ms, with no re-encode anywhere. Not measured:
a real camera segment, and footage at the Pi's rates, where a group of ten rows at 1 fps is ten
seconds of footage.
