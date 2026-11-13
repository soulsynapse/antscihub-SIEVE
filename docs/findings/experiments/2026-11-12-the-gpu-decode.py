"""Second experiment behind docs/findings/2026-11-12-the-gpu-over-a-walk.md: what a sequential decode of a
clip costs a frame, wall and CPU over every thread, with the capture's acceleration off, asked for as any,
and asked for as D3D11, each converted to BGR and left as the luma plane, twice.

    .venv\Scripts\python -X utf8 docs\findings\experiments\2026-11-12-the-gpu-decode.py video-tests\00000.MTS 2>NUL
"""
import os, sys, time
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
import cv2
path, N = sys.argv[1], 1500
names = {0: "none", 1: "any", 2: "d3d11", 3: "vaapi", 4: "mfx"}
for accel in (cv2.VIDEO_ACCELERATION_NONE, cv2.VIDEO_ACCELERATION_ANY, cv2.VIDEO_ACCELERATION_D3D11):
    for rgb in (1, 0):
        for rep in range(2):
            cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG, [cv2.CAP_PROP_HW_ACCELERATION, accel])
            if not cap.isOpened():
                print(names[accel], "did not open"); break
            cap.set(cv2.CAP_PROP_CONVERT_RGB, rgb)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 3000)
            ok, f = cap.read()
            t = time.perf_counter(); c = time.process_time()
            n = 0
            while n < N:
                ok, f = cap.read()
                if not ok: break
                n += 1
            dt = time.perf_counter() - t; cpu = time.process_time() - c
            got = int(cap.get(cv2.CAP_PROP_HW_ACCELERATION))
            print(f"asked {names[accel]:6} got {names.get(got, got):6} convert_rgb {rgb}  {dt / max(n,1) * 1000:6.2f} ms/frame wall  "
                  f"{cpu / max(n,1) * 1000:6.2f} ms/frame cpu, all threads  {None if f is None else f.shape}")
            cap.release()
