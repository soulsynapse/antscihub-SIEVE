# SIEVE's walk runs nothing on the GPU

2026-11-12, on v5-monitor, the working tree over 5ceb287a. The observation the GPU's fork in
`docs/spec/monitor.md` asks for, under The window says what is wrong first. Experiment:
`docs/findings/experiments/2026-11-12-the-gpu-over-a-walk.py`.

`video-tests/purb-settings.json` as it stood that evening, both of its bake nodes set live so that every
tool ran, walked over its first 6000 rows offscreen, so nothing painted. The process's share of every GPU
engine was read off `\GPU Engine(*)\Utilization Percentage` about four times a second, raw, by engine type.

| | |
| --- | --- |
| OpenCV | 5.0.0, FFMPEG prebuilt, OpenCL built (NVD3D11), no CUDA device |
| the plate's capture | backend FFMPEG, `CAP_PROP_HW_ACCELERATION` 0, none; `HW_DEVICE` -1 |
| the walk | 6000 rows in 15.2 s and, the run before, 16.5 s |
| samples | 56, and 60 |
| the walk's process, every engine, max and mean | 0.00% |
| everything on the machine, 3D, max and mean | 25.9% and 2.6%; the run before 23.1% and 9.3% |
| everything, VideoDecode | 0.00% |

The process held an instance on the 3D engine in every sample, at nothing: something in it opens a device,
OpenCV's OpenCL or Qt's offscreen platform, and which was not looked for. `cv2.ocl.useOpenCL()` is true, and
OpenCV takes the OpenCL path only for a `UMat`; the tools hand it arrays, and no tool or player module names
a `UMat`, CUDA or OpenCL, by the reading in the spec's facts.

So the decode is the CPU's and so is every tool this document runs, and the fork's first side holds: the
GPU is one line. The 3D load the machine carried over the walk was other processes'.

Not observed: the player's painting. A player was open on the machine for the first run and closed before
it was sampled, so whether a player's process shows any share of an engine while it paints is not known;
Qt's widgets raster on the CPU and the desktop's compositor is another process, which is a reason to expect
none and no measurement. The line the panel draws is read off the samples, so it says a share if one
appears. Not observed either: any document but this one, a bake being written, or the GoPro clip, whose
codec the capture might treat otherwise.

## Whether the decode would be better on it

Asked by Kendrick the same evening. `docs/findings/experiments/2026-11-12-the-gpu-decode.py` steps 1500
frames of `00000.MTS` from row 3000 through a bare `cv2.VideoCapture`, twice each way; CPU is the
process's, every thread.

| acceleration asked, got | output | ms a frame, wall | ms a frame, CPU |
| --- | --- | --- | --- |
| none, none | BGR | 2.45, 2.42 | 7.72, 7.72 |
| none, none | luma plane | 1.28, 1.29 | 5.79, 6.49 |
| any, D3D11 | BGR | 3.88, 4.00 | 10.45, 9.11 |
| any, D3D11 | luma plane | 1.99, 2.00 | 2.68, 2.76 |
| D3D11, D3D11 | BGR | 5.46, 4.61 | 10.65, 12.17 |
| D3D11, D3D11 | luma plane | 1.95, 1.98 | 2.80, 2.93 |

On the path the purb document reads, the luma plane, the GPU's decode is half again slower by the wall,
2.0 ms against 1.3, and costs under half the CPU, 2.7 ms against about 6. The CPU's decode at 1.3 ms of
wall is some four and a half cores busy; the GPU's is one and a third. So it would not make a walk faster
and would make it lighter on the machine, which is a trade and not a win, and bears on the report that a
clip walk makes the machine chug only if the cores are what chugs, which the machine's fork has not
observed. Not checked: that the accelerated luma plane is the same pixels, that seeking behaves, or any
clip but this one.
