# Measured figures for the simulation's prices

The figures `sim/sim.py` prices work with, as measured in `docs/findings/`. A figure is the finding's
own, on the footage it names, and stands only as long as that finding does. "derived" marks a
division of a finding's numbers done here. The machine is the i9-14900KF below unless the footage
cell names another.

| figure | value | footage, frame size | finding |
|---|---|---|---|
| decode, a row in order | 2.71–2.79 ms | `00000.MTS`, 1920×1080 | 2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md |
| decode, a row in order | 3.42–3.47 ms | `00000_168-178.mp4` cut clip, 1920×1080 | 2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md |
| decode, a row in order | 2.5 ms (copy); 2.9–3.1 ms (H.264 re-encodes); 5.3 ms (MJPEG, FFV1) | `00000_168-178.mp4` and remuxes, 1920×1080, a laptop with an RTX 4060 | 2026-11-04-remux-encode-and-seek.md |
| decode, a row in order as luma | 1.52 ms | `00000.MTS`, luma at 0.5, 960×540 | 2026-11-01-trex-runs-and-frame-parallel.md |
| decode, a row in a walk, the plate | 1.05–1.13 ms; 1.41–1.55 on a slower day | `00000.MTS`, 1920×1080 | 2026-11-12-served-bake-upstream-walk.md |
| decode, a row in a walk, the plate | 1.10–1.19 ms | `00000_168-178.mp4`, 1920×1080 | 2026-11-09-crop-cold-walk.md |
| decode, a row in order | 31 ms; 8.4–13 ms as luma | `GX010047c2_02_17_26.MP4`, 5312×2988 | 2026-10-31-background-composite-cost.md; 2026-11-08-bake-window-fit.md |
| decode, a row, served crop | 0.125–0.190 ms luma; 0.07 ms | `square-1.mp4` 256×256; `square-6` crop 260×260 | 2026-11-13-detect-on-a-thresholded-crop.md; 2026-11-21-the-stress-documents-walk-against-its-floor.md |
| decode, a cold seek: a Decoder's opening and first seek | 256 ms; 167 ms | `00000.MTS`; `00000_168-178.mp4`, both 1920×1080 | 2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md |
| decode, a seek to a row at random | 80–86 ms; 137–144 ms | `00000.MTS`; `00000_168-178.mp4` | 2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md |
| decode, a seek to a row at random | 117 ms copy; 19–23 ms keyframe every 1–10 rows; 188 ms HEVC | `00000_168-178.mp4` and remuxes, laptop | 2026-11-04-remux-encode-and-seek.md |
| decode, a seek | 490 ms | `GX010047c2_02_17_26.MP4`, 5312×2988 | 2026-10-31-background-composite-cost.md |
| gray | 1.5 ms | `GX010047c2_02_17_26.MP4`, 5312×2988 | 2026-10-31-background-composite-cost.md |
| threshold | 0.11 ms (cv2 32 threads), 0.15 (1) | `00000.MTS` luma 960×540 | 2026-11-01-trex-runs-and-frame-parallel.md |
| threshold | 0.02–0.04 ms | `00000_168-178.mp4` at 0.5 and its crops | 2026-11-09-crop-cold-walk.md |
| threshold | 0.005–0.009 ms | `square-1.mp4`, 256×256 | 2026-11-13-detect-on-a-thresholded-crop.md |
| detect | 0.039–0.051 ms | `square-1.mp4`, 256×256 | 2026-11-13-detect-on-a-thresholded-crop.md |
| detect | 0.14–0.20 ms, in the player's walk | `square-1.mp4`, 256×256 | 2026-11-13-a-signal-a-row.md |
| blobs | 7.72 ms full-plane, 1.36 ms crop-first | `00000.MTS` luma 960×540 | 2026-11-01-trex-runs-and-frame-parallel.md |
| blobs | 2.34–2.48 ms; 1.66 dish 398×398; 0.97 pile 230×230 | `00000_168-178.mp4` at 0.5, 960×540 | 2026-11-09-crop-cold-walk.md |
| blobs | 0.39–0.45 ms | `00000.MTS` crop to 274×203 | 2026-11-12-served-bake-upstream-walk.md |
| blobs | 0.189–0.204 ms | `square-1.mp4`, 256×256 | 2026-11-13-detect-on-a-thresholded-crop.md |
| motion (with bg-subtract) | 0.01 ms the two | `square-6` crop, 260×260 | 2026-11-21-the-stress-documents-walk-against-its-floor.md |
| flow; speed; changeenergy | 0.76; 0.18; 0.12 ms | `square-6` crop, 260×260 | 2026-11-21-the-stress-documents-walk-against-its-floor.md |
| background, the composite at its first row | 0.93–2.29 s for 50–100 samples, ~20 ms a sample | `2025.7.17…_A5.mp4`, 592×602 | 2026-10-31-background-composite-cost.md |
| background, the composite; bg-subtract a row | 32.5 s for 50 samples; 6.0 ms | `GX010047c2_02_17_26.MP4`, 5312×2988 | 2026-10-31-background-composite-cost.md |
| track, a step | 0.57–0.89 ms | `00000_168-178.mp4`, ~19 blobs a row | 2026-11-08-bake-window-fit.md |
| series tool over a whole clip, a run | smooth mean 2.0 ms; smooth median reach 60 91.9 ms; tracks-filter 1711–1850 ms; resolve 2126 ms; csv 4.8 ms | `purb-settings.json`, 38100 rows | 2026-11-12-what-a-walk-holds.md |
| series tool over a window, a run | size 4.5–6.2 ms; tracks-filter 11.2–11.5; resolve 52–54 | `00000_168-178.mp4`, 590 rows | 2026-11-08-bake-window-fit.md |
| bytes, a decoded frame | 1.98 MB luma 1080p; 15.1 MB luma 5.3K; 45.4 MB 5.3K colour | 1920×1080; 5312×2988 | 2026-11-08-bake-window-fit.md; 2026-10-31-background-composite-cost.md |
| bytes, a gray plane | 0.34 MB; 2 MB (arithmetic); 16 MB | 592×602; 1920×1080; 5312×2988 | 2026-10-31-background-composite-cost.md |
| bytes, a mask | 506 KB dense, 63 KB packbits, 5.0 KB packbits+zlib | 960×540 | 2026-11-01-trex-runs-and-frame-parallel.md |
| bytes, a blobs table row (the head `bake_2`); a tracks row | 1199 B; 1208 B (995 behind contours) | `purb-settings.json`, ~2 animals a row | 2026-11-12-what-a-walk-holds.md |
| bytes, a series signal | 4 B held, 64 B charged by `graph.nbytes` | `purb-settings.json` | 2026-11-12-what-a-walk-holds.md |
| bytes, a row of planes in the memo | 1.49 MB; 1.07 MB cropped to the dish; ~1.4 MB six planes | `00000_168-178.mp4`; `square-6` 260×260 | 2026-11-09-crop-cold-walk.md; 2026-11-21-the-stress-documents-walk-against-its-floor.md |
| bare walk, rows a second; decode's share | 4469–6691 (0.149–0.224 ms a row); about two thirds | `square-1.mp4`, 256×256, threshold → detect | 2026-11-13-a-signal-a-row.md; 2026-11-13-detect-on-a-thresholded-crop.md |
| bare walk, rows a second; decode's share | 515 (1.94 ms a row) at a 64 MB memo, 151–316 at 4 GB; 4% | `square-6` crop 260×260, the stress document | 2026-11-21-the-stress-documents-walk-against-its-floor.md |
| clip walk in the player, rows a second | 1330–1346; 2153 with no ledger | `square-1.mp4`, 256×256 | 2026-11-13-a-signal-a-row.md |
| clip walk in the player, rows a second | 738–1798 | thermal file 1920×1080, served region 256×258 | 2026-11-15-what-a-clip-walk-costs-the-gui-thread.md |
| clip walk in the player, rows a second | 116 (8.6 ms a row) | `square-6` crop 260×260, the stress document | 2026-11-21-the-stress-documents-walk-against-its-floor.md |
| clip walk headless, ms a row | 1.91–5.84 | `purb-settings.json` on `00000.MTS`, 38100 rows | 2026-11-12-a-cold-window-and-the-clip.md |
| window walk cold, ms a row; decode's share | 2.32–2.49; ~45% (derived) | `00000.MTS` crop 274×203, 600 rows | 2026-11-12-served-bake-upstream-walk.md |
| window walk cold, ms a row; decode's share | 5.6–5.8 (derived, 3.3–3.4 s over 590); about a third | `00000_168-178.mp4`, 1920×1080 | 2026-11-09-crop-cold-walk.md |
| held file, bytes a row | ~67 B (derived: 24.0 MB over 345595 clip rows and 21 runs of 600) | `square-1.mp4`, chain track, size, count | 2026-11-13-what-the-held-file-costs.md |
| held file, write | 1775–2107 ms a clip run's first filing; 3.5 ms a 600-row run added; 19 ms a rewrite on letting go | same | 2026-11-13-what-the-held-file-costs.md |
| held file, load | 62 ms (VERSION 4); 2155 ms (VERSION 3 pickle, 85.2 MB) | same | 2026-11-13-what-the-held-file-costs.md |
| threads, threshold + blobs pool | 7.03 ms a row at 1 worker, 2.05 at 4 and 8, 2.57 at 16 | `00000.MTS` luma 960×540, 600 rows | 2026-11-01-trex-runs-and-frame-parallel.md |
| threads, decode | 4 captures on chunks 1.3× one capture; 8 no better | `00000.MTS` luma 960×540 | 2026-11-01-trex-runs-and-frame-parallel.md |
| threads, detect; blobs | 11391 rows a second at 1 thread, 7850 at 8; blobs 4643 at 1, 8618 at 4 | `square-1.mp4`, 256×256 | 2026-11-13-detect-on-a-thresholded-crop.md |
| threads and processes, fused arithmetic | 0.94 ms a row 1 thread; 0.49 at 4 threads, flat after; 0.28 over 16 processes after 0.6 s to start | `square-6` crop 260×260 | 2026-11-21-the-stress-documents-walk-against-its-floor.md |
| GPU | none: decode and every tool on the CPU | `purb-settings.json` | 2026-11-12-the-gpu-over-a-walk.md |
| machine, cores | i9-14900KF, 24 cores, 32 threads | psutil, 2026-11-21 | no finding |
| machine, RAM | 63.7 GiB | psutil, 2026-11-21 | no finding |
| machine, the store's disk | `%LOCALAPPDATA%\SIEVE\store` on C:, Samsung PM9F1 2 TB NVMe SSD | `store.folder()`, Get-PhysicalDisk | no finding |
| machine, the footage's disk | `video-tests/` on C:, the same NVMe SSD; D: is a 20 TB Seagate USB HDD | Get-PhysicalDisk | no finding |
| disk, read and write bytes a second; a seek | no finding | | no finding |
